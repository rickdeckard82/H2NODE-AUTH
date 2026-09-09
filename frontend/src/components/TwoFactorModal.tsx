import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import { fmtDate } from "../lib/format";
import { Button, Field, Modal, useToast } from "./ui";

interface SetupOut {
  secret: string;
  otpauth_uri: string;
  qr_svg: string;
}

interface RecoveryOut {
  recovery_codes: string[];
}

type Step = "status" | "setup" | "recovery" | "regenerate" | "disable";

interface TrustedDevice {
  id: number;
  user_agent: string | null;
  ip_address: string | null;
  created_at: string;
  last_used_at: string | null;
  expires_at: string;
  current: boolean;
}

function shortUA(ua: string | null): string {
  if (!ua) return "Dispositivo desconhecido";
  const os = /Windows/.test(ua)
    ? "Windows"
    : /Android/.test(ua)
      ? "Android"
      : /iPhone|iPad|iOS/.test(ua)
        ? "iOS"
        : /Mac OS X|Macintosh/.test(ua)
          ? "macOS"
          : /Linux/.test(ua)
            ? "Linux"
            : "outro SO";
  const browser = /Edg\//.test(ua)
    ? "Edge"
    : /OPR\/|Opera/.test(ua)
      ? "Opera"
      : /Firefox\//.test(ua)
        ? "Firefox"
        : /Chrome\//.test(ua)
          ? "Chrome"
          : /Safari\//.test(ua)
            ? "Safari"
            : "navegador";
  return `${browser} · ${os}`;
}

