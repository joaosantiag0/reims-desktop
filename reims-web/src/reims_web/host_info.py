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
from pathlib import Path
from typing import Any, Dict, List, Optional

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
