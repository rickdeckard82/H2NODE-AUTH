import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import { Button, Field, Modal, useToast } from "./ui";

interface SetupOut {
  secret: string;
  otpauth_uri: string;
}

type Step = "status" | "setup" | "disable";

export function TwoFactorModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { user, refresh } = useAuth();
  const toast = useToast();
  const [step, setStep] = useState<Step>("status");
  const [setup, setSetup] = useState<SetupOut | null>(null);
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setStep("status");
    setSetup(null);
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
    mutationFn: () => api.post("/auth/mfa/enable", { code }),
    onSuccess: async () => {
      toast("ok", "2FA ativado");
      await refresh();
      close();
    },
    onError: (e) => setError(e instanceof ApiError ? e.detail : "Código inválido"),
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

  function onSubmitEnable(e: FormEvent) {
    e.preventDefault();
    setError(null);
    confirmEnable.mutate();
  }

  function onSubmitDisable(e: FormEvent) {
    e.preventDefault();
    setError(null);
    confirmDisable.mutate();
  }

  return (
    <Modal open={open} onClose={close} title="Autenticação em duas etapas (2FA)">
      {step === "status" && (
        <div className="space-y-4">
          {user?.mfa_enabled ? (
            <>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                O 2FA está <strong>ativo</strong> na sua conta.
              </p>
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
        <form className="space-y-4" onSubmit={onSubmitEnable}>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            No seu aplicativo autenticador, adicione uma conta usando esta chave (entrada
            manual — "chave baseada em tempo"):
          </p>
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

      {step === "disable" && (
        <form className="space-y-3" onSubmit={onSubmitDisable}>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Confirme sua senha e um código atual do autenticador para desativar o 2FA.
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
          <Field label="Código de verificação" error={error ?? undefined}>
            <input
              className="input text-center font-mono text-lg tracking-widest"
              inputMode="numeric"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              required
            />
          </Field>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={close}>
              Cancelar
            </Button>
            <Button type="submit" variant="danger" loading={confirmDisable.isPending} disabled={code.length !== 6}>
              Desativar 2FA
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}
