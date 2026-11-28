export type VmStatus =
  | "running"
  | "stopped"
  | "starting"
  | "stopping"
  | "restarting"
  | "suspended"
  | "error";

export interface VmInfo {
  name: string;
  status: VmStatus;
  cpus: number;
  memory_mib: number;
  memory_gib: number;
  disk_path: string | null;
  disk_size_gb: number | null;
  graphics: string;
  gpu_name: string | null;
  macos_version: string;
  ssh_port: number | null;
  pid: number | null;
  // Optional/mocked enriched fields when not provided by reims-ctl:
  ip_address?: string | null;
  uptime_seconds?: number | null;
  remote_access_enabled?: boolean;
  description?: string;
}

export interface HostOverview {
  hostname: string;
  os: string;
  cpu: {
    model: string | null;
    cores: number;
    threads: number;
    temp_celsius: number | null;
  };
  memory: {
    total_bytes: number | null;
    used_bytes: number | null;
    available_bytes: number | null;
    vm_reserved_bytes: number;
  };
  storage: {
    total_bytes: number;
    used_bytes: number;
    available_bytes: number;
    vm_used_bytes: number;
    volumes_count: number;
  };
}

export interface DoctorHealth {
  kvm_ok: boolean;
  kvm_details: string;
  udmabuf_ok: boolean;
  udmabuf_details: string;
  vulkan_ok: boolean;
  vulkan_details: string;
  qemu_ok: boolean;
  qemu_details: string;
  all_ok: boolean;
}

export interface GpuDevice {
  name: string;
  vendor_id: string;
  device_id: string;
  id_string: string;
  is_default: boolean;
}

export interface StatsSample {
  timestamp: number;
  cpu_percent: number;
  ram_percent: number;
  ram_used_gb: number;
  ram_total_gb: number;
  // Optional telemetry (null when backend does not expose it):
  gpu_percent: number | null;
  disk_io_mbps: number | null;
  net_mbps: number | null;
}

export interface CreateVmPayload {
  name: string;
  macos_release: string;
  cpus: number;
  memory_mib: number;
  disk_size_gb: number;
  gpu_name: string | null;
  // Extended wizard fields (stored client-side until backend supports them):
  description?: string;
  storage_type?: "qcow2" | "raw";
  network_mode?: "user-nat" | "bridge";
  ip_mode?: "dhcp" | "static";
  static_ip?: string;
  remote_access?: boolean;
  remote_protocol?: "mjpeg-xdotool" | "novnc" | "spice" | "vnc";
}

export interface CreationTask {
  task_id: string;
  progress: number;
  message: string;
  log: string[];
  done: boolean;
  ok: boolean;
  vm_name: string;
}

export interface ConsoleInfo {
  available: boolean;
  name: string;
  stream_url?: string;
  input_url?: string;
  width?: number;
  height?: number;
  reason?: string;
}

export interface VmSettings {
  cpus: number;
  memory_mib: number;
  graphics: "reims-vgpu" | "vmware-svga";
  gpu_name: string | null;
  resolution: string;
  borderless: boolean;
  audio_enabled: boolean;
  network_enabled: boolean;
  ssh_port: number;
  disk_controller: "ahci" | "nvme" | "virtio";
  logs_enabled: boolean;
}

export interface VmSnapshot {
  id: string;
  vm_name: string;
  name: string;
  created_at: string;
  size_gb: number;
  description: string;
  mocked: boolean;
}

export interface AlertRule {
  id: string;
  metric: "cpu" | "ram" | "storage" | "temp" | "vm_down" | "vm_start_fail";
  label: string;
  threshold: number;
  unit: string;
  enabled: boolean;
}

export interface ToastMessage {
  id: string;
  kind: "success" | "error" | "info";
  title: string;
  description?: string;
}

export type NavPage =
  | "overview"
  | "vms"
  | "create"
  | "monitoring"
  | "remote"
  | "snapshots"
  | "settings"
  | "vm-detail";
