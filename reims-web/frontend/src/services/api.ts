import type {
  AlertRule,
  ConsoleInfo,
  CreateVmPayload,
  CreationTask,
  DoctorHealth,
  GpuDevice,
  HostOverview,
  StatsSample,
  VmInfo,
  VmSettings,
  VmSnapshot,
} from "@/types/vm";

const TOKEN_KEY = "reims.token";

export function getStoredToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string | null): void {
  if (token) {
    sessionStorage.setItem(TOKEN_KEY, token);
  } else {
    sessionStorage.removeItem(TOKEN_KEY);
  }
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const res = await fetch(path, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(data.error || data.detail || `HTTP ${res.status}`, res.status);
  }
  return data as T;
}

// ============================================================================
// INTEGRATED BACKEND ENDPOINTS (FastAPI -> reims-ctl / host sysfs)
// ============================================================================

export async function getAuthStatus(): Promise<{ auth_required: boolean }> {
  return request("/api/auth/status");
}

export async function login(password: string): Promise<{ token: string; auth_required: boolean }> {
  const data = await request<{ token: string; auth_required: boolean }>("/api/login", {
    method: "POST",
    body: JSON.stringify({ password }),
  });
  setStoredToken(data.token);
  return data;
}

export async function logout(): Promise<void> {
  try {
    await request("/api/logout", { method: "POST" });
  } finally {
    setStoredToken(null);
  }
}

export async function listVms(): Promise<VmInfo[]> {
  const vms = await request<VmInfo[]>("/api/vms");
  return vms.map((vm) => ({
    ...vm,
    remote_access_enabled: true,
  }));
}

export async function createVm(payload: CreateVmPayload): Promise<{ task_id: string }> {
  return request("/api/vms", {
    method: "POST",
    body: JSON.stringify({
      name: payload.name,
      macos_release: payload.macos_release,
      cpus: payload.cpus,
      memory_mib: payload.memory_mib,
      disk_size_gb: payload.disk_size_gb,
      gpu_name: payload.gpu_name,
    }),
  });
}

export async function getCreationTask(taskId: string): Promise<CreationTask> {
  return request(`/api/tasks/${encodeURIComponent(taskId)}`);
}

export async function startVm(name: string): Promise<void> {
  await request(`/api/vms/${encodeURIComponent(name)}/start`, { method: "POST" });
}

export async function stopVm(name: string, force = false): Promise<void> {
  await request(`/api/vms/${encodeURIComponent(name)}/stop?force=${force ? "true" : "false"}`, {
    method: "POST",
  });
}

export async function deleteVm(name: string): Promise<void> {
  await request(`/api/vms/${encodeURIComponent(name)}`, { method: "DELETE" });
}

export async function getHostOverview(): Promise<HostOverview> {
  return request("/api/host");
}

export async function getDoctor(): Promise<DoctorHealth> {
  return request("/api/doctor");
}

export async function listGpus(): Promise<GpuDevice[]> {
  return request("/api/gpus");
}

export async function getStats(): Promise<StatsSample> {
  const raw = await request<{
    cpu_percent: number;
    ram_percent: number;
    ram_used_gb: number;
    ram_total_gb: number;
  }>("/api/stats");
  return {
    ...raw,
    timestamp: Date.now(),
    gpu_percent: null,
    disk_io_mbps: null,
    net_mbps: null,
  };
}

export async function getVmLogs(name: string, tail = 120): Promise<string[]> {
  const res = await request<{ name: string; lines: string[] }>(
    `/api/vms/${encodeURIComponent(name)}/logs?tail=${tail}`
  );
  return res.lines;
}

export async function getVmSettings(name: string): Promise<VmSettings> {
  return request(`/api/vms/${encodeURIComponent(name)}/settings`);
}

export async function updateVmSettings(
  name: string,
  settings: Partial<VmSettings>
): Promise<VmSettings> {
  return request(`/api/vms/${encodeURIComponent(name)}/settings`, {
    method: "PATCH",
    body: JSON.stringify(settings),
  });
}

export async function getConsoleInfo(name: string): Promise<ConsoleInfo> {
  return request(`/api/vms/${encodeURIComponent(name)}/console`);
}

