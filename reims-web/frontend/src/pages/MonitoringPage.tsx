import { useState } from "react";
import { Activity, AlertTriangle, BellRing, Cpu, HardDrive, MemoryStick, Server } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card } from "@/components/ui/Primitives";
import * as api from "@/services/api";
import type { AlertRule, HostOverview, StatsSample, VmInfo } from "@/types/vm";
import { formatBytes } from "@/utils/format";

export function MonitoringPage({
  host,
  vms,
  statsHistory,
  onToast,
}: {
  host: HostOverview | null;
  vms: VmInfo[];
  statsHistory: StatsSample[];
  onToast: (kind: "success" | "error" | "info", title: string, desc?: string) => void;
}) {
  const [rules, setRules] = useState<AlertRule[]>(() => api.getAlertRules());

  const latest = statsHistory[statsHistory.length - 1];
  const runningCount = vms.filter((v) => v.status === "running").length;
  const stoppedCount = vms.length - runningCount;

  const diskPct =
    host?.storage.total_bytes && host.storage.used_bytes !== undefined
      ? Math.round((host.storage.used_bytes / host.storage.total_bytes) * 100)
      : 0;

  const toggleRule = (id: string) => {
    const next = rules.map((r) => (r.id === id ? { ...r, enabled: !r.enabled } : r));
    setRules(next);
    api.saveAlertRules(next);
    onToast("success", "Regra de alerta atualizada");
  };

  const updateThreshold = (id: string, threshold: number) => {
    const next = rules.map((r) => (r.id === id ? { ...r, threshold } : r));
    setRules(next);
    api.saveAlertRules(next);
  };

  const chartData = statsHistory.map((s) => ({
    time: new Date(s.timestamp).toLocaleTimeString("pt-BR", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }),
    cpu: Number(s.cpu_percent.toFixed(1)),
    ram: Number(s.ram_percent.toFixed(1)),
  }));

  const activeAlerts: string[] = [];
  for (const r of rules) {
    if (!r.enabled) continue;
    if (r.metric === "cpu" && latest && latest.cpu_percent >= r.threshold) {
      activeAlerts.push(`CPU em ${latest.cpu_percent.toFixed(0)}% (limite ${r.threshold}%)`);
    }
    if (r.metric === "ram" && latest && latest.ram_percent >= r.threshold) {
      activeAlerts.push(`RAM em ${latest.ram_percent.toFixed(0)}% (limite ${r.threshold}%)`);
    }
    if (r.metric === "storage" && diskPct >= r.threshold) {
      activeAlerts.push(`Armazenamento em ${diskPct}% (limite ${r.threshold}%)`);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-white">Monitoramento & Alertas</h1>
        <p className="text-xs text-slate-400">
          Visão global de hardware do servidor e regras de alerta configuráveis.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card className="p-4">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>CPU Global</span>
            <Cpu className="h-4 w-4 text-violet-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-white">
            {latest ? `${latest.cpu_percent.toFixed(1)}%` : "—"}
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Memória Global</span>
            <MemoryStick className="h-4 w-4 text-blue-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-white">
            {latest ? `${latest.ram_percent.toFixed(1)}%` : "—"}
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Armazenamento</span>
            <HardDrive className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-white">
            {diskPct}% <span className="text-xs font-normal text-slate-400">({formatBytes(host?.storage.available_bytes)} livres)</span>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Frota de VMs</span>
            <Server className="h-4 w-4 text-fuchsia-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-white">
            {runningCount} <span className="text-xs font-normal text-emerald-400">ativas</span> / {stoppedCount}{" "}
            <span className="text-xs font-normal text-slate-400">paradas</span>
          </div>
        </Card>
      </div>

      {activeAlerts.length > 0 && (
        <Card className="border-amber-500/40 bg-amber-500/10 p-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-amber-300">
            <AlertTriangle className="h-4 w-4" />
            Alertas Ativos ({activeAlerts.length})
          </div>
          <ul className="mt-2 space-y-1 text-xs text-amber-200">
            {activeAlerts.map((a, i) => (
              <li key={i}>• {a}</li>
            ))}
          </ul>
        </Card>
      )}

      <Card className="p-5">
        <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
          <Activity className="h-4 w-4 text-violet-400" />
          Histórico CPU & RAM
        </div>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#292A3A" vertical={false} />
              <XAxis dataKey="time" stroke="#64748B" fontSize={10} />
              <YAxis domain={[0, 100]} stroke="#64748B" fontSize={10} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#141520",
                  borderColor: "#292A3A",
                  borderRadius: "10px",
                  fontSize: "12px",
                }}
              />
              <Line type="monotone" dataKey="cpu" name="CPU %" stroke="#8B5CF6" strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="ram" name="RAM %" stroke="#3B82F6" strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card className="p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <BellRing className="h-4 w-4 text-fuchsia-400" />
            Configuração de Limites de Alerta
          </div>
          <span className="text-[11px] text-slate-400">Persistência local no navegador</span>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {rules.map((r) => (
            <div
              key={r.id}
              className="flex items-center justify-between rounded-xl border border-[#292A3A] bg-[#090A10] p-3.5 text-xs"
            >
              <label className="flex items-center gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={r.enabled}
                  onChange={() => toggleRule(r.id)}
                  className="h-4 w-4 accent-violet-500"
                />
                <span className="font-medium text-slate-200">{r.label}</span>
              </label>

              {r.unit !== "evt" && (
                <div className="flex items-center gap-1.5">
                  <input
                    type="number"
                    value={r.threshold}
                    onChange={(e) => updateThreshold(r.id, Number(e.target.value))}
                    className="w-16 rounded-md border border-[#292A3A] bg-[#141520] px-2 py-1 text-right text-white"
                  />
                  <span className="text-slate-400">{r.unit}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
