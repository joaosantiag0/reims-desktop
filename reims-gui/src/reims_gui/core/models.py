from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class VmStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    STARTING = "starting"
    STOPPING = "stopping"


class GraphicsType(str, Enum):
    REIMS_VGPU = "reims-vgpu"
    VMWARE_SVGA = "vmware-svga"


@dataclass
class GpuDevice:
    name: str
    vendor_id: int
    device_id: int
    is_default: bool = False

    @property
    def id_string(self) -> str:
        return f"{self.vendor_id:#06x}:{self.device_id:#06x}"


@dataclass
class VmInfo:
    name: str
    status: VmStatus
    cpus: int
    memory_mib: int
    disk_path: str
    disk_size_gb: Optional[float] = None
    graphics: GraphicsType = GraphicsType.REIMS_VGPU
    gpu_name: Optional[str] = None
    macos_version: str = "macOS 26 Tahoe"
    ssh_port: Optional[int] = None
    pid: Optional[int] = None

    @property
    def memory_gib(self) -> float:
        return round(self.memory_mib / 1024, 1)


@dataclass
class DoctorHealth:
    kvm_ok: bool = True
    kvm_details: str = "/dev/kvm acessível com permissões de leitura/gravação"
    udmabuf_ok: bool = True
    udmabuf_details: str = "/dev/udmabuf carregado no kernel e acessível"
    vulkan_ok: bool = True
    vulkan_details: str = "Driver Vulkan 1.3 detectado"
    qemu_ok: bool = True
    qemu_details: str = "Binário qemu-reims-vgpu instalado e funcional"
    all_ok: bool = True

    def evaluate(self) -> bool:
        self.all_ok = self.kvm_ok and self.udmabuf_ok and self.vulkan_ok and self.qemu_ok
        return self.all_ok


@dataclass
class NewVmRequest:
    name: str
    macos_release: str
    cpus: int
    memory_mib: int
    disk_size_gb: int
    gpu: Optional[GpuDevice] = None
    use_online_installer: bool = True
    custom_installer_path: Optional[str] = None
