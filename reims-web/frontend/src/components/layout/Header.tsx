import { useState } from "react";
import { Bell, LogOut, Plus, ShieldCheck, User, Wifi, WifiOff } from "lucide-react";
import { Button } from "@/components/ui/Primitives";
import type { NavPage } from "@/types/vm";

const BREADCRUMBS: Record<NavPage, string> = {
  overview: "Overview",
  vms: "Minhas VMs",
  create: "Criar Máquina Virtual",
  monitoring: "Monitoramento & Alertas",
  remote: "Acesso Remoto",
  snapshots: "Snapshots e Backups",
  settings: "Configurações",
  "vm-detail": "Detalhes da VM",
};

export function Header({
  activePage,
  detailVmName,
  wsConnected,
  authRequired,
  notifications,
  onNavigate,
  onLogout,
}: {
  activePage: NavPage;
  detailVmName?: string | null;
  wsConnected: boolean;
  authRequired: boolean;
  notifications: string[];
  onNavigate: (page: NavPage) => void;
  onLogout: () => void;
}) {
  const [showNotifs, setShowNotifs] = useState(false);
  const [showUser, setShowUser] = useState(false);

  return (
    <header className="glass-surface sticky top-0 z-30 flex h-16 shrink-0 items-center justify-between border-b border-[#292A3A] px-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        <button
          onClick={() => onNavigate("overview")}
          className="text-slate-400 hover:text-white transition-colors"
        >
          Reims Cloud
        </button>
        <span className="text-slate-600">/</span>
        <span className="font-medium text-white">
          {BREADCRUMBS[activePage]}
        </span>
        {activePage === "vm-detail" && detailVmName && (
          <>
            <span className="text-slate-600">/</span>
            <span className="rounded-md border border-violet-500/30 bg-violet-500/10 px-2 py-0.5 text-xs font-medium text-violet-300">
              {detailVmName}
            </span>
          </>
        )}
      </div>

      {/* Right actions */}
      <div className="flex items-center gap-3">
        {/* Connection pill */}
        <div
          className={`hidden sm:flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${
            wsConnected
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
              : "border-amber-500/30 bg-amber-500/10 text-amber-300"
          }`}
        >
          {wsConnected ? <Wifi className="h-3.5 w-3.5" /> : <WifiOff className="h-3.5 w-3.5" />}
          <span>{wsConnected ? "Tempo real ativo" : "Modo polling"}</span>
        </div>

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => {
              setShowNotifs((v) => !v);
              setShowUser(false);
            }}
            className="relative rounded-lg border border-[#292A3A] bg-[#141520] p-2 text-slate-300 hover:bg-[#1C1E2C] hover:text-white"
            title="Notificações"
          >
            <Bell className="h-4 w-4" />
            {notifications.length > 0 && (
              <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-fuchsia-500 text-[10px] font-bold text-white">
                {notifications.length}
              </span>
            )}
          </button>
          {showNotifs && (
            <div className="absolute right-0 mt-2 w-72 rounded-xl border border-[#292A3A] bg-[#141520] p-3 shadow-2xl">
              <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                Notificações
              </div>
              {notifications.length === 0 ? (
                <p className="py-3 text-center text-xs text-slate-500">
                  Nenhum alerta ativo no momento.
                </p>
              ) : (
                <ul className="space-y-1.5">
                  {notifications.map((n, i) => (
                    <li
                      key={i}
                      className="rounded-lg border border-amber-500/20 bg-amber-500/10 px-2.5 py-2 text-xs text-amber-200"
                    >
                      {n}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>

        {/* User menu */}
        <div className="relative">
          <button
            onClick={() => {
              setShowUser((v) => !v);
              setShowNotifs(false);
            }}
            className="flex items-center gap-2 rounded-lg border border-[#292A3A] bg-[#141520] px-2.5 py-1.5 text-xs text-slate-200 hover:bg-[#1C1E2C]"
          >
            <User className="h-3.5 w-3.5 text-violet-400" />
            <span className="hidden md:inline">Admin</span>
          </button>
          {showUser && (
            <div className="absolute right-0 mt-2 w-52 rounded-xl border border-[#292A3A] bg-[#141520] p-2 shadow-2xl">
              <div className="flex items-center gap-2 px-2.5 py-2 text-xs text-slate-300">
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                <span>{authRequired ? "Sessão autenticada" : "Modo aberto (LAN/dev)"}</span>
              </div>
              {authRequired && (
                <button
                  onClick={onLogout}
                  className="mt-1 flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-xs text-rose-300 hover:bg-rose-500/10"
                >
                  <LogOut className="h-3.5 w-3.5" />
                  Sair da sessão
                </button>
              )}
            </div>
          )}
        </div>

        {/* Quick Create VM */}
        <Button variant="primary" size="sm" onClick={() => onNavigate("create")}>
          <Plus className="h-3.5 w-3.5" />
          <span>Criar VM</span>
        </Button>
      </div>
    </header>
  );
}
