import { useEffect, useState } from "react";
import {
  Activity,
  ArrowLeft,
  Camera,
  FileText,
  Info,
  Play,
  RefreshCw,
  Settings,
  Square,
  Terminal,
  Trash2,
} from "lucide-react";
import { Button, Card } from "@/components/ui/Primitives";
import * as api from "@/services/api";
import type { StatsSample, VmInfo, VmSnapshot } from "@/types/vm";
import { STATUS_META, formatUptime } from "@/utils/format";

type DetailTab = "overview" | "performance" | "console" | "snapshots" | "settings" | "logs";

export function VmDetailPage({
  vm,
  statsHistory,
  onBack,
  onStart,
  onStop,
  onOpenConsole,
  onToast,
}: {
  vm: VmInfo;
  statsHistory: StatsSample[];
  onBack: () => void;
  onStart: (name: string) => void;
  onStop: (name: string, force?: boolean) => void;
  onOpenConsole: (name: string) => void;
  onToast: (kind: "success" | "error" | "info", title: string, desc?: string) => void;
}) {
  const [tab, setTab] = useState<DetailTab>("overview");
  const [logs, setLogs] = useState<string[]>([]);
  const [snapshots, setSnapshots] = useState<VmSnapshot[]>(() => api.listSnapshots(vm.name));
  const [snapName, setSnapName] = useState("");
  const meta = STATUS_META[vm.status] || STATUS_META.stopped;

  const loadLogs = async () => {
    try {
      const lines = await api.getVmLogs(vm.name, 120);
      setLogs(lines);
    } catch {
      setLogs([]);
    }
  };

  useEffect(() => {
    if (tab === "logs") loadLogs();
  }, [tab, vm.name]);

  const handleCreateSnap = () => {
    if (!snapName.trim()) return;
    api.createSnapshot(vm.name, snapName.trim(), "Snapshot criado pelo painel web");
    setSnapshots(api.listSnapshots(vm.name));
    setSnapName("");
    onToast("info", "Snapshot registrado (mock local)", "Backend QMP savevm ainda não integrado.");
  };

  const handleDeleteSnap = (id: string) => {
    api.deleteSnapshot(id);
    setSnapshots(api.listSnapshots(vm.name));
  };

  const latest = statsHistory[statsHistory.length - 1];

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={onBack}>
            <ArrowLeft className="h-4 w-4" />
            Voltar
          </Button>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-semibold text-white">{vm.name}</h1>
              <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${meta.badge}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
                {meta.label}
              </span>
            </div>
            <p className="text-xs text-slate-400">{vm.macos_version} • {vm.gpu_name || vm.graphics}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {vm.status !== "running" ? (
            <Button variant="primary" size="sm" onClick={() => onStart(vm.name)}>
              <Play className="h-3.5 w-3.5" />
              Iniciar
            </Button>
          ) : (
            <Button variant="danger" size="sm" onClick={() => onStop(vm.name, false)}>
              <Square className="h-3.5 w-3.5" />
              Parar
            </Button>
          )}
          <Button variant="secondary" size="sm" onClick={() => onOpenConsole(vm.name)}>
            <Terminal className="h-3.5 w-3.5 text-blue-400" />
            Abrir Console
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-1 border-b border-[#292A3A] pb-2">
        {[
          { id: "overview", label: "Overview", icon: Info },
          { id: "performance", label: "Performance", icon: Activity },
          { id: "console", label: "Console", icon: Terminal },
          { id: "snapshots", label: "Snapshots", icon: Camera },
          { id: "settings", label: "Configurações", icon: Settings },
          { id: "logs", label: "Logs", icon: FileText },
        ].map((tItem) => {
          const Icon = tItem.icon;
          const active = tab === tItem.id;
          return (
            <button
              key={tItem.id}
              onClick={() => setTab(tItem.id as DetailTab)}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                active
                  ? "bg-violet-600/20 text-violet-200 border border-violet-500/30"
                  : "text-slate-400 hover:bg-white/5 hover:text-white"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              {tItem.label}
            </button>
          );
        })}
      </div>

      {tab === "overview" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Card className="p-5 space-y-3 text-sm">
            <h3 className="font-semibold text-white">Informações Gerais</h3>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between"><span className="text-slate-400">Nome</span><span className="text-white">{vm.name}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Sistema</span><span className="text-white">{vm.macos_version}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">IP</span><span className="font-mono text-white">{vm.ip_address || "Não disponível"}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">PID QEMU</span><span className="font-mono text-white">{vm.pid ?? "—"}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Uptime</span><span className="text-white">{vm.status === "running" ? formatUptime(vm.uptime_seconds) : "—"}</span></div>
            </div>
          </Card>

          <Card className="p-5 space-y-3 text-sm">
            <h3 className="font-semibold text-white">Recursos Alocados</h3>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between"><span className="text-slate-400">vCPUs</span><span className="text-white">{vm.cpus}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Memória RAM</span><span className="text-white">{vm.memory_gib} GB ({vm.memory_mib} MiB)</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Disco</span><span className="text-white">{vm.disk_size_gb ? `${vm.disk_size_gb} GB` : "Não disponível"}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Caminho</span><span className="truncate max-w-[220px] font-mono text-slate-300">{vm.disk_path || "—"}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">GPU</span><span className="text-white">{vm.gpu_name || vm.graphics}</span></div>
            </div>
          </Card>
        </div>
      )}

      {tab === "performance" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Card className="p-5">
            <div className="text-xs text-slate-400">CPU do Host (tempo real)</div>
            <div className="mt-2 text-2xl font-bold text-white">
              {latest ? `${latest.cpu_percent.toFixed(1)}%` : "Não disponível"}
            </div>
          </Card>
          <Card className="p-5">
            <div className="text-xs text-slate-400">Memória do Host</div>
            <div className="mt-2 text-2xl font-bold text-white">
              {latest ? `${latest.ram_percent.toFixed(1)}%` : "Não disponível"}
            </div>
          </Card>
          <Card className="p-5">
            <div className="text-xs text-slate-400">GPU / Disco / Rede por VM</div>
            <div className="mt-2 text-sm text-slate-400">
              Não disponível (sem guest agent conectado)
            </div>
          </Card>
        </div>
      )}

      {tab === "console" && (
        <Card className="flex flex-col items-center justify-center p-10 text-center">
          <Terminal className="h-10 w-10 text-blue-400" />
          <h3 className="mt-3 text-base font-medium text-white">Console Remoto Integrado</h3>
          <p className="mt-1 max-w-md text-xs text-slate-400">
            Abra o console ao vivo em janela dedicada com suporte a tela cheia, mouse e teclado.
          </p>
          <Button variant="primary" className="mt-4" onClick={() => onOpenConsole(vm.name)}>
            Abrir Console ao Vivo
          </Button>
        </Card>
      )}

      {tab === "snapshots" && (
        <Card className="p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="text-sm font-semibold text-white">Snapshots da VM</h3>
              <p className="text-xs text-amber-300/80">
                Persistência simulada no navegador (integração QMP savevm pendente no backend).
              </p>
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={snapName}
                onChange={(e) => setSnapName(e.target.value)}
                placeholder="Nome do snapshot..."
                className="rounded-lg border border-[#292A3A] bg-[#090A10] px-3 py-1.5 text-xs text-white"
              />
              <Button variant="primary" size="sm" onClick={handleCreateSnap}>
                Criar Snapshot
              </Button>
            </div>
          </div>

          {snapshots.length === 0 ? (
            <p className="py-6 text-center text-xs text-slate-500">
              Nenhum snapshot criado para esta VM.
            </p>
          ) : (
            <div className="space-y-2">
              {snapshots.map((s) => (
                <div
                  key={s.id}
                  className="flex items-center justify-between rounded-xl border border-[#292A3A] bg-[#090A10] px-4 py-3 text-xs"
                >
                  <div>
                    <div className="font-medium text-white">{s.name}</div>
                    <div className="text-slate-400">{new Date(s.created_at).toLocaleString("pt-BR")}</div>
                  </div>
                  <Button variant="danger" size="sm" onClick={() => handleDeleteSnap(s.id)}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {tab === "settings" && (
        <Card className="p-5 space-y-3 text-xs">
          <h3 className="text-sm font-semibold text-white">Configurações da VM</h3>
          <p className="text-slate-400">
            Edição dinâmica via API ainda não suportada pelo `reims-ctl` — utilize `vm.toml` no host ou recrie a VM pelo Wizard.
          </p>
          <div className="grid grid-cols-2 gap-3 rounded-xl border border-[#292A3A] bg-[#090A10] p-4">
            <div><span className="text-slate-400">vCPUs:</span> <strong className="text-white">{vm.cpus}</strong></div>
            <div><span className="text-slate-400">RAM:</span> <strong className="text-white">{vm.memory_gib} GB</strong></div>
            <div><span className="text-slate-400">Gráficos:</span> <strong className="text-white">{vm.graphics}</strong></div>
            <div><span className="text-slate-400">GPU:</span> <strong className="text-white">{vm.gpu_name || "Auto"}</strong></div>
          </div>
        </Card>
      )}

      {tab === "logs" && (
        <Card className="p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Logs do QEMU (`qemu.log`)</h3>
            <Button variant="secondary" size="sm" onClick={loadLogs}>
              <RefreshCw className="h-3.5 w-3.5" />
              Atualizar
            </Button>
          </div>
          <pre className="max-h-96 overflow-auto rounded-xl border border-[#292A3A] bg-[#090A10] p-3 font-mono text-xs text-slate-300">
            {logs.length > 0 ? logs.join("\n") : "Nenhum log encontrado para esta VM."}
          </pre>
        </Card>
      )}
    </div>
  );
}
