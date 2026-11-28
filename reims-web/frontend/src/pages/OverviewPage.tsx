import { useState } from "react";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Cpu,
  HardDrive,
  MemoryStick,
  MonitorPlay,
  Plus,
  Server,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Button, Card, Skeleton } from "@/components/ui/Primitives";
import { VmCard } from "@/components/vm/VmCard";
import type {
  DoctorHealth,
  GpuDevice,
  HostOverview,
  NavPage,
  StatsSample,
  VmInfo,
} from "@/types/vm";
import { formatBytes } from "@/utils/format";

type TimeWindow = "15m" | "1h" | "6h" | "24h";

interface OverviewPageProps {
  host: HostOverview | null;
  doctor: DoctorHealth | null;
  gpus: GpuDevice[];
  vms: VmInfo[];
  statsHistory: StatsSample[];
  loading: boolean;
  busyMap: Record<string, string | null>;
  onNavigate: (page: NavPage) => void;
  onSelectVm: (name: string) => void;
  onStartVm: (name: string) => void;
  onStopVm: (name: string, force?: boolean) => void;
  onRestartVm: (name: string) => void;
  onSuspendVm: (name: string) => void;
  onOpenConsole: (name: string) => void;
  onSnapshotVm: (name: string) => void;
  onCloneVm: (name: string) => void;
  onDeleteVm: (name: string) => void;
}

