import { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { ConfirmModal, ToastContainer } from "@/components/ui/Primitives";
import { CreateVmPage } from "@/pages/CreateVmPage";
import { LoginPage } from "@/pages/LoginPage";
import { MonitoringPage } from "@/pages/MonitoringPage";
import { OverviewPage } from "@/pages/OverviewPage";
import { RemoteConsolePage } from "@/pages/RemoteConsolePage";
import { SettingsPage } from "@/pages/SettingsPage";
import { SnapshotsPage } from "@/pages/SnapshotsPage";
import { VmDetailPage } from "@/pages/VmDetailPage";
import { VmsPage } from "@/pages/VmsPage";
import * as api from "@/services/api";
import type {
  DoctorHealth,
  GpuDevice,
  HostOverview,
  NavPage,
  StatsSample,
  ToastMessage,
  VmInfo,
} from "@/types/vm";

export function App() {
  const [authChecked, setAuthChecked] = useState(false);
  const [authRequired, setAuthRequired] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);

  const [page, setPage] = useState<NavPage>("overview");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [selectedVmName, setSelectedVmName] = useState<string | null>(null);
  const [consoleVmName, setConsoleVmName] = useState<string | null>(null);

  const [vms, setVms] = useState<VmInfo[]>([]);
  const [host, setHost] = useState<HostOverview | null>(null);
  const [doctor, setDoctor] = useState<DoctorHealth | null>(null);
  const [gpus, setGpus] = useState<GpuDevice[]>([]);
  const [statsHistory, setStatsHistory] = useState<StatsSample[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busyMap, setBusyMap] = useState<Record<string, string | null>>({});
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const addToast = useCallback(
    (kind: ToastMessage["kind"], title: string, description?: string) => {
      const id = `${Date.now()}-${Math.random()}`;
      setToasts((prev) => [...prev.slice(-4), { id, kind, title, description }]);
      window.setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 4500);
    },
    []
  );

  const checkAuth = useCallback(async () => {
    try {
      const status = await api.getAuthStatus();
      setAuthRequired(status.auth_required);
      if (!status.auth_required) {
        setAuthenticated(true);
      } else if (api.getStoredToken()) {
        await api.listVms();
        setAuthenticated(true);
      } else {
        setAuthenticated(false);
      }
    } catch {
      setAuthenticated(false);
    } finally {
      setAuthChecked(true);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const refreshAll = useCallback(async () => {
    try {
      const [vmList, hostData, doctorData, gpuList] = await Promise.all([
        api.listVms(),
        api.getHostOverview(),
        api.getDoctor(),
        api.listGpus(),
      ]);
      setVms(vmList);
      setHost(hostData);
      setDoctor(doctorData);
      setGpus(gpuList);
    } catch (e) {
      if (e instanceof api.ApiError && e.status === 401) {
        setAuthenticated(false);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!authenticated) return;
    refreshAll();
    const vmTimer = window.setInterval(refreshAll, 5000);
    const closeWs = api.openStatsSocket(
      (sample) => {
        setStatsHistory((prev) => [...prev.slice(-59), sample]);
      },
      (connected) => setWsConnected(connected)
    );
    return () => {
      window.clearInterval(vmTimer);
      closeWs();
    };
  }, [authenticated, refreshAll]);

  const runVmAction = async (
    name: string,
    action: string,
    fn: () => Promise<void>,
    successMsg: string
  ) => {
    setBusyMap((m) => ({ ...m, [name]: action }));
    try {
      await fn();
      addToast("success", successMsg);
      await refreshAll();
    } catch (e) {
      addToast("error", `Erro ao executar ${action} em "${name}"`, String(e));
    } finally {
      setBusyMap((m) => ({ ...m, [name]: null }));
    }
  };

  const handleOpenConsole = (name: string) => {
    setConsoleVmName(name);
    setPage("remote");
  };

  const handleSelectVm = (name: string) => {
    setSelectedVmName(name);
    setPage("vm-detail");
  };

  const handleLogout = async () => {
    await api.logout();
    setAuthenticated(false);
  };

  if (!authChecked) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#090A10] text-sm text-slate-400">
        Conectando ao servidor Reims...
      </div>
    );
  }

  if (!authenticated) {
    return <LoginPage onSuccess={() => setAuthenticated(true)} />;
  }

  const runningCount = vms.filter((v) => v.status === "running").length;
  const selectedVm = vms.find((v) => v.name === selectedVmName) || null;
  const notifications: string[] = [];
  if (doctor && !doctor.all_ok) {
    notifications.push("Verifique o diagnóstico do host em Configurações.");
  }

  return (
    <div className="flex min-h-screen bg-[#090A10] text-slate-100">
      <Sidebar
        activePage={page}
        collapsed={sidebarCollapsed}
        wsConnected={wsConnected}
        hostname={host?.hostname || "localhost"}
        vmCount={vms.length}
        runningCount={runningCount}
        onNavigate={setPage}
        onToggleCollapse={() => setSidebarCollapsed((c) => !c)}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <Header
          activePage={page}
          detailVmName={selectedVmName}
          wsConnected={wsConnected}
          authRequired={authRequired}
          notifications={notifications}
          onNavigate={setPage}
          onLogout={handleLogout}
        />

        <main className="flex-1 p-6">
          {page === "overview" && (
            <OverviewPage
              host={host}
              doctor={doctor}
              gpus={gpus}
              vms={vms}
              statsHistory={statsHistory}
              loading={loading}
              busyMap={busyMap}
              onNavigate={setPage}
              onSelectVm={handleSelectVm}
              onStartVm={(n) => runVmAction(n, "start", () => api.startVm(n), `VM "${n}" iniciada`)}
              onStopVm={(n, f) => runVmAction(n, "stop", () => api.stopVm(n, f), `VM "${n}" parada`)}
              onRestartVm={(n) => runVmAction(n, "restart", () => api.restartVm(n), `VM "${n}" reiniciada`)}
              onSuspendVm={(n) => runVmAction(n, "suspend", () => api.suspendVm(n), `VM "${n}" suspensa`)}
              onOpenConsole={handleOpenConsole}
              onSnapshotVm={(n) => {
                api.createSnapshot(n, `snap-${Date.now()}`, "Snapshot rápido");
                addToast("info", `Snapshot criado para "${n}" (mock local)`);
              }}
              onCloneVm={(n) =>
                addToast("info", `Clonagem de "${n}"`, "Operação ainda não integrada ao reims-ctl.")
              }
              onDeleteVm={(n) => setDeleteTarget(n)}
            />
          )}

          {page === "vms" && (
            <VmsPage
              vms={vms}
              busyMap={busyMap}
              onNavigate={setPage}
              onSelectVm={handleSelectVm}
              onStartVm={(n) => runVmAction(n, "start", () => api.startVm(n), `VM "${n}" iniciada`)}
              onStopVm={(n, f) => runVmAction(n, "stop", () => api.stopVm(n, f), `VM "${n}" parada`)}
              onRestartVm={(n) => runVmAction(n, "restart", () => api.restartVm(n), `VM "${n}" reiniciada`)}
              onSuspendVm={(n) => runVmAction(n, "suspend", () => api.suspendVm(n), `VM "${n}" suspensa`)}
              onOpenConsole={handleOpenConsole}
              onSnapshotVm={(n) => {
                api.createSnapshot(n, `snap-${Date.now()}`, "Snapshot rápido");
                addToast("info", `Snapshot criado para "${n}" (mock local)`);
              }}
              onCloneVm={(n) =>
                addToast("info", `Clonagem de "${n}"`, "Operação ainda não integrada ao reims-ctl.")
              }
              onDeleteVm={(n) => setDeleteTarget(n)}
            />
          )}

          {page === "create" && (
            <CreateVmPage
              host={host}
              gpus={gpus}
              onCreated={() => {
                refreshAll();
                setPage("vms");
              }}
              onCancel={() => setPage("overview")}
              onToast={addToast}
            />
          )}

          {page === "monitoring" && (
            <MonitoringPage
              host={host}
              vms={vms}
              statsHistory={statsHistory}
              onToast={addToast}
            />
          )}

          {page === "remote" && (
            <RemoteConsolePage
              vms={vms}
              initialVmName={consoleVmName}
              onToast={addToast}
            />
          )}

          {page === "snapshots" && <SnapshotsPage vms={vms} onToast={addToast} />}

          {page === "settings" && (
            <SettingsPage host={host} doctor={doctor} gpus={gpus} />
          )}

          {page === "vm-detail" && selectedVm && (
            <VmDetailPage
              vm={selectedVm}
              statsHistory={statsHistory}
              onBack={() => setPage("vms")}
              onStart={(n) => runVmAction(n, "start", () => api.startVm(n), `VM "${n}" iniciada`)}
              onStop={(n, f) => runVmAction(n, "stop", () => api.stopVm(n, f), `VM "${n}" parada`)}
              onOpenConsole={handleOpenConsole}
              onToast={addToast}
            />
          )}
        </main>
      </div>

      <ConfirmModal
        open={Boolean(deleteTarget)}
        title={`Remover "${deleteTarget}"?`}
        description="Esta ação removerá permanentemente a máquina virtual e seus arquivos de disco no servidor."
        confirmLabel="Remover VM"
        loading={Boolean(deleteTarget && busyMap[deleteTarget] === "delete")}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={async () => {
          if (!deleteTarget) return;
          const target = deleteTarget;
          await runVmAction(target, "delete", () => api.deleteVm(target), `VM "${target}" removida`);
          setDeleteTarget(null);
          if (selectedVmName === target) setPage("vms");
        }}
      />

      <ToastContainer
        toasts={toasts}
        onDismiss={(id) => setToasts((prev) => prev.filter((t) => t.id !== id))}
      />
    </div>
  );
}

export default App;