function TrustedDevices() {
  const toast = useToast();
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["trusted-devices"],
    queryFn: () => api.get<TrustedDevice[]>("/auth/mfa/trusted-devices"),
  });
  const invalidate = () => qc.invalidateQueries({ queryKey: ["trusted-devices"] });
  const revoke = useMutation({
    mutationFn: (id: number) => api.del(`/auth/mfa/trusted-devices/${id}`),
    onSuccess: () => {
      toast("ok", "Dispositivo removido");
      invalidate();
    },
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : "Erro ao remover"),
  });
  const revokeAll = useMutation({
    mutationFn: () => api.del("/auth/mfa/trusted-devices"),
    onSuccess: () => {
      toast("ok", "Todos os dispositivos foram esquecidos");
      invalidate();
    },
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : "Erro ao remover"),
  });

  const devices = q.data ?? [];
  return (
    <div className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800">
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium text-slate-700 dark:text-slate-200">
          Dispositivos confiáveis
        </span>
        {devices.length > 0 && (
          <Button variant="ghost" onClick={() => revokeAll.mutate()} loading={revokeAll.isPending}>
            Esquecer todos
          </Button>
        )}
      </div>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
        Navegadores que pulam o código do 2FA no login. A validade (30 dias) renova a cada
        acesso.
      </p>
      {q.isLoading ? (
        <p className="mt-2 text-slate-400">Carregando…</p>
      ) : devices.length === 0 ? (
        <p className="mt-2 text-slate-400 dark:text-slate-500">
          Nenhum — o 2FA é pedido em todo login.
        </p>
      ) : (
        <ul className="mt-2 divide-y divide-slate-100 dark:divide-slate-800">
          {devices.map((d) => (
            <li key={d.id} className="flex items-center justify-between gap-3 py-2">
              <div className="min-w-0">
                <div className="truncate text-slate-700 dark:text-slate-200">
                  {shortUA(d.user_agent)}
                  {d.current && (
                    <span className="ml-1 text-xs text-brand-600 dark:text-brand-400">
                      (este dispositivo)
                    </span>
                  )}
                </div>
                <div className="text-xs text-slate-400 dark:text-slate-500">
                  {d.ip_address ?? "IP desconhecido"} · expira {fmtDate(d.expires_at)}
                </div>
              </div>
              <button
                type="button"
                className="shrink-0 text-rose-600 hover:underline dark:text-rose-400"
                onClick={() => revoke.mutate(d.id)}
              >
                Remover
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function RecoveryCodes({ codes }: { codes: string[] }) {
  const toast = useToast();
  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Guarde estes <strong>códigos de recuperação</strong> num lugar seguro. Cada um
        funciona <strong>uma única vez</strong> e serve para entrar ou desativar o 2FA se
        você perder o aplicativo autenticador.
      </p>
      <div className="grid grid-cols-2 gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 text-center font-mono text-sm dark:border-slate-800 dark:bg-slate-800/50">
        {codes.map((c) => (
          <span key={c} className="tracking-wider">
            {c}
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <Button
          type="button"
          variant="ghost"
          onClick={() => {
            navigator.clipboard
              .writeText(codes.join("\n"))
              .then(() => toast("ok", "Códigos copiados"))
              .catch(() => toast("err", "Não foi possível copiar"));
          }}
        >
          Copiar
        </Button>
        <Button
          type="button"
          variant="ghost"
          onClick={() => {
            const blob = new Blob([codes.join("\n") + "\n"], { type: "text/plain" });
            const a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = "pulse-radius-codigos-recuperacao.txt";
            a.click();
            URL.revokeObjectURL(a.href);
          }}
        >
          Baixar .txt
        </Button>
      </div>
    </div>
  );
}

export function TwoFactorModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { user, refresh } = useAuth();
  const toast = useToast();
  const [step, setStep] = useState<Step>("status");
  const [setup, setSetup] = useState<SetupOut | null>(null);
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setStep("status");
    setSetup(null);
    setRecoveryCodes(null);
    setCode("");
    setPassword("");
    setError(null);
  }

  function close() {
    reset();
    onClose();
  }

  const startSetup = useMutation({
    mutationFn: () => api.post<SetupOut>("/auth/mfa/setup"),
    onSuccess: (res) => {
      setSetup(res);
      setStep("setup");
    },
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : "Erro ao iniciar o 2FA"),
  });

  const confirmEnable = useMutation({
    mutationFn: () => api.post<{ detail: string } & RecoveryOut>("/auth/mfa/enable", { code }),
    onSuccess: async (res) => {
      toast("ok", "2FA ativado");
      await refresh();
      setRecoveryCodes(res.recovery_codes);
      setCode("");
      setPassword("");
      setError(null);
      setStep("recovery");
    },
    onError: (e) => setError(e instanceof ApiError ? e.detail : "Código inválido"),
  });

  const regenerate = useMutation({
    mutationFn: () =>
      api.post<RecoveryOut>("/auth/mfa/recovery-codes/regenerate", { password, code }),
    onSuccess: (res) => {
      toast("ok", "Novos códigos gerados");
      setRecoveryCodes(res.recovery_codes);
      setCode("");
      setPassword("");
      setError(null);
      setStep("recovery");
    },
    onError: (e) => setError(e instanceof ApiError ? e.detail : "Senha ou código inválido"),
  });

  const confirmDisable = useMutation({
    mutationFn: () => api.post("/auth/mfa/disable", { password, code }),
    onSuccess: async () => {
      toast("ok", "2FA desativado");
      await refresh();
      close();
    },
    onError: (e) => setError(e instanceof ApiError ? e.detail : "Senha ou código inválido"),
  });

  function submit(fn: () => void) {
    return (e: FormEvent) => {
      e.preventDefault();
      setError(null);
      fn();
    };
  }

  const remaining = user?.mfa_recovery_codes_remaining ?? 0;

  return (
    <Modal open={open} onClose={close} title="Autenticação em duas etapas (2FA)">
      {step === "status" && (
        <div className="space-y-4">
          {user?.mfa_enabled ? (
            <>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                O 2FA está <strong>ativo</strong> na sua conta.
              </p>
              <div className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-slate-600 dark:text-slate-300">
                    Códigos de recuperação restantes:{" "}
                    <strong className={remaining <= 2 ? "text-red-600 dark:text-red-400" : ""}>
                      {remaining}
                    </strong>
                  </span>
                  <Button variant="ghost" onClick={() => setStep("regenerate")}>
                    Gerar novos
                  </Button>
                </div>
                {remaining <= 2 && (
                  <p className="mt-2 text-xs text-red-600 dark:text-red-400">
                    Você está quase sem códigos — gere um lote novo e guarde-o.
                  </p>
                )}
              </div>
              <TrustedDevices />
              <div className="flex justify-end gap-2">
                <Button variant="ghost" onClick={close}>
                  Fechar
                </Button>
                <Button variant="danger" onClick={() => setStep("disable")}>
                  Desativar 2FA
                </Button>
              </div>
            </>
          ) : (
            <>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                O 2FA está <strong>desativado</strong>. Ative para exigir um código do seu
                aplicativo autenticador (Google Authenticator, Authy, 1Password…) a cada login.
              </p>
              <div className="flex justify-end gap-2">
                <Button variant="ghost" onClick={close}>
                  Fechar
                </Button>
                <Button loading={startSetup.isPending} onClick={() => startSetup.mutate()}>
                  Ativar 2FA
                </Button>
              </div>
            </>
          )}
        </div>
      )}

      {step === "setup" && setup && (
        <form className="space-y-4" onSubmit={submit(() => confirmEnable.mutate())}>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            No seu aplicativo autenticador, escaneie o QR code abaixo — ou adicione a conta
            manualmente com esta chave ("chave baseada em tempo"):
          </p>
          <div className="flex justify-center">
            <img
              src={setup.qr_svg}
              alt="QR code para configurar o 2FA no aplicativo autenticador"
              className="h-48 w-48 rounded-lg border border-slate-200 bg-white p-2 dark:border-slate-700"
            />
          </div>
          <div className="break-all rounded-lg border border-slate-200 bg-slate-50 p-3 text-center font-mono text-sm tracking-wider dark:border-slate-800 dark:bg-slate-800/50">
            {setup.secret}
          </div>
          <p className="text-xs text-slate-400 dark:text-slate-500">
            Alguns apps aceitam colar o link diretamente:{" "}
            <span className="break-all font-mono">{setup.otpauth_uri}</span>
          </p>
          <Field label="Código gerado pelo app" error={error ?? undefined}>
            <input
              className="input text-center font-mono text-lg tracking-widest"
              inputMode="numeric"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              required
              autoFocus
            />
          </Field>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={close}>
              Cancelar
            </Button>
            <Button type="submit" loading={confirmEnable.isPending} disabled={code.length !== 6}>
              Confirmar e ativar
            </Button>
          </div>
        </form>
      )}

      {step === "recovery" && recoveryCodes && (
        <div className="space-y-4">
          <RecoveryCodes codes={recoveryCodes} />
          <div className="flex justify-end">
            <Button onClick={close}>Já guardei os códigos</Button>
          </div>
        </div>
      )}

      {step === "regenerate" && (
        <form className="space-y-3" onSubmit={submit(() => regenerate.mutate())}>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Confirme sua senha e um código atual (do autenticador ou um código de
            recuperação ainda válido). Os códigos anteriores deixam de funcionar.
          </p>
          <Field label="Senha atual">
            <input
              className="input"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoFocus
            />
          </Field>
          <Field label="Código do autenticador ou de recuperação" error={error ?? undefined}>
            <input
              className="input text-center font-mono text-lg tracking-widest"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              required
            />
          </Field>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={() => setStep("status")}>
              Cancelar
            </Button>
            <Button
              type="submit"
              loading={regenerate.isPending}
              disabled={code.trim().length < 6 || !password}
            >
              Gerar novos códigos
            </Button>
          </div>
        </form>
      )}

      {step === "disable" && (
        <form className="space-y-3" onSubmit={submit(() => confirmDisable.mutate())}>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Confirme sua senha e um código para desativar o 2FA — pode ser o código atual
            do autenticador ou um dos seus códigos de recuperação.
          </p>
          <Field label="Senha atual">
            <input
              className="input"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoFocus
            />
          </Field>
          <Field label="Código do autenticador ou de recuperação" error={error ?? undefined}>
            <input
              className="input text-center font-mono text-lg tracking-widest"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              required
            />
          </Field>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={close}>
              Cancelar
            </Button>
            <Button
              type="submit"
              variant="danger"
              loading={confirmDisable.isPending}
              disabled={code.trim().length < 6 || !password}
            >
              Desativar 2FA
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}
