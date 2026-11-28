import { useState } from "react";
import {
  Camera,
  Copy,
  Cpu,
  HardDrive,
  Laptop,
  MemoryStick,
  Monitor,
  MoreHorizontal,
  Pause,
  Play,
  RotateCw,
  Settings,
  Square,
  Terminal,
  Trash2,
} from "lucide-react";
import { Button, Card } from "@/components/ui/Primitives";
import type { VmInfo } from "@/types/vm";
import { STATUS_META, formatUptime } from "@/utils/format";

interface VmCardProps {
  vm: VmInfo;
  busyAction?: string | null;
  onSelect: (name: string) => void;
  onStart: (name: string) => void;
  onStop: (name: string, force?: boolean) => void;
  onRestart: (name: string) => void;
  onSuspend: (name: string) => void;
  onOpenConsole: (name: string) => void;
  onSnapshot: (name: string) => void;
  onClone: (name: string) => void;
  onDelete: (name: string) => void;
}

export function VmCard({
  vm,
  busyAction,
  onSelect,
  onStart,
  onStop,
  onRestart,
  onSuspend,
  onOpenConsole,
  onSnapshot,
  onClone,
  onDelete,
}: VmCardProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const meta = STATUS_META[vm.status] || STATUS_META.stopped;
  const isRunning = vm.status === "running";
  const isBusy = Boolean(busyAction);

  return (
    <Card className="group relative flex flex-col justify-between p-5 hover:border-violet-500/40 hover:shadow-[0_0_28px_rgba(139,92,246,0.08)]">
      {/* Top row */}
      <div>
        <div className="flex items-start justify-between gap-3">
          <button
            onClick={() => onSelect(vm.name)}
            className="flex items-center gap-3 text-left"
          >
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-[#292A3A] bg-gradient-to-br from-violet-500/20 via-blue-500/10 to-fuchsia-500/15 text-violet-300">
              <Laptop className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h3 className="truncate text-base font-semibold text-white group-hover:text-violet-300 transition-colors">
                {vm.name}
              </h3>
              <div className="mt-0.5 flex items-center gap-2 text-xs text-slate-400">
                <span>{vm.macos_version || "macOS"}</span>
                {vm.remote_access_enabled && (
                  <span className="inline-flex items-center gap-1 rounded bg-blue-500/10 px-1.5 py-0.5 text-[10px] font-medium text-blue-300 border border-blue-500/20">
                    <Monitor className="h-2.5 w-2.5" />
                    Remoto
                  </span>
                )}
              </div>
            </div>
          </button>

          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${meta.badge}`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
              {meta.label}
            </span>
            <div className="relative">
              <button
                onClick={() => setMenuOpen((v) => !v)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-white/5 hover:text-white"
                title="Mais ações"
              >
                <MoreHorizontal className="h-4 w-4" />
              </button>
              {menuOpen && (
                <div
                  onMouseLeave={() => setMenuOpen(false)}
                  className="absolute right-0 z-20 mt-1 w-48 rounded-xl border border-[#292A3A] bg-[#141520] p-1.5 shadow-2xl"
                >
                  <button
                    onClick={() => {
                      setMenuOpen(false);
                      onSelect(vm.name);
                    }}
                    className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 hover:bg-white/5"
                  >
                    <Settings className="h-3.5 w-3.5 text-slate-400" />
                    Editar configurações
                  </button>
                  <button
                    onClick={() => {
                      setMenuOpen(false);
                      onSnapshot(vm.name);
                    }}
                    className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 hover:bg-white/5"
                  >
                    <Camera className="h-3.5 w-3.5 text-violet-400" />
                    Criar snapshot
                  </button>
                  <button
                    onClick={() => {
                      setMenuOpen(false);
                      onClone(vm.name);
                    }}
                    className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 hover:bg-white/5"
                  >
                    <Copy className="h-3.5 w-3.5 text-blue-400" />
                    Clonar VM
                  </button>
                  <div className="my-1 border-t border-[#292A3A]" />
                  <button
                    onClick={() => {
                      setMenuOpen(false);
                      onDelete(vm.name);
                    }}
                    className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-rose-300 hover:bg-rose-500/10"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Remover VM
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Specs grid */}
        <div className="mt-4 grid grid-cols-2 gap-2.5 rounded-xl border border-[#292A3A]/70 bg-[#0D0E17]/70 p-3 text-xs">
          <div className="flex items-center gap-2 text-slate-300">
            <Cpu className="h-3.5 w-3.5 text-violet-400 shrink-0" />
            <span className="text-slate-400">CPU:</span>
            <span className="font-medium text-white">{vm.cpus} vCPUs</span>
          </div>
          <div className="flex items-center gap-2 text-slate-300">
            <MemoryStick className="h-3.5 w-3.5 text-blue-400 shrink-0" />
            <span className="text-slate-400">RAM:</span>
            <span className="font-medium text-white">{vm.memory_gib} GB</span>
          </div>
          <div className="flex items-center gap-2 text-slate-300">
            <HardDrive className="h-3.5 w-3.5 text-fuchsia-400 shrink-0" />
            <span className="text-slate-400">Disco:</span>
            <span className="font-medium text-white">
              {vm.disk_size_gb ? `${vm.disk_size_gb} GB` : "Não disponível"}
            </span>
          </div>
          <div className="flex items-center gap-2 text-slate-300">
            <Monitor className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
            <span className="text-slate-400">IP:</span>
            <span className="truncate font-mono text-[11px] text-slate-200">
              {vm.ip_address || "Não disponível"}
            </span>
          </div>
          <div className="col-span-2 flex items-center justify-between border-t border-[#292A3A]/60 pt-2 text-[11px] text-slate-400">
            <span className="truncate max-w-[65%]">
              GPU: <strong className="font-medium text-slate-200">{vm.gpu_name || vm.graphics}</strong>
            </span>
            <span>
              Uptime: <strong className="font-medium text-slate-200">{isRunning ? formatUptime(vm.uptime_seconds) : "—"}</strong>
            </span>
          </div>
        </div>
      </div>

      {/* Action bar */}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        {!isRunning ? (
          <Button
            variant="primary"
            size="sm"
            loading={busyAction === "start"}
            disabled={isBusy}
            onClick={() => onStart(vm.name)}
          >
            <Play className="h-3.5 w-3.5" />
            Iniciar
          </Button>
        ) : (
          <>
            <Button
              variant="secondary"
              size="sm"
              loading={busyAction === "stop"}
              disabled={isBusy}
              onClick={() => onStop(vm.name, false)}
            >
              <Square className="h-3.5 w-3.5 text-rose-400" />
              Parar
            </Button>
            <Button
              variant="secondary"
              size="sm"
              loading={busyAction === "restart"}
              disabled={isBusy}
              onClick={() => onRestart(vm.name)}
              title="Reiniciar VM"
            >
              <RotateCw className="h-3.5 w-3.5 text-violet-400" />
            </Button>
            <Button
              variant="secondary"
              size="sm"
              loading={busyAction === "suspend"}
              disabled={isBusy}
              onClick={() => onSuspend(vm.name)}
              title="Suspender VM"
            >
              <Pause className="h-3.5 w-3.5 text-amber-400" />
            </Button>
          </>
        )}

        <Button
          variant="secondary"
          size="sm"
          onClick={() => onOpenConsole(vm.name)}
          className="ml-auto"
        >
          <Terminal className="h-3.5 w-3.5 text-blue-400" />
          Console
        </Button>
      </div>
    </Card>
  );
}