export async function sendConsoleInput(
  inputUrl: string,
  payload: Record<string, unknown>
): Promise<void> {
  await request(inputUrl, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function buildStreamUrl(streamUrl: string): string {
  const token = getStoredToken();
  if (!token) return streamUrl;
  const sep = streamUrl.includes("?") ? "&" : "?";
  return `${streamUrl}${sep}token=${encodeURIComponent(token)}`;
}

export function openStatsSocket(
  onSample: (sample: StatsSample) => void,
  onStatusChange: (connected: boolean) => void
): () => void {
  let ws: WebSocket | null = null;
  let closed = false;
  let timer: number | null = null;

  const connect = () => {
    if (closed) return;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const token = getStoredToken();
    const tokenQ = token ? `?token=${encodeURIComponent(token)}` : "";
    ws = new WebSocket(`${proto}://${window.location.host}/api/ws/stats${tokenQ}`);
    ws.onopen = () => onStatusChange(true);
    ws.onmessage = (ev) => {
      try {
        const d = JSON.parse(ev.data);
        onSample({
          timestamp: Date.now(),
          cpu_percent: Number(d.cpu_percent ?? 0),
          ram_percent: Number(d.ram_percent ?? 0),
          ram_used_gb: Number(d.ram_used_gb ?? 0),
          ram_total_gb: Number(d.ram_total_gb ?? 0),
          gpu_percent: null,
          disk_io_mbps: null,
          net_mbps: null,
        });
      } catch {
        // ignore malformed frames
      }
    };
    ws.onclose = () => {
      onStatusChange(false);
      if (!closed) {
        timer = window.setTimeout(connect, 4000);
      }
    };
  };

  connect();
  return () => {
    closed = true;
    if (timer !== null) window.clearTimeout(timer);
    if (ws) ws.close();
  };
}

// ============================================================================
// NOT YET INTEGRATED WITH BACKEND (explicit client-side mocks / localStorage)
// ============================================================================

const SNAPSHOTS_KEY = "reims.mock.snapshots";
const ALERTS_KEY = "reims.mock.alerts";

export async function restartVm(name: string): Promise<void> {
  // Uses real stop + start sequence against reims-ctl.
  await stopVm(name, false);
  await startVm(name);
}

export async function suspendVm(name: string): Promise<void> {
  // NOT INTEGRATED IN BACKEND: reims-ctl does not yet expose `pause/suspend`
  // via QMP; falls back to graceful stop until QMP savevm is wired.
  await stopVm(name, false);
}

export function listSnapshots(vmName?: string): VmSnapshot[] {
  // NOT INTEGRATED IN BACKEND: persisted in localStorage for UI workflow.
  try {
    const raw = localStorage.getItem(SNAPSHOTS_KEY);
    const items: VmSnapshot[] = raw ? JSON.parse(raw) : [];
    return vmName ? items.filter((s) => s.vm_name === vmName) : items;
  } catch {
    return [];
  }
}

export function createSnapshot(vmName: string, name: string, description: string): VmSnapshot {
  // NOT INTEGRATED IN BACKEND: mock snapshot record.
  const all = listSnapshots();
  const snap: VmSnapshot = {
    id: `snap-${Date.now()}`,
    vm_name: vmName,
    name,
    description,
    created_at: new Date().toISOString(),
    size_gb: 1.4,
    mocked: true,
  };
  localStorage.setItem(SNAPSHOTS_KEY, JSON.stringify([snap, ...all]));
  return snap;
}

export function deleteSnapshot(id: string): void {
  // NOT INTEGRATED IN BACKEND: mock snapshot removal.
  const all = listSnapshots().filter((s) => s.id !== id);
  localStorage.setItem(SNAPSHOTS_KEY, JSON.stringify(all));
}

export function getAlertRules(): AlertRule[] {
  // NOT INTEGRATED IN BACKEND: client-side alert thresholds.
  try {
    const raw = localStorage.getItem(ALERTS_KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    // ignore
  }
  return [
    { id: "cpu-high", metric: "cpu", label: "CPU acima do limite", threshold: 85, unit: "%", enabled: true },
    { id: "ram-high", metric: "ram", label: "Memória RAM crítica", threshold: 90, unit: "%", enabled: true },
    { id: "disk-high", metric: "storage", label: "Armazenamento crítico", threshold: 85, unit: "%", enabled: true },
    { id: "temp-high", metric: "temp", label: "Temperatura elevada", threshold: 88, unit: "°C", enabled: false },
    { id: "vm-down", metric: "vm_down", label: "VM indisponível", threshold: 1, unit: "evt", enabled: true },
    { id: "vm-fail", metric: "vm_start_fail", label: "Falha ao iniciar VM", threshold: 1, unit: "evt", enabled: true },
  ];
}

export function saveAlertRules(rules: AlertRule[]): void {
  localStorage.setItem(ALERTS_KEY, JSON.stringify(rules));
}
