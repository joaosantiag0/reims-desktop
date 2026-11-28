import React from "react";
import {
  Activity,
  Camera,
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
  Monitor,
  PlusCircle,
  Server,
  Settings,
  Terminal,
} from "lucide-react";
import type { NavPage } from "@/types/vm";

interface SidebarProps {
  activePage: NavPage;
  collapsed: boolean;
  wsConnected: boolean;
  hostname: string;
  vmCount: number;
  runningCount: number;
  onNavigate: (page: NavPage) => void;
  onToggleCollapse: () => void;
}

const NAV_ITEMS: { id: NavPage; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "vms", label: "Minhas VMs", icon: Server },
  { id: "create", label: "Criar VM", icon: PlusCircle },
  { id: "monitoring", label: "Monitoramento", icon: Activity },
  { id: "remote", label: "Acesso remoto", icon: Terminal },
  { id: "snapshots", label: "Snapshots e backups", icon: Camera },
  { id: "settings", label: "Configurações", icon: Settings },
];

export function Sidebar({
  activePage,
  collapsed,
  wsConnected,
  hostname,
  vmCount,
  runningCount,
  onNavigate,
  onToggleCollapse,
}: SidebarProps) {
  return (
    <aside
      className={`flex shrink-0 flex-col border-r border-[#292A3A] bg-[#0D0E17] transition-all duration-200 ${
        collapsed ? "w-[74px]" : "w-64"
      }`}
    >
      {/* Brand header */}
      <div className="flex h-16 items-center justify-between border-b border-[#292A3A] px-3.5">
        <button
          onClick={() => onNavigate("overview")}
          className="flex items-center gap-3 overflow-hidden text-left"
        >
          <img
            src="/logo.png"
            alt="Reims Desktop"
            className="h-9 w-9 shrink-0 rounded-xl border border-[#292A3A] object-cover shadow-[0_0_16px_rgba(139,92,246,0.28)]"
          />
          {!collapsed && (
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold tracking-tight text-white">
                Reims Cloud
              </div>
              <div className="truncate text-[11px] text-slate-400">
                macOS Hypervisor
              </div>
            </div>
          )}
        </button>
        <button
          onClick={onToggleCollapse}
          title={collapsed ? "Expandir menu" : "Recolher menu"}
          className="rounded-lg p-1.5 text-slate-400 hover:bg-white/5 hover:text-white"
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-3">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const active =
            activePage === item.id ||
            (activePage === "vm-detail" && item.id === "vms");
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              title={collapsed ? item.label : undefined}
              className={`group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all ${
                active
                  ? "bg-gradient-to-r from-violet-600/20 via-indigo-600/15 to-transparent text-white border border-violet-500/30 shadow-[inset_2px_0_0_#8B5CF6]"
                  : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-100 border border-transparent"
              }`}
            >
              <Icon
                className={`h-4 w-4 shrink-0 ${
                  active ? "text-violet-400" : "text-slate-400 group-hover:text-slate-200"
                }`}
              />
              {!collapsed && <span className="truncate">{item.label}</span>}
              {!collapsed && item.id === "vms" && vmCount > 0 && (
                <span className="ml-auto rounded-md bg-[#1D1F2E] px-1.5 py-0.5 text-[11px] text-slate-300">
                  {runningCount}/{vmCount}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom host status & profile */}
      <div className="border-t border-[#292A3A] p-3 space-y-2.5">
        {!collapsed ? (
          <>
            <div className="rounded-xl border border-[#292A3A] bg-[#141520] p-2.5">
              <div className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5 text-slate-300 font-medium">
                  <Monitor className="h-3.5 w-3.5 text-blue-400" />
                  <span className="truncate max-w-[115px]">{hostname || "localhost"}</span>
                </span>
                <span
                  className={`h-2 w-2 rounded-full ${
                    wsConnected
                      ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]"
                      : "bg-amber-400"
                  }`}
                />
              </div>
              <div className="mt-1 flex items-center justify-between text-[11px] text-slate-500">
                <span>ReimsOS v0.1.0</span>
                <span>{wsConnected ? "Online" : "Polling"}</span>
              </div>
            </div>
            <div className="flex items-center gap-2.5 px-1">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-fuchsia-500 text-xs font-bold text-white">
                AD
              </div>
              <div className="min-w-0">
                <div className="truncate text-xs font-medium text-slate-200">
                  Administrador
                </div>
                <div className="truncate text-[11px] text-slate-500">
                  KVM + reims-vgpu
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <span
              title={wsConnected ? "Servidor conectado" : "Reconectando"}
              className={`h-2.5 w-2.5 rounded-full ${
                wsConnected ? "bg-emerald-400" : "bg-amber-400"
              }`}
            />
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-fuchsia-500 text-xs font-bold text-white">
              AD
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
