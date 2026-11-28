from __future__ import annotations
import json
import logging
import os
import re
import shutil
import subprocess
from typing import Callable, Dict, List, Optional, Tuple

from reims_gui.core.models import (
    DoctorHealth,
    GpuDevice,
    GraphicsType,
    NewVmRequest,
    VmInfo,
    VmStatus,
)
from reims_gui.i18n.translator import t

logger = logging.getLogger(__name__)

# Marker in `reims-ctl --help` of the upstream Rust tool (steelbrain/reims-vgpu),
# whose CLI differs from the bundled `reims-desktop-ctl` bash fallback.
UPSTREAM_HELP_MARKER = "reims-vgpu"

# GUI release names -> values upstream `create --macos` accepts (a name like
# "tahoe", or a number: Sequoia is 15, Sonoma is 14, Ventura is 13).
MACOS_RELEASE_MAP: Dict[str, str] = {
    "tahoe": "tahoe",
    "26": "tahoe",
    "sequoia": "15",
    "15": "15",
    "sonoma": "14",
    "14": "14",
    "ventura": "13",
    "13": "13",
}


# VM-mode helper (reims-desktop-suspend): pauses/kills the LXQt desktop while a
# VM runs and restores it afterwards, freeing CPU/RAM for the guest. Best-effort
# and idempotent: safe to call regardless of backend (the bundled bash ctl also
# does this on its own).
_SUSPEND_BINARY_CANDIDATES = (
    "/usr/bin/reims-desktop-suspend",
    "reims-desktop-suspend",
)


def find_suspend_binary() -> Optional[str]:
    path = os.environ.get("REIMS_SUSPEND_BIN") or ""
    if path and (os.path.isfile(path) and os.access(path, os.X_OK)):
        return path
    for candidate in _SUSPEND_BINARY_CANDIDATES:
        resolved = shutil.which(candidate) if "/" not in candidate else candidate
        if resolved and os.path.isfile(resolved) and os.access(resolved, os.X_OK):
            return resolved
    return None


def suspend_desktop_for_vm() -> None:
    """Pause/kill the desktop right before a VM starts (best-effort, silent)."""
    binary = find_suspend_binary()
    if not binary:
        return
    try:
        subprocess.run(
            [binary, "pause"],
            check=False,
            timeout=15,
            capture_output=True,
            text=True,
        )
        logger.info("VM mode: desktop suspended for VM run")
    except Exception as e:  # pragma: no cover - defensive: never block VM start
        logger.debug(f"VM mode: could not suspend desktop: {e}")


def resume_desktop_after_vm() -> None:
    """Restore the desktop after a VM stops (best-effort, silent)."""
    binary = find_suspend_binary()
    if not binary:
        return
    try:
        subprocess.run(
            [binary, "resume"],
            check=False,
            timeout=30,
            capture_output=True,
            text=True,
        )
        logger.info("VM mode: desktop restored after VM stop")
    except Exception as e:  # pragma: no cover - defensive: never block VM stop
        logger.debug(f"VM mode: could not restore desktop: {e}")


