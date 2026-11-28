import { useMemo, useState } from "react";
import { ArrowUpDown, Plus, Search, Server } from "lucide-react";
import { Button, Card } from "@/components/ui/Primitives";
import { VmCard } from "@/components/vm/VmCard";
import type { NavPage, VmInfo } from "@/types/vm";

interface VmsPageProps {
  vms: VmInfo[];
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

export function VmsPage({
  vms,
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
}: VmsPageProps) {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<"name" | "ram" | "cpu" | "status">("name");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return vms
      .filter((v) => {
        if (statusFilter !== "all" && v.status !== statusFilter) return false;
        if (q && !v.name.toLowerCase().includes(q) && !v.macos_version.toLowerCase().includes(q)) {
          return false;
        }
        return true;
      })
      .sort((a, b) => {
        if (sortBy === "ram") return b.memory_mib - a.memory_mib;
        if (sortBy === "cpu") return b.cpus - a.cpus;
        if (sortBy === "status") return a.status.localeCompare(b.status);
        return a.name.localeCompare(b.name);
      });
  }, [vms, query, statusFilter, sortBy]);

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Minhas Máquinas Virtuais</h1>
          <p className="text-xs text-slate-400">
            Gerencie ciclo de vida, console remoto, snapshots e recursos das suas VMs macOS.
          </p>
        </div>
        <Button variant="primary" onClick={() => onNavigate("create")}>
          <Plus className="h-4 w-4" />
          Nova VM
        </Button>
      </div>

      {/* Search, filter & sort bar */}
      <Card className="flex flex-col gap-3 p-3.5 md:flex-row md:items-center md:justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar por nome ou versão do macOS..."
            className="w-full rounded-lg border border-[#292A3A] bg-[#090A10] py-2 pr-3 pl-9 text-sm text-white placeholder-slate-500 focus:border-violet-500 focus:outline-none"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1 rounded-lg border border-[#292A3A] bg-[#090A10] p-1 text-xs">
            {[
              { id: "all", label: "Todas" },
              { id: "running", label: "Running" },
              { id: "stopped", label: "Stopped" },
              { id: "error", label: "Error" },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setStatusFilter(f.id)}
                className={`rounded-md px-2.5 py-1 font-medium transition-colors ${
                  statusFilter === f.id
                    ? "bg-violet-600/30 text-violet-200"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1.5 rounded-lg border border-[#292A3A] bg-[#090A10] px-2.5 py-1.5 text-xs text-slate-300">
            <ArrowUpDown className="h-3.5 w-3.5 text-slate-400" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
              className="bg-transparent text-xs text-slate-200 focus:outline-none"
            >
              <option value="name" className="bg-[#141520]">Nome</option>
              <option value="status" className="bg-[#141520]">Status</option>
              <option value="ram" className="bg-[#141520]">Memória RAM</option>
              <option value="cpu" className="bg-[#141520]">vCPUs</option>
            </select>
          </div>
        </div>
      </Card>

      {filtered.length === 0 ? (
        <Card className="flex flex-col items-center justify-center p-12 text-center">
          <Server className="h-10 w-10 text-slate-600" />
          <h3 className="mt-3 text-sm font-medium text-white">
            Nenhuma VM encontrada
          </h3>
          <p className="mt-1 text-xs text-slate-400">
            Ajuste os filtros de busca ou crie uma nova máquina virtual.
          </p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((vm) => (
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
  );
}
