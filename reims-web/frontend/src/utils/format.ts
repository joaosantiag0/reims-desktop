import type { VmStatus } from "@/types/vm";

export function formatBytes(bytes: number | null | undefined, decimals = 1): string {
  if (bytes === null || bytes === undefined || Number.isNaN(bytes)) {
    return "Não disponível";
  }
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.min(sizes.length - 1, Math.floor(Math.log(bytes) / Math.log(k)));
  return `${(bytes / Math.pow(k, i)).toFixed(decimals)} ${sizes[i]}`;
}

export function formatUptime(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return "Não disponível";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

export const STATUS_META: Record<
  VmStatus,
  { label: string; dot: string; badge: string }
> = {
  running: {
    label: "Running",
    dot: "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.7)]",
    badge: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  },
  stopped: {
    label: "Stopped",
    dot: "bg-rose-500",
    badge: "bg-rose-500/10 text-rose-300 border-rose-500/30",
  },
  starting: {
    label: "Starting",
    dot: "bg-blue-400 animate-pulse",
    badge: "bg-blue-500/10 text-blue-300 border-blue-500/30",
  },
  stopping: {
    label: "Stopping",
    dot: "bg-amber-400 animate-pulse",
    badge: "bg-amber-500/10 text-amber-300 border-amber-500/30",
  },
  restarting: {
    label: "Restarting",
    dot: "bg-violet-400 animate-pulse",
    badge: "bg-violet-500/10 text-violet-300 border-violet-500/30",
  },
  suspended: {
    label: "Suspended",
    dot: "bg-fuchsia-400",
    badge: "bg-fuchsia-500/10 text-fuchsia-300 border-fuchsia-500/30",
  },
  error: {
    label: "Error",
    dot: "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.7)]",
    badge: "bg-red-500/15 text-red-300 border-red-500/40",
  },
};
