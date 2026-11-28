import { useEffect, useState } from "react";
import { Check, ChevronLeft, ChevronRight, Cpu, Globe, Laptop, Monitor, ShieldCheck } from "lucide-react";
import { Button, Card } from "@/components/ui/Primitives";
import * as api from "@/services/api";
import type { CreationTask, CreateVmPayload, GpuDevice, HostOverview } from "@/types/vm";
import { formatBytes } from "@/utils/format";

interface CreateVmPageProps {
  host: HostOverview | null;
  gpus: GpuDevice[];
  onCreated: () => void;
  onCancel: () => void;
  onToast: (kind: "success" | "error" | "info", title: string, desc?: string) => void;
}

const STEPS = [
  { id: 1, title: "Identificação", icon: Laptop },
  { id: 2, title: "Recursos", icon: Cpu },
  { id: 3, title: "Rede", icon: Globe },
  { id: 4, title: "Acesso Remoto", icon: Monitor },
  { id: 5, title: "Revisão", icon: ShieldCheck },
];

export function CreateVmPage({
  host,
  gpus,
  onCreated,
  onCancel,
  onToast,
}: CreateVmPageProps) {
  const [step, setStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [task, setTask] = useState<CreationTask | null>(null);

  const [form, setForm] = useState<CreateVmPayload>({
    name: "macOS-Tahoe",
    description: "",
    macos_release: "tahoe",
    cpus: 4,
    memory_mib: 8192,
    disk_size_gb: 64,
    storage_type: "qcow2",
    gpu_name: null,
    network_mode: "user-nat",
    ip_mode: "dhcp",
    static_ip: "",
    remote_access: true,
    remote_protocol: "mjpeg-xdotool",
  });

  const maxCpus = host?.cpu.threads ?? 16;
  const hostRamTotalGb = host?.memory.total_bytes
    ? Math.floor(host.memory.total_bytes / 1024 ** 3)
    : 16;
  const reservedRamGb = host?.memory.vm_reserved_bytes
    ? Math.round(host.memory.vm_reserved_bytes / 1024 ** 3)
    : 0;
  const availableRamGb = Math.max(2, hostRamTotalGb - reservedRamGb);
  const availableDiskGb = host?.storage.available_bytes
    ? Math.floor(host.storage.available_bytes / 1024 ** 3)
    : 256;

  const requestedRamGb = Math.round(form.memory_mib / 1024);
  const ramExceeds = requestedRamGb > hostRamTotalGb;
  const diskExceeds = form.disk_size_gb > availableDiskGb;
  const cpuExceeds = form.cpus > maxCpus;
  const nameValid = /^[A-Za-z0-9._-]+$/.test(form.name.trim());

  useEffect(() => {
    if (!task || task.done) return;
    const timer = window.setInterval(async () => {
      try {
        const updated = await api.getCreationTask(task.task_id);
        setTask(updated);
        if (updated.done) {
          window.clearInterval(timer);
          if (updated.ok) {
            onToast("success", `VM "${updated.vm_name}" criada com sucesso`);
            onCreated();
          } else {
            onToast("error", "Falha ao criar VM", updated.message);
          }
        }
      } catch (e) {
        window.clearInterval(timer);
        onToast("error", "Erro ao acompanhar criação", String(e));
      }
    }, 1000);
    return () => window.clearInterval(timer);
  }, [task, onCreated, onToast]);

  const handleSubmit = async () => {
    if (!nameValid || cpuExceeds || ramExceeds || diskExceeds) return;
    setSubmitting(true);
    try {
      const res = await api.createVm(form);
      setTask({
        task_id: res.task_id,
        progress: 5,
        message: "Iniciando criação da VM...",
        log: [],
        done: false,
        ok: false,
        vm_name: form.name,
      });
    } catch (e) {
      onToast("error", "Não foi possível iniciar a criação", String(e));
    } finally {
      setSubmitting(false);
    }
  };

  if (task) {
    return (
      <Card className="mx-auto max-w-2xl p-6 space-y-4">
        <h2 className="text-lg font-semibold text-white">
          Provisionando "{task.vm_name}"
        </h2>
        <div className="h-2.5 w-full overflow-hidden rounded-full bg-[#090A10]">
          <div
            className="h-full rounded-full bg-gradient-to-r from-violet-500 via-blue-500 to-fuchsia-500 transition-all"
            style={{ width: `${task.progress}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-slate-300">
          <span>{task.message || "Processando..."}</span>
          <span>{task.progress}%</span>
        </div>
        <pre className="h-56 overflow-auto rounded-xl border border-[#292A3A] bg-[#090A10] p-3 font-mono text-xs text-slate-300">
          {task.log.join("\n") || "Aguardando logs do reims-ctl..."}
        </pre>
        {task.done && (
          <div className="flex justify-end">
            <Button variant="primary" onClick={onCreated}>
              Ir para Minhas VMs
            </Button>
          </div>
        )}
      </Card>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-white">Criar Máquina Virtual macOS</h1>
        <p className="text-xs text-slate-400">
          Configure identificação, recursos físicos, rede e acesso remoto em 5 etapas.
        </p>
      </div>

      {/* Stepper */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        {STEPS.map((s) => {
          const Icon = s.icon;
          const active = step === s.id;
          const done = step > s.id;
          return (
            <button
              key={s.id}
              onClick={() => s.id < step && setStep(s.id)}
              className={`flex items-center gap-2 rounded-xl border px-3 py-2.5 text-left text-xs font-medium transition-all ${
                active
                  ? "border-violet-500/50 bg-violet-500/15 text-white"
                  : done
                    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                    : "border-[#292A3A] bg-[#141520] text-slate-400"
              }`}
            >
              {done ? <Check className="h-3.5 w-3.5 shrink-0" /> : <Icon className="h-3.5 w-3.5 shrink-0" />}
              <span className="truncate">{s.id}. {s.title}</span>
            </button>
          );
        })}
      </div>

      <Card className="p-6">
        {step === 1 && (
          <div className="space-y-4">
            <h2 className="text-base font-semibold text-white">1. Identificação</h2>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-300">
                  Nome da VM *
                </label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full rounded-xl border border-[#292A3A] bg-[#090A10] px-3 py-2 text-sm text-white focus:border-violet-500 focus:outline-none"
                />
                {!nameValid && (
                  <p className="mt-1 text-xs text-rose-400">
                    Use apenas letras, números, ponto, hífen ou underscore.
                  </p>
                )}
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-300">
                  Versão do macOS
                </label>
                <select
                  value={form.macos_release}
                  onChange={(e) => setForm({ ...form, macos_release: e.target.value })}
                  className="w-full rounded-xl border border-[#292A3A] bg-[#090A10] px-3 py-2 text-sm text-white focus:border-violet-500 focus:outline-none"
                >
                  <option value="tahoe">macOS 26 Tahoe (Recovery Apple)</option>
                  <option value="sequoia">macOS 15 Sequoia (Recovery Apple)</option>
                  <option value="sonoma">macOS 14 Sonoma (Recovery Apple)</option>
                  <option value="ventura">macOS 13 Ventura (Recovery Apple)</option>
                </select>
              </div>
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-300">
                Descrição opcional
              </label>
              <input
                type="text"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="Ex.: Ambiente Xcode / CI iOS"
                className="w-full rounded-xl border border-[#292A3A] bg-[#090A10] px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-violet-500 focus:outline-none"
              />
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-5">
            <h2 className="text-base font-semibold text-white">2. Recursos Físicos</h2>

            {/* Host availability summary */}
            <div className="grid grid-cols-1 gap-3 rounded-xl border border-[#292A3A] bg-[#090A10] p-4 text-xs sm:grid-cols-3">
              <div>
                <span className="text-slate-400">Threads disponíveis:</span>
                <div className="mt-0.5 font-semibold text-white">{maxCpus} threads</div>
              </div>
              <div>
                <span className="text-slate-400">RAM livre p/ alocação:</span>
                <div className="mt-0.5 font-semibold text-blue-300">
                  {availableRamGb} GB de {hostRamTotalGb} GB ({reservedRamGb} GB reservados)
                </div>
              </div>
              <div>
                <span className="text-slate-400">Disco disponível:</span>
                <div className="mt-0.5 font-semibold text-emerald-300">
                  {formatBytes(host?.storage.available_bytes)}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-300">
                  vCPUs (máx. {maxCpus})
                </label>
                <input
                  type="number"
                  min={1}
                  max={maxCpus}
                  value={form.cpus}
                  onChange={(e) => setForm({ ...form, cpus: Number(e.target.value) })}
                  className="w-full rounded-xl border border-[#292A3A] bg-[#090A10] px-3 py-2 text-sm text-white"
                />
                {cpuExceeds && <p className="mt-1 text-xs text-rose-400">Excede os threads do host.</p>}
              </div>

              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-300">
                  Memória RAM (MiB — {requestedRamGb} GB)
                </label>
                <input
                  type="number"
                  min={4096}
                  step={1024}
                  max={hostRamTotalGb * 1024}
                  value={form.memory_mib}
                  onChange={(e) => setForm({ ...form, memory_mib: Number(e.target.value) })}
                  className="w-full rounded-xl border border-[#292A3A] bg-[#090A10] px-3 py-2 text-sm text-white"
                />
                {ramExceeds && (
                  <p className="mt-1 text-xs text-rose-400">Ultrapassa a RAM total do servidor.</p>
                )}
              </div>

              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-300">
                  Tamanho do disco (GB)
                </label>
                <input
                  type="number"
                  min={32}
                  max={availableDiskGb}
                  value={form.disk_size_gb}
                  onChange={(e) => setForm({ ...form, disk_size_gb: Number(e.target.value) })}
                  className="w-full rounded-xl border border-[#292A3A] bg-[#090A10] px-3 py-2 text-sm text-white"
                />
                {diskExceeds && (
                  <p className="mt-1 text-xs text-rose-400">Espaço em disco insuficiente.</p>
                )}
              </div>

              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-300">
                  GPU (reims-vgpu Vulkan)
                </label>
                <select
                  value={form.gpu_name || ""}
                  onChange={(e) => setForm({ ...form, gpu_name: e.target.value || null })}
                  className="w-full rounded-xl border border-[#292A3A] bg-[#090A10] px-3 py-2 text-sm text-white"
                >
                  <option value="">Automático (melhor GPU Vulkan)</option>
                  {gpus.map((g) => (
                    <option key={g.id_string} value={g.name}>
                      {g.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <h2 className="text-base font-semibold text-white">3. Rede</h2>
            <p className="text-xs text-slate-400">
              Nota: configurações avançadas de rede são registradas no perfil da UI; o backend atual usa virtio-net NAT por padrão.
            </p>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-300">
                  Modo de rede
                </label>
                <select
                  value={form.network_mode}
                  onChange={(e) =>
                    setForm({ ...form, network_mode: e.target.value as "user-nat" | "bridge" })
                  }
                  className="w-full rounded-xl border border-[#292A3A] bg-[#090A10] px-3 py-2 text-sm text-white"
                >
                  <option value="user-nat">QEMU User NAT (virtio-net-pci)</option>
                  <option value="bridge">Bridge LAN (requer configuração no host)</option>
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-300">
                  Endereçamento IP
                </label>
                <select
                  value={form.ip_mode}
                  onChange={(e) =>
                    setForm({ ...form, ip_mode: e.target.value as "dhcp" | "static" })
                  }
                  className="w-full rounded-xl border border-[#292A3A] bg-[#090A10] px-3 py-2 text-sm text-white"
                >
                  <option value="dhcp">DHCP automático</option>
                  <option value="static">IP estático</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-4">
            <h2 className="text-base font-semibold text-white">4. Acesso Remoto</h2>
            <label className="flex items-center gap-3 rounded-xl border border-[#292A3A] bg-[#090A10] p-4 text-sm text-slate-200 cursor-pointer">
              <input
                type="checkbox"
                checked={form.remote_access}
                onChange={(e) => setForm({ ...form, remote_access: e.target.checked })}
                className="h-4 w-4 accent-violet-500"
              />
              <div>
                <div className="font-medium">Habilitar console remoto integrado</div>
                <div className="text-xs text-slate-400">
                  Permite visualizar a tela da VM e enviar mouse/teclado diretamente pelo navegador.
                </div>
              </div>
            </label>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-300">
                Protocolo de console
              </label>
              <select
                value={form.remote_protocol}
                onChange={(e) =>
                  setForm({
                    ...form,
                    remote_protocol: e.target.value as CreateVmPayload["remote_protocol"],
                  })
                }
                className="w-full rounded-xl border border-[#292A3A] bg-[#090A10] px-3 py-2 text-sm text-white"
              >
                <option value="mjpeg-xdotool">Reims Live Stream (MJPEG + xdotool — ativo)</option>
                <option value="novnc">noVNC / WebSocket (quando disponível no QEMU)</option>
                <option value="spice">SPICE (planejado)</option>
              </select>
            </div>
          </div>
        )}

        {step === 5 && (
          <div className="space-y-4">
            <h2 className="text-base font-semibold text-white">5. Revisão Final</h2>
            <div className="grid grid-cols-2 gap-3 rounded-xl border border-[#292A3A] bg-[#090A10] p-4 text-xs sm:grid-cols-3">
              <div><span className="text-slate-400">Nome:</span> <strong className="text-white">{form.name}</strong></div>
              <div><span className="text-slate-400">macOS:</span> <strong className="text-white">{form.macos_release}</strong></div>
              <div><span className="text-slate-400">vCPUs:</span> <strong className="text-white">{form.cpus}</strong></div>
              <div><span className="text-slate-400">Memória:</span> <strong className="text-white">{requestedRamGb} GB</strong></div>
              <div><span className="text-slate-400">Disco:</span> <strong className="text-white">{form.disk_size_gb} GB</strong></div>
              <div><span className="text-slate-400">GPU:</span> <strong className="text-white">{form.gpu_name || "Automático"}</strong></div>
              <div><span className="text-slate-400">Rede:</span> <strong className="text-white">{form.network_mode} ({form.ip_mode})</strong></div>
              <div><span className="text-slate-400">Console:</span> <strong className="text-white">{form.remote_access ? form.remote_protocol : "Desativado"}</strong></div>
            </div>
          </div>
        )}

        {/* Footer nav */}
        <div className="mt-6 flex items-center justify-between border-t border-[#292A3A] pt-4">
          <Button
            variant="ghost"
            onClick={() => (step === 1 ? onCancel() : setStep((s) => s - 1))}
          >
            <ChevronLeft className="h-4 w-4" />
            {step === 1 ? "Cancelar" : "Voltar"}
          </Button>

          {step < 5 ? (
            <Button
              variant="primary"
              disabled={(step === 1 && !nameValid) || (step === 2 && (cpuExceeds || ramExceeds || diskExceeds))}
              onClick={() => setStep((s) => s + 1)}
            >
              Próximo
              <ChevronRight className="h-4 w-4" />
            </Button>
          ) : (
            <Button variant="primary" loading={submitting} onClick={handleSubmit}>
              Criar máquina virtual
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}
