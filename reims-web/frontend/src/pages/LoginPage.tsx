import React, { useState } from "react";
import { Lock } from "lucide-react";
import { Button } from "@/components/ui/Primitives";
import * as api from "@/services/api";

export function LoginPage({ onSuccess }: { onSuccess: () => void }) {
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.login(password);
      onSuccess();
    } catch {
      setError("Senha inválida. Verifique as credenciais do servidor.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#090A10] p-4">
      <img
        src="/wallpaper.png"
        alt=""
        className="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-30"
      />
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-[#090A10]/60 via-[#090A10]/80 to-[#090A10]" />

      <div className="glass-surface relative z-10 w-full max-w-md rounded-2xl border border-[#292A3A] p-8 shadow-2xl">
        <div className="flex flex-col items-center text-center">
          <img
            src="/logo.png"
            alt="Reims Desktop"
            className="h-16 w-16 rounded-2xl border border-[#292A3A] shadow-[0_0_30px_rgba(139,92,246,0.35)]"
          />
          <h1 className="mt-4 text-xl font-semibold tracking-tight text-white">
            Reims Cloud Console
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Plataforma de virtualização macOS acelerada
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-300">
              Senha do administrador
            </label>
            <div className="relative">
              <Lock className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-500" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full rounded-xl border border-[#292A3A] bg-[#090A10]/80 py-2.5 pr-3 pl-9 text-sm text-white placeholder-slate-500 focus:border-violet-500 focus:outline-none"
              />
            </div>
          </div>

          {error && (
            <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
              {error}
            </div>
          )}

          <Button type="submit" variant="primary" className="w-full" loading={loading}>
            Entrar no painel
          </Button>
        </form>
      </div>
    </div>
  );
}
