"""Host hardware, storage, and VM log inspection helpers for Reims Web.

Collects real host metrics where the OS exposes them and returns `None` for
metrics that cannot be collected (e.g. NVK/nouveau VRAM or CPU temperature on
hosts without sysfs thermal sensors), so the UI never fabricates hardware data.
"""
from __future__ import annotations

import os
import platform
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]

from reims_gui.core.models import VmInfo


def _read_cpu_model() -> Optional[str]:
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        for line in cpuinfo.read_text(errors="ignore").splitlines():
            if line.lower().startswith("model name"):
                _, val = line.split(":", 1)
                return val.strip()
    proc = platform.processor()
    return proc.strip() or None


def _read_cpu_temp_celsius() -> Optional[float]:
    thermal_root = Path("/sys/class/thermal")
    if not thermal_root.is_dir():
        return None
    best: Optional[float] = None
    for zone in sorted(thermal_root.glob("thermal_zone*")):
        temp_file = zone / "temp"
        if not temp_file.is_file():
            continue
        try:
            raw = int(temp_file.read_text().strip())
            c = raw / 1000.0 if raw > 200 else float(raw)
            if 0 < c < 130 and (best is None or c > best):
                best = round(c, 1)
        except Exception:
            continue
    return best


def _vms_root() -> Path:
    return Path.home() / ".local" / "share" / "reims-ctl" / "vms"


def _read_meminfo_bytes() -> Dict[str, Optional[int]]:
    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        vals: Dict[str, int] = {}
        for line in meminfo.read_text(errors="ignore").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                vals[parts[0].rstrip(":")] = int(parts[1]) * 1024
        total = vals.get("MemTotal")
        avail = vals.get("MemAvailable", vals.get("MemFree"))
        if total is not None and avail is not None:
            return {
                "total_bytes": total,
                "available_bytes": avail,
                "used_bytes": max(0, total - avail),
            }
    return {"total_bytes": None, "available_bytes": None, "used_bytes": None}


def get_host_overview(vms: List[VmInfo], mock: bool = False) -> Dict[str, Any]:
    if mock:
        vm_ram_bytes = sum(v.memory_mib * 1024 * 1024 for v in vms)
        return {
            "hostname": "reims-dev-mock",
            "os": f"{platform.system()} {platform.release()} (mock)",
            "cpu": {
                "model": _read_cpu_model() or "Mock x86_64 CPU",
                "cores": os.cpu_count() or 8,
                "threads": os.cpu_count() or 8,
                "temp_celsius": None,
            },
            "memory": {
                "total_bytes": 16 * 1024**3,
                "used_bytes": 4 * 1024**3,
                "available_bytes": 12 * 1024**3,
                "vm_reserved_bytes": vm_ram_bytes,
            },
            "storage": {
                "total_bytes": 512 * 1024**3,
                "used_bytes": 148 * 1024**3,
                "available_bytes": 364 * 1024**3,
                "vm_used_bytes": 64 * 1024**3,
                "volumes_count": len(vms),
            },
        }

    mem = _read_meminfo_bytes()
    vm_ram_bytes = sum(v.memory_mib * 1024 * 1024 for v in vms)

    vms_dir = _vms_root()
    usage_target = vms_dir if vms_dir.exists() else Path.home()
    disk = shutil.disk_usage(usage_target)

    vm_used_bytes = 0
    volumes_count = 0
    if vms_dir.is_dir():
        for vm_dir in vms_dir.iterdir():
            if not vm_dir.is_dir():
                continue
            for img in vm_dir.iterdir():
                if img.suffix in (".qcow2", ".img", ".raw") and img.is_file():
                    volumes_count += 1
                    try:
                        vm_used_bytes += img.stat().st_size
                    except OSError:
                        pass

    threads = os.cpu_count() or 1
    return {
        "hostname": socket.gethostname(),
        "os": f"{platform.system()} {platform.release()}",
        "cpu": {
            "model": _read_cpu_model(),
            "cores": threads,
            "threads": threads,
            "temp_celsius": _read_cpu_temp_celsius(),
        },
        "memory": {
            **mem,
            "vm_reserved_bytes": vm_ram_bytes,
        },
        "storage": {
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "available_bytes": disk.free,
            "vm_used_bytes": vm_used_bytes,
            "volumes_count": volumes_count,
        },
    }


def read_vm_logs(name: str, tail_lines: int = 120, mock: bool = False) -> List[str]:
    if mock:
        return [
            f"[mock] VM '{name}' initialized",
            "[mock] OpenCore EFI bootloader loaded",
            "[mock] reims-graphics-pci Vulkan surface ready",
        ]
    log_path = _vms_root() / name / "logs" / "qemu.log"
    if not log_path.is_file():
        return []
    lines = log_path.read_text(errors="ignore").splitlines()
    return lines[-tail_lines:]


