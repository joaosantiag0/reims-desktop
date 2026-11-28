import { CheckCircle2, Cpu, Shield, XCircle } from "lucide-react";
import { Card } from "@/components/ui/Primitives";
import type { DoctorHealth, GpuDevice, HostOverview } from "@/types/vm";

export function SettingsPage({
  host,
  doctor,
  gpus,
}: {
  host: HostOverview | null;
  doctor: DoctorHealth | null;
  gpus: GpuDevice[];
}) {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-white">Configurações & Diagnóstico</h1>
        <p className="text-xs text-slate-400">
          Estado dos drivers de virtualização, GPUs detectadas e informações do servidor.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card className="p-5 space-y-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <Shield className="h-4 w-4 text-violet-400" />
            Diagnóstico do Host (`reims-ctl doctor`)
          </div>
          {doctor ? (
            <div className="space-y-2.5 text-xs">
              {[
                { name: "KVM (/dev/kvm)", ok: doctor.kvm_ok, detail: doctor.kvm_details },
                { name: "udmabuf (/dev/udmabuf)", ok: doctor.udmabuf_ok, detail: doctor.udmabuf_details },
                { name: "Vulkan", ok: doctor.vulkan_ok, detail: doctor.vulkan_details },
                { name: "QEMU (reims-vgpu)", ok: doctor.qemu_ok, detail: doctor.qemu_details },
              ].map((row) => (
                <div
                  key={row.name}
                  className="flex items-start justify-between gap-3 rounded-xl border border-[#292A3A] bg-[#090A10] p-3"
                >
                  <div>
                    <div className="font-medium text-white">{row.name}</div>
                    <div className="mt-0.5 text-slate-400">{row.detail || "OK"}</div>
                  </div>
                  {row.ok ? (
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
                  ) : (
                    <XCircle className="h-4 w-4 shrink-0 text-rose-400" />
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-500">Carregando diagnóstico...</p>
          )}
        </Card>

        <Card className="p-5 space-y-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <Cpu className="h-4 w-4 text-blue-400" />
            GPUs Físicas Detectadas
          </div>
          {gpus.length === 0 ? (
            <p className="text-xs text-slate-500">Nenhuma GPU detectada.</p>
          ) : (
            <div className="space-y-2 text-xs">
              {gpus.map((g) => (
                <div
                  key={g.id_string}
                  className="flex items-center justify-between rounded-xl border border-[#292A3A] bg-[#090A10] p-3"
                >
                  <div>
                    <div className="font-medium text-white">{g.name}</div>
                    <div className="mt-0.5 font-mono text-slate-400">{g.id_string}</div>
                  </div>
                  {g.is_default && (
                    <span className="rounded-md border border-violet-500/30 bg-violet-500/15 px-2 py-0.5 text-[11px] text-violet-300">
                      Padrão
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}

          <div className="mt-4 rounded-xl border border-[#292A3A] bg-[#090A10] p-3 text-xs text-slate-400">
            <div><strong className="text-slate-200">Hostname:</strong> {host?.hostname || "—"}</div>
            <div className="mt-1"><strong className="text-slate-200">Sistema:</strong> {host?.os || "—"}</div>
            <div className="mt-1"><strong className="text-slate-200">Aviso legal:</strong> Reims Desktop é um projeto comunitário independente, sem afiliação com a Apple Inc. ou steelbrain/reims-vgpu.</div>
          </div>
        </Card>
      </div>
    </div>
  );
}
