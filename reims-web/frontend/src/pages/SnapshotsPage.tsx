import { useState } from "react";
import { Camera, Plus, Trash2 } from "lucide-react";
import { Button, Card } from "@/components/ui/Primitives";
import * as api from "@/services/api";
import type { VmInfo, VmSnapshot } from "@/types/vm";

export function SnapshotsPage({
  vms,
  onToast,
}: {
  vms: VmInfo[];
  onToast: (kind: "success" | "error" | "info", title: string, desc?: string) => void;
}) {
  const [snapshots, setSnapshots] = useState<VmSnapshot[]>(() => api.listSnapshots());
  const [vmName, setVmName] = useState(vms[0]?.name || "");
  const [snapName, setSnapName] = useState("");

  const handleCreate = () => {
    if (!vmName || !snapName.trim()) return;
    api.createSnapshot(vmName, snapName.trim(), "Backup manual");
    setSnapshots(api.listSnapshots());
    setSnapName("");
    onToast("info", "Snapshot criado (mock local)", "Integração QMP savevm pendente no backend.");
  };

  const handleDelete = (id: string) => {
    api.deleteSnapshot(id);
    setSnapshots(api.listSnapshots());
    onToast("success", "Snapshot removido");
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-white">Snapshots e Backups</h1>
        <p className="text-xs text-slate-400">
          Gerencie pontos de restauração das máquinas virtuais (armazenamento local simulado até integração QMP no backend).
        </p>
      </div>

      <Card className="flex flex-wrap items-center gap-3 p-4">
        <select
          value={vmName}
          onChange={(e) => setVmName(e.target.value)}
          className="rounded-lg border border-[#292A3A] bg-[#090A10] px-3 py-2 text-xs text-white"
        >
          {vms.length === 0 && <option value="">Nenhuma VM</option>}
          {vms.map((v) => (
            <option key={v.name} value={v.name}>
              {v.name}
            </option>
          ))}
        </select>
        <input
          type="text"
          value={snapName}
          onChange={(e) => setSnapName(e.target.value)}
          placeholder="Nome do snapshot (ex.: pre-xcode-update)"
          className="flex-1 min-w-[200px] rounded-lg border border-[#292A3A] bg-[#090A10] px-3 py-2 text-xs text-white"
        />
        <Button variant="primary" size="sm" onClick={handleCreate} disabled={!vmName || !snapName.trim()}>
          <Plus className="h-3.5 w-3.5" />
          Criar Snapshot
        </Button>
      </Card>

      {snapshots.length === 0 ? (
        <Card className="flex flex-col items-center justify-center p-12 text-center">
          <Camera className="h-10 w-10 text-slate-600" />
          <h3 className="mt-3 text-sm font-medium text-white">Nenhum snapshot salvo</h3>
          <p className="mt-1 text-xs text-slate-400">
            Crie um snapshot acima para registrar um ponto de restauração.
          </p>
        </Card>
      ) : (
        <div className="space-y-2.5">
          {snapshots.map((s) => (
            <Card key={s.id} className="flex items-center justify-between p-4 text-xs">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-white">{s.name}</span>
                  <span className="rounded bg-violet-500/15 px-2 py-0.5 text-[11px] text-violet-300">
                    {s.vm_name}
                  </span>
                </div>
                <div className="mt-1 text-slate-400">
                  {new Date(s.created_at).toLocaleString("pt-BR")} • {s.description}
                </div>
              </div>
              <Button variant="danger" size="sm" onClick={() => handleDelete(s.id)}>
                <Trash2 className="h-3.5 w-3.5" />
                Remover
              </Button>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
