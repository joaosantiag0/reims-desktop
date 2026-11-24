from __future__ import annotations
import json
import logging
import os
import shutil
import subprocess
from typing import Callable, List, Optional

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


class ReimsCtlClient:
    """Client wrapper for calling the `reims-ctl` CLI tool."""

    def __init__(self, binary_path: Optional[str] = None, mock: bool = False):
        self.binary_path = binary_path or shutil.which("reims-desktop-ctl") or shutil.which("reims-ctl") or "/usr/bin/reims-desktop-ctl"
        self.mock = mock or not os.path.exists(self.binary_path)

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
            output = (res.stdout + res.stderr).lower()
            health.kvm_ok = "kvm" not in output or "ok" in output
            health.udmabuf_ok = "udmabuf" in output and "error" not in output
            health.vulkan_ok = "vulkan" in output and "error" not in output
            health.qemu_ok = "qemu" in output and "error" not in output
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
            gpus: List[GpuDevice] = []
            for line in res.stdout.strip().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Format: [vendor:device] Name
                parts = line.split(maxsplit=1)
                name = parts[1] if len(parts) > 1 else parts[0]
                gpus.append(GpuDevice(name=name, vendor_id=0, device_id=0, is_default=len(gpus) == 0))
            return gpus if gpus else self._mock_gpus
        except Exception as e:
            logger.error(f"Error listing GPUs: {e}")
            return self._mock_gpus

    def list_vms(self) -> List[VmInfo]:
        if self.mock:
            return list(self._mock_vms)

        try:
            res = subprocess.run([self.binary_path, "list", "--json"], capture_output=True, text=True, check=True, timeout=10)
            data = json.loads(res.stdout)
            vms = []
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
        except Exception as e:
            logger.warning(f"Error fetching VM list with --json: {e}")
            return []

    def start_vm(self, name: str) -> bool:
        if self.mock:
            for vm in self._mock_vms:
                if vm.name == name:
                    vm.status = VmStatus.RUNNING
                    vm.pid = 9999
                    return True
            return False

        try:
            # Launch asynchronously
            subprocess.Popen([self.binary_path, "start", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            logger.error(f"Failed to start VM {name}: {e}")
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
            subprocess.run(cmd, check=True, timeout=15)
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
                    if "[1/4]" in line_str:
                        pct = 25
                        step_msg = t("wizard.creation.step_init")
                    elif "[2/4]" in line_str:
                        pct = 50
                        step_msg = t("wizard.creation.step_disk", size=req.disk_size_gb)
                    elif "[3/4]" in line_str:
                        pct = 75
                        step_msg = t("wizard.creation.step_config")
                    elif "[4/4]" in line_str or "sucesso" in line_str.lower():
                        pct = 100
                        step_msg = t("wizard.creation.step_done")
                    else:
                        step_msg = line_str

                    if progress_callback:
                        progress_callback(pct, step_msg, line_str)

            proc.wait(timeout=180)
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
            return True
        except Exception as e:
            logger.error(f"Failed to delete VM {name}: {e}")
            return False