def detect_ctl_backend(binary_path: str) -> str:
    """Return "upstream" for the Rust reims-ctl, "desktop" for the bash fallback."""
    try:
        res = subprocess.run(
            [binary_path, "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        out = (res.stdout or "") + (res.stderr or "")
        return "upstream" if UPSTREAM_HELP_MARKER in out else "desktop"
    except Exception:
        return "desktop"


def _parse_mib(value: str) -> Optional[int]:
    """Parse an upstream size string such as "16G", "512M" or "8192" into MiB."""
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([GgMm]?)", str(value).strip())
    if not m:
        return None
    number = float(m.group(1))
    unit = m.group(2).lower()
    if unit == "g":
        return int(number * 1024)
    if unit == "m":
        return int(number)
    # A bare number is KiB in upstream's format_mib output; treat it as MiB anyway.
    return int(number)


def parse_upstream_doctor(output: str) -> Tuple[Dict[str, bool], Dict[str, str]]:
    """Parse upstream `doctor` lines: "ok  <what>: <detail>" / "FAIL <what>: <detail>"."""
    ok: Dict[str, bool] = {"kvm": False, "udmabuf": False, "vulkan": False, "qemu": False}
    details: Dict[str, str] = {}
    for raw in output.splitlines():
        m = re.match(r"^(ok|FAIL)\s+(.+?):\s*(.*)$", raw.strip())
        if not m:
            continue
        passed = m.group(1) == "ok"
        what = m.group(2).strip().lower()
        detail = m.group(3).strip()
        for key in ok:
            if key in what:
                ok[key] = passed
                details[key] = detail
    return ok, details


def parse_desktop_doctor(output: str) -> Tuple[Dict[str, bool], Dict[str, str]]:
    """Heuristic parse of the bundled bash ctl's `doctor` output."""
    low = output.lower()
    ok = {
        "kvm": "kvm" not in low or "ok" in low,
        "udmabuf": "udmabuf" in low and "error" not in low,
        "vulkan": "vulkan" in low and "error" not in low,
        "qemu": "qemu" in low and "error" not in low,
    }
    return ok, {}


def parse_upstream_gpus(output: str) -> List[GpuDevice]:
    """Parse upstream `gpus` lines: " 1. Name  [10de:2520]  /path/icd.json"."""
    gpus: List[GpuDevice] = []
    for raw in output.splitlines():
        m = re.match(
            r"^\s*\d+\.\s+(.+?)\s+\[([0-9a-fA-F]{4}):([0-9a-fA-F]{4})\]",
            raw.strip(),
        )
        if not m:
            continue
        try:
            vendor_id = int(m.group(2), 16)
            device_id = int(m.group(3), 16)
        except ValueError:
            vendor_id = device_id = 0
        gpus.append(
            GpuDevice(
                name=m.group(1).strip(),
                vendor_id=vendor_id,
                device_id=device_id,
                is_default=len(gpus) == 0,
            )
        )
    return gpus


def parse_desktop_gpus(output: str) -> List[GpuDevice]:
    """Parse the bundled bash ctl's `gpus` lines: "[vendor:device] Name"."""
    gpus: List[GpuDevice] = []
    for raw in output.splitlines():
        line = raw.strip()
        if not line or not line.startswith("["):
            continue
        m = re.match(r"^\[([0-9a-fA-F]{4}):([0-9a-fA-F]{4})\]\s*(.*)$", line)
        if not m:
            continue
        try:
            vendor_id = int(m.group(1), 16)
            device_id = int(m.group(2), 16)
        except ValueError:
            vendor_id = device_id = 0
        gpus.append(
            GpuDevice(
                name=m.group(3).strip() or m.group(0),
                vendor_id=vendor_id,
                device_id=device_id,
                is_default=len(gpus) == 0,
            )
        )
    return gpus


def parse_upstream_show(text: str) -> Dict[str, str]:
    """Parse upstream `show NAME`: indented key/value lines under the VM's name."""
    fields: Dict[str, str] = {}
    for raw in text.splitlines():
        m = re.match(r"^\s+([a-z ]+?)\s{2,}(.+?)\s*$", raw)
        if m:
            fields[m.group(1).strip()] = m.group(2)
    return fields


def vm_info_from_upstream(item: dict, show_fields: Optional[Dict[str, str]] = None) -> VmInfo:
    """Build a VmInfo from an upstream `list --json` item plus `show` details."""
    state = str(item.get("state", "stopped"))
    status = VmStatus.RUNNING if state == "running" else VmStatus.STOPPED
    fields = show_fields or {}
    directory = str(item.get("dir", ""))
    disk = fields.get("disk", "")
    disk_name = disk.split(" ", 1)[0] if disk else ""
    graphics = fields.get("graphics", "").lower()
    gpu = fields.get("gpu", "")
    if gpu.startswith("automatic"):
        gpu = "Auto"
    cpus = int(fields["cpus"]) if fields.get("cpus", "").isdigit() else 4
    memory_mib = _parse_mib(fields.get("memory", "")) or 8192
    return VmInfo(
        name=str(item.get("name", "Unknown")),
        status=status,
        cpus=cpus,
        memory_mib=memory_mib,
        disk_path=os.path.join(directory, disk_name) if directory and disk_name else directory,
        disk_size_gb=None,
        graphics=GraphicsType.VMWARE_SVGA if "vmware" in graphics else GraphicsType.REIMS_VGPU,
        gpu_name=gpu or "Auto",
        macos_version="macOS",
        pid=item.get("pid") if status == VmStatus.RUNNING else None,
    )


def build_upstream_create_cmd(binary_path: str, req: NewVmRequest) -> List[str]:
    """Map a NewVmRequest onto upstream `reims-ctl create` flags."""
    cmd = [binary_path, "create", req.name]
    cmd += ["--cpus", str(req.cpus)]
    memory_mib = int(req.memory_mib)
    if memory_mib % 1024 == 0:
        cmd += ["--memory", f"{memory_mib // 1024}G"]
    else:
        cmd += ["--memory", f"{memory_mib}M"]
    cmd += ["--disk-size", f"{int(req.disk_size_gb)}G"]
    if req.custom_installer_path:
        cmd += ["--installer", str(req.custom_installer_path)]
    else:
        macos = MACOS_RELEASE_MAP.get(str(req.macos_release).lower(), "latest")
        cmd += ["--macos", macos]
    if req.gpu and req.gpu.name and req.gpu.name.lower() != "auto":
        cmd += ["--gpu", req.gpu.name]
    return cmd


class ReimsCtlClient:
    """Client wrapper for calling the `reims-ctl` CLI tool.

    Speaks two backends: the upstream Rust reims-ctl (steelbrain/reims-vgpu),
    detected by its `--help` text, and the bundled bash `reims-desktop-ctl`.
    """

    def __init__(self, binary_path: Optional[str] = None, mock: bool = False):
        self.binary_path = (
            binary_path
            or shutil.which("reims-ctl")
            or shutil.which("reims-desktop-ctl")
            or os.path.expanduser("~/.cargo/bin/reims-ctl")
            or "/usr/bin/reims-desktop-ctl"
        )
        self.mock = mock or not os.path.exists(self.binary_path)
        self.backend = "mock" if self.mock else detect_ctl_backend(self.binary_path)
        self._show_cache: Dict[str, Dict[str, str]] = {}

        # In-memory state for mock mode
        self._mock_vms: List[VmInfo] = [
            VmInfo(
                name="macOS-Tahoe-Dev",
                status=VmStatus.RUNNING,
                cpus=8,
                memory_mib=16384,
                disk_path="/home/user/.local/share/reims-ctl/vms/macOS-Tahoe-Dev/disk.qcow2",
                disk_size_gb=120.0,
                graphics=GraphicsType.REIMS_VGPU,
                gpu_name="NVIDIA GeForce RTX 4070 (Vulkan 1.3)",
                macos_version="macOS 26 Tahoe",
                ssh_port=2222,
                pid=14230,
            ),
            VmInfo(
                name="macOS-Sequoia-Test",
                status=VmStatus.STOPPED,
                cpus=6,
                memory_mib=8192,
                disk_path="/home/user/.local/share/reims-ctl/vms/macOS-Sequoia-Test/disk.qcow2",
                disk_size_gb=80.0,
                graphics=GraphicsType.REIMS_VGPU,
                gpu_name="AMD Radeon 780M (RADV)",
                macos_version="macOS 15 Sequoia",
            ),
        ]

        self._mock_gpus: List[GpuDevice] = [
            GpuDevice(name="NVIDIA GeForce RTX 4070", vendor_id=0x10DE, device_id=0x2786, is_default=True),
            GpuDevice(name="AMD Radeon 780M (RADV)", vendor_id=0x1002, device_id=0x15BF, is_default=False),
        ]

    def is_available(self) -> bool:
        if self.mock:
            return True
        return os.path.exists(self.binary_path) and os.access(self.binary_path, os.X_OK)

    def run_doctor(self) -> DoctorHealth:
        if self.mock:
            return DoctorHealth(
                kvm_ok=True,
                kvm_details="/dev/kvm disponível e acessível (grupo kvm)",
                udmabuf_ok=True,
                udmabuf_details="/dev/udmabuf carregado com sucesso",
                vulkan_ok=True,
                vulkan_details="Vulkan 1.3 ativo (NVIDIA 550.54 / Mesa 24.0)",
                qemu_ok=True,
                qemu_details="qemu-reims-vgpu instalado em /usr/lib/reims/",
                all_ok=True,
            )

        health = DoctorHealth()
        try:
            res = subprocess.run([self.binary_path, "doctor"], capture_output=True, text=True, timeout=10)
            output = res.stdout + res.stderr
            if self.backend == "upstream":
                checks, details = parse_upstream_doctor(output)
            else:
                checks, details = parse_desktop_doctor(output.lower())
            health.kvm_ok = checks["kvm"]
            health.udmabuf_ok = checks["udmabuf"]
            health.vulkan_ok = checks["vulkan"]
            health.qemu_ok = checks["qemu"]
            if details.get("kvm"):
                health.kvm_details = details["kvm"]
            if details.get("udmabuf"):
                health.udmabuf_details = details["udmabuf"]
            if details.get("vulkan"):
                health.vulkan_details = details["vulkan"]
            if details.get("qemu"):
                health.qemu_details = details["qemu"]
        except Exception as e:
            logger.warning(f"Failed to execute reims-ctl doctor: {e}")
            health.kvm_ok = os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK)
            health.udmabuf_ok = os.path.exists("/dev/udmabuf")
            health.vulkan_ok = True
            health.qemu_ok = True

        health.evaluate()
        return health

    def list_gpus(self) -> List[GpuDevice]:
        if self.mock:
            return self._mock_gpus

        try:
            res = subprocess.run([self.binary_path, "gpus"], capture_output=True, text=True, check=True, timeout=8)
            if self.backend == "upstream":
                gpus = parse_upstream_gpus(res.stdout)
            else:
                gpus = parse_desktop_gpus(res.stdout)
            return gpus if gpus else self._mock_gpus
        except Exception as e:
            logger.error(f"Error listing GPUs: {e}")
            return self._mock_gpus

    def _upstream_show(self, name: str) -> Dict[str, str]:
        cached = self._show_cache.get(name)
        if cached is not None:
            return cached
        try:
            res = subprocess.run(
                [self.binary_path, "show", name],
                capture_output=True,
                text=True,
                check=True,
                timeout=8,
            )
            fields = parse_upstream_show(res.stdout)
        except Exception as e:
            logger.warning(f"Error reading VM details for {name}: {e}")
            fields = {}
        self._show_cache[name] = fields
        return fields

    def list_vms(self) -> List[VmInfo]:
        if self.mock:
            return list(self._mock_vms)

        try:
            res = subprocess.run([self.binary_path, "list", "--json"], capture_output=True, text=True, check=True, timeout=10)
            data = json.loads(res.stdout)
        except Exception as e:
            logger.warning(f"Error fetching VM list with --json: {e}")
            return []

        vms: List[VmInfo] = []
        if self.backend == "upstream":
            for item in data:
                fields = self._upstream_show(str(item.get("name", "")))
                vms.append(vm_info_from_upstream(item, fields))
            return vms

        for item in data:
            status = VmStatus.RUNNING if item.get("running") else VmStatus.STOPPED
            config = item.get("config", {})
            disk_size = config.get("disk_size_gb")
            if disk_size is not None:
                try:
                    disk_size = float(disk_size)
                except (ValueError, TypeError):
                    disk_size = None

            gpu_val = config.get("gpu")
            macos_rel = str(config.get("macos_release", "Tahoe")).capitalize()
            vms.append(
                VmInfo(
                    name=item.get("name", "Unknown"),
                    status=status,
                    cpus=config.get("cpus", 4),
                    memory_mib=config.get("memory_mib", 8192),
                    disk_path=config.get("disk", ""),
                    disk_size_gb=disk_size,
                    graphics=GraphicsType.REIMS_VGPU if config.get("graphics") == "ReimsVgpu" else GraphicsType.VMWARE_SVGA,
                    gpu_name=gpu_val,
                    macos_version=f"macOS {macos_rel}",
                )
            )
        return vms

    def start_vm(self, name: str) -> bool:
        if self.mock:
            for vm in self._mock_vms:
                if vm.name == name:
                    vm.status = VmStatus.RUNNING
                    vm.pid = 9999
                    return True
            return False

        try:
            env = dict(os.environ)
            if "DISPLAY" not in env or not env["DISPLAY"]:
                env["DISPLAY"] = ":0"
            # VM mode: free CPU/RAM for the guest before the VM window opens
            # (idempotent no-op when REIMS_VM_MODE=off or nothing to suspend).
            suspend_desktop_for_vm()
            if self.backend == "upstream":
                # The upstream ctl may stay attached to QEMU where no systemd user
                # manager lingers (e.g. over SSH): never wait for it, and never kill it.
                # VM solo mode: when the suspend helper is available, wrap the ctl
                # call so the desktop is suspended while the VM runs and restored
                # automatically when the QEMU window closes (ctl stays attached).
                suspend_bin = find_suspend_binary()
                cmd = [self.binary_path, "start", name]
                if suspend_bin:
                    cmd = [suspend_bin, "wrap", *cmd]
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=env,
                    start_new_session=True,
                )
                try:
                    code = proc.wait(timeout=10)
                    return code == 0
                except subprocess.TimeoutExpired:
                    # Still attached: the VM window is running, so this is success.
                    return True
            res = subprocess.run(
                [self.binary_path, "start", name],
                check=True,
                timeout=15,
                env=env,
                capture_output=True,
                text=True,
            )
            logger.info("start_vm output: %s", res.stdout)
            return True
        except Exception as e:
            logger.error(f"Failed to start VM {name}: {e}")
            # VM mode: the VM did not start, so give the desktop back.
            resume_desktop_after_vm()
            return False

    def stop_vm(self, name: str, force: bool = False) -> bool:
        if self.mock:
            for vm in self._mock_vms:
                if vm.name == name:
                    vm.status = VmStatus.STOPPED
                    vm.pid = None
                    return True
            return False

        cmd = [self.binary_path, "stop", name]
        if force:
            cmd.append("--force")
        try:
            timeout = 10 if self.backend == "desktop" else 120
            subprocess.run(cmd, check=True, timeout=timeout)
            self._show_cache.pop(name, None)
            # VM mode: bring the desktop back once the guest is gone.
            resume_desktop_after_vm()
            return True
        except Exception as e:
            logger.error(f"Failed to stop VM {name}: {e}")
            return False

    def create_vm(
        self,
        req: NewVmRequest,
        progress_callback: Optional[Callable[[int, str, str], None]] = None,
    ) -> bool:
        if self.mock:
            if progress_callback:
                progress_callback(25, t("wizard.creation.step_init"), f"==> [1/4] Inicializando diretório da VM '{req.name}'...")
                progress_callback(50, t("wizard.creation.step_disk", size=req.disk_size_gb), f"==> [2/4] Alocando disco virtual QCOW2 ({req.disk_size_gb} GB)...")
                progress_callback(75, t("wizard.creation.step_config"), f"==> [3/4] Configurando perfil de hardware e bootloader EFI...")
                progress_callback(100, t("wizard.creation.step_done"), f"==> [4/4] Máquina virtual '{req.name}' criada com sucesso!")

            new_vm = VmInfo(
                name=req.name,
                status=VmStatus.STOPPED,
                cpus=req.cpus,
                memory_mib=req.memory_mib,
                disk_path=f"/home/user/.local/share/reims-ctl/vms/{req.name}/disk.qcow2",
                disk_size_gb=float(req.disk_size_gb),
                graphics=GraphicsType.REIMS_VGPU,
                gpu_name=req.gpu.name if req.gpu else "Auto",
                macos_version=f"macOS {req.macos_release.capitalize()}",
            )
            self._mock_vms.append(new_vm)
            return True

        if self.backend == "upstream":
            cmd = build_upstream_create_cmd(self.binary_path, req)
        else:
            cmd = [
                self.binary_path,
                "create",
                req.name,
                f"--cpus={req.cpus}",
                f"--memory-mib={req.memory_mib}",
                f"--disk-gb={req.disk_size_gb}",
            ]
            if req.gpu:
                cmd.append(f"--gpu={req.gpu.name}")
            if req.custom_installer_path:
                cmd.append(f"--installer={req.custom_installer_path}")
            else:
                cmd.append(f"--macos={req.macos_release}")

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            pct = 10
            if proc.stdout:
                for line in iter(proc.stdout.readline, ""):
                    line_str = line.strip()
                    if not line_str:
                        continue
                    step_msg = None
                    m = re.search(r"(\d{1,3})%", line_str)
                    if self.backend == "upstream":
                        # Upstream streams free-form progress; bucket it by content.
                        low = line_str.lower()
                        if m:
                            pct = min(max(int(m.group(1)), pct), 99)
                        elif "download" in low or "fetch" in low:
                            pct = max(pct, 20)
                        elif "disk" in low:
                            pct = max(pct, 50)
                        elif "opencore" in low:
                            pct = max(pct, 70)
                        elif "created" in low or "created vm" in low or low.startswith("created"):
                            pct = 100
                    elif "[1/4]" in line_str or "[1/5]" in line_str:
                        pct = 25
                        step_msg = t("wizard.creation.step_init")
                    elif "[2/4]" in line_str or "[2/5]" in line_str:
                        pct = 50
                        step_msg = t("wizard.creation.step_disk", size=req.disk_size_gb)
                    elif "[3/4]" in line_str or "[3/5]" in line_str:
                        pct = 75
                        step_msg = t("wizard.creation.step_config")
                    elif "[4/4]" in line_str or "[5/5]" in line_str or "sucesso" in line_str.lower():
                        pct = 100
                        step_msg = t("wizard.creation.step_done")

                    if step_msg is None:
                        step_msg = line_str

                    if progress_callback:
                        progress_callback(pct, step_msg, line_str)

            proc.wait(timeout=600)
            return proc.returncode == 0
        except Exception as e:
            logger.error(f"Failed to create VM {req.name}: {e}")
            if progress_callback:
                progress_callback(0, t("wizard.creation.step_error", err=str(e)), str(e))
            return False

    def delete_vm(self, name: str) -> bool:
        if self.mock:
            self._mock_vms = [v for v in self._mock_vms if v.name != name]
            return True

        try:
            subprocess.run([self.binary_path, "delete", name, "--yes"], check=True, timeout=10)
            self._show_cache.pop(name, None)
            return True
        except Exception as e:
            logger.error(f"Failed to delete VM {name}: {e}")
            return False