export function OverviewPage({
  host,
  doctor,
  gpus,
  vms,
  statsHistory,
  loading,
  busyMap,
  onNavigate,
  onSelectVm,
  onStartVm,
  onStopVm,
  onRestartVm,
  onSuspendVm,
  onOpenConsole,
  onSnapshotVm,
  onCloneVm,
  onDeleteVm,
}: OverviewPageProps) {
  const [timeWindow, setTimeWindow] = useState<TimeWindow>("15m");

  const latest = statsHistory[statsHistory.length - 1];
  const runningVms = vms.filter((v) => v.status === "running");
  const primaryGpu = gpus.find((g) => g.is_default) || gpus[0];
  const vmsWithGpu = vms.filter((v) => Boolean(v.gpu_name)).length;

  const memTotal = host?.memory.total_bytes ?? null;
  const memUsed = host?.memory.used_bytes ?? null;
  const memPct =
    memTotal && memUsed !== null ? Math.round((memUsed / memTotal) * 100) : latest?.ram_percent ?? 0;

  const diskTotal = host?.storage.total_bytes ?? null;
  const diskUsed = host?.storage.used_bytes ?? null;
  const diskPct =
    diskTotal && diskUsed !== null ? Math.round((diskUsed / diskTotal) * 100) : 0;

  const chartData = statsHistory.map((s) => ({
    time: new Date(s.timestamp).toLocaleTimeString("pt-BR", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }),
    cpu: Number(s.cpu_percent.toFixed(1)),
    ram: Number(s.ram_percent.toFixed(1)),
  }));

  return (
    <div className="space-y-6">
      {/* Hero greeting banner with wallpaper.png */}
      <div className="relative overflow-hidden rounded-2xl border border-[#292A3A] bg-[#141520] p-6">
        <img
          src="/wallpaper.png"
          alt=""
          className="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-25"
        />
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-[#090A10]/95 via-[#090A10]/75 to-transparent" />

        <div className="relative z-10 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-violet-500/30 bg-violet-500/10 px-3 py-1 text-xs font-medium text-violet-300">
              <Server className="h-3.5 w-3.5" />
              <span>{host?.hostname || "Servidor Reims"}</span>
              <span className="text-slate-500">•</span>
              <span>{host?.os || "Linux KVM"}</span>
            </div>
            <h1 className="mt-3 text-2xl font-semibold tracking-tight text-white">
              Painel de Infraestrutura macOS
            </h1>
            <p className="mt-1 text-sm text-slate-300">
              {runningVms.length} de {vms.length} máquinas virtuais em execução •{" "}
              {gpus.length} GPU(s) detectada(s) via Vulkan
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {doctor && (
              <div className="flex flex-wrap items-center gap-2 rounded-xl border border-[#292A3A] bg-[#090A10]/80 px-3 py-2 text-xs">
                {[
                  { label: "KVM", ok: doctor.kvm_ok },
                  { label: "udmabuf", ok: doctor.udmabuf_ok },
                  { label: "Vulkan", ok: doctor.vulkan_ok },
                  { label: "QEMU", ok: doctor.qemu_ok },
                ].map((c) => (
                  <span
                    key={c.label}
                    className={`inline-flex items-center gap-1 font-medium ${
                      c.ok ? "text-emerald-400" : "text-rose-400"
                    }`}
                  >
                    {c.ok ? (
                      <CheckCircle2 className="h-3.5 w-3.5" />
                    ) : (
                      <AlertCircle className="h-3.5 w-3.5" />
                    )}
                    {c.label}
                  </span>
                ))}
              </div>
            )}
            <Button variant="primary" onClick={() => onNavigate("create")}>
              <Plus className="h-4 w-4" />
              Nova Máquina Virtual
            </Button>
          </div>
        </div>
      </div>

      {/* 4 Physical Resource Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {/* CPU Card */}
        <Card className="p-5">
          {loading && !host ? (
            <Skeleton className="h-32 w-full" />
          ) : (
            <>
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
                  CPU Host
                </span>
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-500/15 text-violet-400">
                  <Cpu className="h-4 w-4" />
                </div>
              </div>
              <div className="mt-3 flex items-baseline justify-between">
                <div className="text-2xl font-bold text-white">
                  {latest ? `${latest.cpu_percent.toFixed(0)}%` : "—"}
                </div>
                <span className="text-xs text-slate-400">
                  {host?.cpu.cores ?? "—"}C / {host?.cpu.threads ?? "—"}T
                </span>
              </div>
              <p className="mt-1 truncate text-xs text-slate-400" title={host?.cpu.model || ""}>
                {host?.cpu.model || "Não disponível"}
              </p>
              <div className="mt-3 h-10 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData}>
                    <Area
                      type="monotone"
                      dataKey="cpu"
                      stroke="#8B5CF6"
                      fill="#8B5CF6"
                      fillOpacity={0.18}
                      strokeWidth={1.75}
                      isAnimationActive={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
                <span>Temperatura</span>
                <span className="text-slate-200">
                  {host?.cpu.temp_celsius !== null && host?.cpu.temp_celsius !== undefined
                    ? `${host.cpu.temp_celsius} °C`
                    : "Não disponível"}
                </span>
              </div>
            </>
          )}
        </Card>

        {/* RAM Card */}
        <Card className="p-5">
          {loading && !host ? (
            <Skeleton className="h-32 w-full" />
          ) : (
            <>
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
                  Memória RAM
                </span>
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/15 text-blue-400">
                  <MemoryStick className="h-4 w-4" />
                </div>
              </div>
              <div className="mt-3 flex items-baseline justify-between">
                <div className="text-2xl font-bold text-white">{memPct}%</div>
                <span className="text-xs text-slate-400">
                  {formatBytes(host?.memory.used_bytes)} / {formatBytes(host?.memory.total_bytes)}
                </span>
              </div>
              <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-[#090A10]">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-blue-500 to-violet-500 transition-all"
                  style={{ width: `${Math.min(100, memPct)}%` }}
                />
              </div>
              <div className="mt-4 space-y-1.5 text-xs">
                <div className="flex justify-between text-slate-400">
                  <span>Disponível</span>
                  <span className="text-slate-200">
                    {formatBytes(host?.memory.available_bytes)}
                  </span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Reservada p/ VMs</span>
                  <span className="font-medium text-blue-300">
                    {formatBytes(host?.memory.vm_reserved_bytes)}
                  </span>
                </div>
              </div>
            </>
          )}
        </Card>

        {/* GPU Card */}
        <Card className="p-5">
          {loading && !host ? (
            <Skeleton className="h-32 w-full" />
          ) : (
            <>
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
                  GPU & Aceleração
                </span>
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-fuchsia-500/15 text-fuchsia-400">
                  <MonitorPlay className="h-4 w-4" />
                </div>
              </div>
              <div className="mt-3 text-sm font-semibold text-white line-clamp-2 min-h-[2.5rem]">
                {primaryGpu?.name || "Não disponível"}
              </div>
              <div className="mt-2 space-y-1.5 text-xs">
                <div className="flex justify-between text-slate-400">
                  <span>Tecnologia</span>
                  <span className="text-fuchsia-300 font-medium">
                    reims-vgpu (Compartilhado)
                  </span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>VRAM / Uso GPU</span>
                  <span className="text-slate-500">Não disponível</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>VMs com GPU</span>
                  <span className="text-slate-200">{vmsWithGpu}</span>
                </div>
              </div>
            </>
          )}
        </Card>

        {/* Storage Card */}
        <Card className="p-5">
          {loading && !host ? (
            <Skeleton className="h-32 w-full" />
          ) : (
            <>
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
                  Armazenamento
                </span>
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/15 text-emerald-400">
                  <HardDrive className="h-4 w-4" />
                </div>
              </div>
              <div className="mt-3 flex items-baseline justify-between">
                <div className="text-2xl font-bold text-white">{diskPct}%</div>
                <span className="text-xs text-slate-400">
                  {formatBytes(host?.storage.used_bytes)} / {formatBytes(host?.storage.total_bytes)}
                </span>
              </div>
              <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-[#090A10]">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-blue-500 transition-all"
                  style={{ width: `${Math.min(100, diskPct)}%` }}
                />
              </div>
              <div className="mt-4 space-y-1.5 text-xs">
                <div className="flex justify-between text-slate-400">
                  <span>Espaço livre</span>
                  <span className="text-slate-200">
                    {formatBytes(host?.storage.available_bytes)}
                  </span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>VMs ({host?.storage.volumes_count ?? 0} volumes)</span>
                  <span className="font-medium text-emerald-300">
                    {formatBytes(host?.storage.vm_used_bytes)}
                  </span>
                </div>
              </div>
            </>
          )}
        </Card>
      </div>

      {/* Monitoring Charts */}
      <Card className="p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-violet-400" />
            <h2 className="text-base font-semibold text-white">
              Telemetria em Tempo Real
            </h2>
          </div>
          <div className="flex items-center gap-1 rounded-lg border border-[#292A3A] bg-[#090A10] p-1">
            {(["15m", "1h", "6h", "24h"] as TimeWindow[]).map((w) => (
              <button
                key={w}
                onClick={() => setTimeWindow(w)}
                className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                  timeWindow === w
                    ? "bg-violet-600/30 text-violet-200 border border-violet-500/40"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {w}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="rounded-xl border border-[#292A3A]/80 bg-[#0D0E17] p-4">
            <div className="mb-2 flex items-center justify-between text-xs">
              <span className="font-medium text-slate-300">CPU & Memória (%)</span>
              <span className="text-slate-500">Janela: {timeWindow}</span>
            </div>
            <div className="h-52 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="cpuGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.35} />
                      <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="ramGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#292A3A" vertical={false} />
                  <XAxis dataKey="time" stroke="#64748B" fontSize={10} tickLine={false} />
                  <YAxis domain={[0, 100]} stroke="#64748B" fontSize={10} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#141520",
                      borderColor: "#292A3A",
                      borderRadius: "10px",
                      fontSize: "12px",
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="cpu"
                    name="CPU %"
                    stroke="#8B5CF6"
                    fill="url(#cpuGrad)"
                    strokeWidth={2}
                    isAnimationActive={false}
                  />
                  <Area
                    type="monotone"
                    dataKey="ram"
                    name="RAM %"
                    stroke="#3B82F6"
                    fill="url(#ramGrad)"
                    strokeWidth={2}
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 lg:grid-cols-1">
            {[
              { title: "Utilização da GPU", detail: "Não suportado pelo driver NVK/nouveau atual" },
              { title: "I/O de Disco", detail: "Não disponível na API de telemetria atual" },
              { title: "Tráfego de Rede", detail: "Não disponível na API de telemetria atual" },
            ].map((item) => (
              <div
                key={item.title}
                className="flex items-center justify-between rounded-xl border border-dashed border-[#292A3A] bg-[#0D0E17]/60 px-4 py-3.5"
              >
                <div>
                  <div className="text-xs font-medium text-slate-300">{item.title}</div>
                  <div className="mt-0.5 text-[11px] text-slate-500">{item.detail}</div>
                </div>
                <span className="rounded-md border border-[#292A3A] bg-[#141520] px-2 py-1 text-[11px] text-slate-400">
                  Não disponível
                </span>
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* VMs Fleet preview */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-semibold text-white">Máquinas Virtuais</h2>
          <Button variant="ghost" size="sm" onClick={() => onNavigate("vms")}>
            Ver todas ({vms.length})
          </Button>
        </div>
        {vms.length === 0 ? (
          <Card className="flex flex-col items-center justify-center p-10 text-center">
            <Server className="h-10 w-10 text-slate-600" />
            <h3 className="mt-3 text-sm font-medium text-white">
              Nenhuma máquina virtual cadastrada
            </h3>
            <p className="mt-1 text-xs text-slate-400">
              Crie sua primeira VM macOS acelerada por GPU com alguns cliques.
            </p>
            <Button variant="primary" size="sm" className="mt-4" onClick={() => onNavigate("create")}>
              <Plus className="h-3.5 w-3.5" />
              Criar VM
            </Button>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {vms.map((vm) => (
              <VmCard
                key={vm.name}
                vm={vm}
                busyAction={busyMap[vm.name]}
                onSelect={onSelectVm}
                onStart={onStartVm}
                onStop={onStopVm}
                onRestart={onRestartVm}
                onSuspend={onSuspendVm}
                onOpenConsole={onOpenConsole}
                onSnapshot={onSnapshotVm}
                onClone={onCloneVm}
                onDelete={onDeleteVm}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