def read_vm_settings(name: str, vm: Optional[VmInfo] = None, mock: bool = False) -> Dict[str, Any]:
    if mock or tomllib is None:
        return {
            "cpus": vm.cpus if vm else 4,
            "memory_mib": vm.memory_mib if vm else 8192,
            "graphics": vm.graphics.value if vm else "reims-vgpu",
            "gpu_name": vm.gpu_name if vm else None,
            "resolution": "1920x1080",
            "borderless": False,
            "audio_enabled": True,
            "network_enabled": True,
            "ssh_port": vm.ssh_port or 0 if vm else 0,
            "disk_controller": "ahci",
            "logs_enabled": False,
        }

    toml_path = _vms_root() / name / "vm.toml"
    if not toml_path.is_file():
        raise FileNotFoundError(f"vm.toml not found for {name}")

    data = tomllib.loads(toml_path.read_text(encoding="utf-8", errors="ignore"))
    display = data.get("display", {})
    gpu = data.get("gpu", {})
    audio = data.get("audio", {})
    network = data.get("network", {})
    logs = data.get("logs", {})
    q35 = data.get("q35", {})

    return {
        "cpus": int(data.get("cpus", vm.cpus if vm else 4)),
        "memory_mib": int(data.get("memory_mib", vm.memory_mib if vm else 8192)),
        "graphics": str(data.get("graphics", "reims-vgpu")),
        "gpu_name": gpu.get("name") or None,
        "resolution": str(display.get("resolution", "1920x1080")),
        "borderless": bool(display.get("borderless", False)),
        "audio_enabled": bool(audio.get("enabled", True)),
        "network_enabled": bool(network.get("enabled", True)),
        "ssh_port": int(network.get("ssh_port", 0) or 0),
        "disk_controller": str(q35.get("disk_controller", "ahci")),
        "logs_enabled": bool(logs.get("enabled", False)),
    }


def update_vm_settings(
    name: str,
    payload: Dict[str, Any],
    ctl_binary: str,
    mock: bool = False,
) -> Dict[str, Any]:
    if mock:
        return {
            "cpus": int(payload.get("cpus", 4)),
            "memory_mib": int(payload.get("memory_mib", 8192)),
            "graphics": str(payload.get("graphics", "reims-vgpu")),
            "gpu_name": payload.get("gpu_name") or None,
            "resolution": str(payload.get("resolution", "1920x1080")),
            "borderless": bool(payload.get("borderless", False)),
            "audio_enabled": bool(payload.get("audio_enabled", True)),
            "network_enabled": bool(payload.get("network_enabled", True)),
            "ssh_port": int(payload.get("ssh_port", 0) or 0),
            "disk_controller": str(payload.get("disk_controller", "ahci")),
            "logs_enabled": bool(payload.get("logs_enabled", False)),
        }

    args: List[str] = [ctl_binary, "set", name]
    if "cpus" in payload:
        cpus = max(1, int(payload["cpus"]))
        args.extend(["--cpus", str(cpus)])
    if "memory_mib" in payload:
        mem = max(2048, int(payload["memory_mib"]))
        args.extend(["--memory", f"{mem}M"])
    if "graphics" in payload and payload["graphics"] in ("reims-vgpu", "vmware-svga"):
        args.extend(["--graphics", str(payload["graphics"])])
    if "gpu_name" in payload:
        gpu_val = str(payload["gpu_name"]).strip() if payload["gpu_name"] else "auto"
        args.extend(["--gpu", gpu_val or "auto"])
    if "resolution" in payload and payload["resolution"]:
        args.extend(["--resolution", str(payload["resolution"]).strip()])
    if "borderless" in payload:
        args.extend(["--borderless", "true" if payload["borderless"] else "false"])
    if "audio_enabled" in payload:
        args.extend(["--audio", "true" if payload["audio_enabled"] else "false"])
    if "network_enabled" in payload:
        args.extend(["--network", "true" if payload["network_enabled"] else "false"])
    if "ssh_port" in payload:
        args.extend(["--ssh-port", str(max(0, int(payload["ssh_port"] or 0)))])
    if "disk_controller" in payload and payload["disk_controller"] in ("ahci", "nvme", "virtio"):
        args.extend(["--disk-controller", str(payload["disk_controller"])])
    if "logs_enabled" in payload:
        args.extend(["--logs", "true" if payload["logs_enabled"] else "false"])

    res = subprocess.run(args, capture_output=True, text=True, timeout=30)
    if res.returncode != 0:
        err = (res.stderr or res.stdout or "reims-ctl set failed").strip()
        raise RuntimeError(err)

    return read_vm_settings(name, mock=False)
