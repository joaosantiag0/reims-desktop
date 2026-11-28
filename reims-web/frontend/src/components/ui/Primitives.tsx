import React from "react";
import { AlertTriangle, CheckCircle2, Info, X, XCircle } from "lucide-react";
import type { ToastMessage } from "@/types/vm";

export function Card({
  children,
  className = "",
  onClick,
}: {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className={`rounded-xl border border-[#292A3A] bg-[#141520] transition-colors ${className}`}
    >
      {children}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-lg bg-[#1E2030] ${className}`}
      aria-hidden="true"
    />
  );
}

export function Button({
  children,
  variant = "secondary",
  size = "md",
  className = "",
  disabled,
  loading,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md";
  loading?: boolean;
}) {
  const variants = {
    primary:
      "bg-gradient-to-r from-violet-600 via-indigo-600 to-blue-600 text-white hover:from-violet-500 hover:to-blue-500 shadow-[0_0_20px_rgba(124,58,237,0.28)] border border-violet-400/20",
    secondary:
      "bg-[#1B1D2B] text-slate-200 hover:bg-[#232638] border border-[#292A3A]",
    ghost:
      "bg-transparent text-slate-300 hover:bg-white/5 hover:text-white border border-transparent",
    danger:
      "bg-rose-500/15 text-rose-300 hover:bg-rose-500/25 border border-rose-500/30",
  };
  const sizes = {
    sm: "px-2.5 py-1.5 text-xs rounded-lg gap-1.5",
    md: "px-3.5 py-2 text-sm rounded-lg gap-2",
  };

  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center font-medium transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${variants[variant]} ${sizes[size]} ${className}`}
    >
      {loading && (
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
      )}
      {children}
    </button>
  );
}

export function ConfirmModal({
  open,
  title,
  description,
  confirmLabel = "Confirmar",
  danger = true,
  loading = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  danger?: boolean;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl border border-[#292A3A] bg-[#141520] p-6 shadow-2xl">
        <div className="flex items-start gap-3">
          <div
            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border ${
              danger
                ? "border-rose-500/30 bg-rose-500/10 text-rose-400"
                : "border-violet-500/30 bg-violet-500/10 text-violet-400"
            }`}
          >
            <AlertTriangle className="h-5 w-5" />
          </div>
          <div className="flex-1">
            <h3 className="text-base font-semibold text-white">{title}</h3>
            <p className="mt-1.5 text-sm text-slate-400">{description}</p>
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-2.5">
          <Button variant="ghost" onClick={onCancel} disabled={loading}>
            Cancelar
          </Button>
          <Button
            variant={danger ? "danger" : "primary"}
            onClick={onConfirm}
            loading={loading}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}

export function ToastContainer({
  toasts,
  onDismiss,
}: {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}) {
  if (toasts.length === 0) return null;
  return (
    <div className="fixed right-4 bottom-4 z-50 flex w-full max-w-sm flex-col gap-2">
      {toasts.map((t) => {
        const icon =
          t.kind === "success" ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          ) : t.kind === "error" ? (
            <XCircle className="h-4 w-4 text-rose-400" />
          ) : (
            <Info className="h-4 w-4 text-blue-400" />
          );
        const border =
          t.kind === "success"
            ? "border-emerald-500/30"
            : t.kind === "error"
              ? "border-rose-500/30"
              : "border-blue-500/30";
        return (
          <div
            key={t.id}
            className={`glass-surface flex items-start gap-3 rounded-xl border ${border} p-3.5 shadow-xl`}
          >
            <div className="mt-0.5 shrink-0">{icon}</div>
            <div className="min-w-0 flex-1">
              <div className="text-sm font-medium text-slate-100">{t.title}</div>
              {t.description && (
                <div className="mt-0.5 text-xs text-slate-400">{t.description}</div>
              )}
            </div>
            <button
              onClick={() => onDismiss(t.id)}
              className="text-slate-500 hover:text-slate-200"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
