import React, { useEffect, useRef, useState } from "react";
import {
  Maximize2,
  Monitor,
  Plug,
  RefreshCw,
  Send,
  Unplug,
  Wifi,
} from "lucide-react";
import { Button, Card } from "@/components/ui/Primitives";
import * as api from "@/services/api";
import type { ConsoleInfo, VmInfo } from "@/types/vm";

export function RemoteConsolePage({
  vms,
  initialVmName,
  onToast,
}: {
  vms: VmInfo[];
  initialVmName?: string | null;
  onToast: (kind: "success" | "error" | "info", title: string, desc?: string) => void;
}) {
  const [selectedVm, setSelectedVm] = useState<string>(
    initialVmName || vms[0]?.name || ""
  );
  const [protocol, setProtocol] = useState<"mjpeg" | "novnc" | "spice" | "vnc">("mjpeg");
  const [quality, setQuality] = useState<"high" | "balanced" | "low">("balanced");
  const [connected, setConnected] = useState(false);
  const [info, setInfo] = useState<ConsoleInfo | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [textInput, setTextInput] = useState("");
  const [streamKey, setStreamKey] = useState(0);

  const stageRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const lastMoveRef = useRef<number>(0);

  useEffect(() => {
    if (initialVmName) setSelectedVm(initialVmName);
  }, [initialVmName]);

  const connect = async (vmName = selectedVm) => {
    if (!vmName) return;
    const t0 = performance.now();
    try {
      const res = await api.getConsoleInfo(vmName);
      setLatencyMs(Math.round(performance.now() - t0));
      setInfo(res);
      if (!res.available) {
        setConnected(false);
        onToast("error", "Console indisponível", res.reason || "Display X11 não encontrado");
        return;
      }
      setConnected(true);
      setStreamKey((k) => k + 1);
      window.setTimeout(() => imgRef.current?.focus(), 100);
    } catch (e) {
      setConnected(false);
      onToast("error", "Falha ao conectar ao console", String(e));
    }
  };

  const disconnect = () => {
    setConnected(false);
    setInfo(null);
  };

  useEffect(() => {
    if (selectedVm && initialVmName) {
      connect(selectedVm);
    }
  }, [initialVmName]);

  const sendInput = (payload: Record<string, unknown>) => {
    if (!info?.input_url || !connected) return;
    api.sendConsoleInput(info.input_url, payload).catch(() => {});
  };

  const normCoords = (ev: React.MouseEvent<HTMLImageElement>) => {
    const rect = ev.currentTarget.getBoundingClientRect();
    if (!rect.width || !rect.height) return { x: 0.5, y: 0.5 };
    return {
      x: Math.max(0, Math.min(1, (ev.clientX - rect.left) / rect.width)),
      y: Math.max(0, Math.min(1, (ev.clientY - rect.top) / rect.height)),
    };
  };

  const handleSendText = (e: React.FormEvent) => {
    e.preventDefault();
    if (!textInput) return;
    sendInput({ type: "text", text: textInput });
    setTextInput("");
    imgRef.current?.focus();
  };

  const toggleFullscreen = () => {
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
    } else {
      stageRef.current?.requestFullscreen().catch(() => {});
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-white">Acesso Remoto</h1>
          <p className="text-xs text-slate-400">
            Streaming de tela ao vivo e envio de mouse/teclado para o display da VM.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            value={selectedVm}
            onChange={(e) => setSelectedVm(e.target.value)}
            className="rounded-lg border border-[#292A3A] bg-[#141520] px-3 py-1.5 text-xs text-white"
          >
            {vms.length === 0 && <option value="">Nenhuma VM</option>}
            {vms.map((v) => (
              <option key={v.name} value={v.name}>
                {v.name} ({v.status})
              </option>
            ))}
          </select>

          <select
            value={protocol}
            onChange={(e) => setProtocol(e.target.value as typeof protocol)}
            className="rounded-lg border border-[#292A3A] bg-[#141520] px-3 py-1.5 text-xs text-white"
          >
            <option value="mjpeg">Live Stream (MJPEG + xdotool)</option>
            <option value="novnc">noVNC (WebSocket)</option>
            <option value="spice">SPICE</option>
            <option value="vnc">VNC nativo</option>
          </select>

          <select
            value={quality}
            onChange={(e) => setQuality(e.target.value as typeof quality)}
            className="rounded-lg border border-[#292A3A] bg-[#141520] px-3 py-1.5 text-xs text-white"
          >
            <option value="high">Qualidade: Alta</option>
            <option value="balanced">Qualidade: Balanceada</option>
            <option value="low">Qualidade: Baixa</option>
          </select>

          {!connected ? (
            <Button variant="primary" size="sm" onClick={() => connect()} disabled={!selectedVm}>
              <Plug className="h-3.5 w-3.5" />
              Conectar
            </Button>
          ) : (
            <>
              <Button variant="secondary" size="sm" onClick={() => connect()}>
                <RefreshCw className="h-3.5 w-3.5" />
                Reconectar
              </Button>
              <Button variant="danger" size="sm" onClick={disconnect}>
                <Unplug className="h-3.5 w-3.5" />
                Desconectar
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Console toolbar + viewport */}
      <Card className="overflow-hidden p-3 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-3">
            <span
              className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-medium ${
                connected
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                  : "border-[#292A3A] bg-[#090A10] text-slate-400"
              }`}
            >
              <Wifi className="h-3 w-3" />
              {connected ? "Conectado" : "Desconectado"}
            </span>
            {info?.width && info?.height && (
              <span className="text-slate-400 font-mono">
                {info.width}×{info.height}
              </span>
            )}
            {latencyMs !== null && (
              <span className="text-slate-400">Latência API: {latencyMs} ms</span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <form onSubmit={handleSendText} className="flex items-center gap-1.5">
              <input
                type="text"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="Enviar texto para a VM..."
                disabled={!connected}
                className="w-48 rounded-lg border border-[#292A3A] bg-[#090A10] px-2.5 py-1 text-xs text-white placeholder-slate-500"
              />
              <Button type="submit" variant="secondary" size="sm" disabled={!connected}>
                <Send className="h-3 w-3" />
                Enviar
              </Button>
            </form>
            <Button variant="secondary" size="sm" onClick={toggleFullscreen} disabled={!connected}>
              <Maximize2 className="h-3.5 w-3.5" />
              Tela cheia
            </Button>
          </div>
        </div>

        <div
          ref={stageRef}
          className="flex min-h-[460px] items-center justify-center rounded-xl border border-[#292A3A] bg-[#05060A] overflow-hidden"
        >
          {connected && info?.stream_url && protocol === "mjpeg" ? (
            <img
              key={streamKey}
              ref={imgRef}
              src={api.buildStreamUrl(info.stream_url)}
              alt={`Console ${selectedVm}`}
              tabIndex={0}
              draggable={false}
              onContextMenu={(e) => e.preventDefault()}
              onMouseDown={(e) => {
                e.preventDefault();
                e.currentTarget.focus();
                const { x, y } = normCoords(e);
                const button = e.button === 2 ? 3 : e.button === 1 ? 2 : 1;
                sendInput({ type: "mousedown", x, y, button });
              }}
              onMouseUp={(e) => {
                e.preventDefault();
                const { x, y } = normCoords(e);
                const button = e.button === 2 ? 3 : e.button === 1 ? 2 : 1;
                sendInput({ type: "mouseup", x, y, button });
              }}
              onMouseMove={(e) => {
                const now = performance.now();
                if (now - lastMoveRef.current < 50) return;
                lastMoveRef.current = now;
                const { x, y } = normCoords(e);
                sendInput({ type: "mousemove", x, y });
              }}
              onWheel={(e) => {
                e.preventDefault();
                const { x, y } = normCoords(e);
                sendInput({ type: "wheel", x, y, deltaY: e.deltaY });
              }}
              onKeyDown={(e) => {
                e.preventDefault();
                sendInput({ type: "keydown", key: e.key });
              }}
              onKeyUp={(e) => {
                e.preventDefault();
                sendInput({ type: "keyup", key: e.key });
              }}
              className="max-h-[75vh] w-full object-contain cursor-crosshair outline-none select-none"
            />
          ) : (
            <div className="p-8 text-center">
              <Monitor className="mx-auto h-12 w-12 text-slate-600" />
              <h3 className="mt-3 text-sm font-medium text-white">
                {protocol !== "mjpeg"
                  ? `Protocolo ${protocol.toUpperCase()} aguardando suporte no backend`
                  : "Console desconectado"}
              </h3>
              <p className="mt-1 max-w-md text-xs text-slate-400">
                {protocol !== "mjpeg"
                  ? "Selecione 'Live Stream (MJPEG + xdotool)' para visualizar e controlar a tela da VM em tempo real."
                  : "Selecione uma VM e clique em Conectar para iniciar o stream de vídeo e controle remoto."}
              </p>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
