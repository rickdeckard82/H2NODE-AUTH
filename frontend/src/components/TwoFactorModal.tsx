import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import { fmtDate } from "../lib/format";
import { useT } from "../lib/i18n";
import { shortUA } from "../lib/ua";
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

function TrustedDevices() {
  const toast = useToast();
  const t = useT();
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["trusted-devices"],
    queryFn: () => api.get<TrustedDevice[]>("/auth/mfa/trusted-devices"),
  });
  const invalidate = () => qc.invalidateQueries({ queryKey: ["trusted-devices"] });
  const revoke = useMutation({
    mutationFn: (id: number) => api.del(`/auth/mfa/trusted-devices/${id}`),
    onSuccess: () => {
      toast("ok", t("Dispositivo removido"));
      invalidate();
    },
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : t("Erro ao remover")),
  });
  const revokeAll = useMutation({
    mutationFn: () => api.del("/auth/mfa/trusted-devices"),
    onSuccess: () => {
      toast("ok", t("Todos os dispositivos foram esquecidos"));
      invalidate();
    },
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : t("Erro ao remover")),
  });

  const devices = q.data ?? [];
  return (
    <div className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800">
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium text-slate-700 dark:text-slate-200">
          {t("Dispositivos confiáveis")}
        </span>
        {devices.length > 0 && (
          <Button variant="ghost" onClick={() => revokeAll.mutate()} loading={revokeAll.isPending}>
            {t("Esquecer todos")}
          </Button>
        )}
      </div>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
        {t("Navegadores que pulam o código do 2FA no login. A validade (30 dias) renova a cada acesso.")}
      </p>
      {q.isLoading ? (
        <p className="mt-2 text-slate-400">{t("Carregando")}…</p>
      ) : devices.length === 0 ? (
        <p className="mt-2 text-slate-400 dark:text-slate-500">
          {t("Nenhum — o 2FA é pedido em todo login.")}
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
                      {t("(este dispositivo)")}
                    </span>
                  )}
                </div>
                <div className="text-xs text-slate-400 dark:text-slate-500">
                  {d.ip_address ?? t("IP desconhecido")} · {t("expira {data}", { data: fmtDate(d.expires_at) })}
                </div>
              </div>
              <button
                type="button"
                className="shrink-0 text-rose-600 hover:underline dark:text-rose-400"
                onClick={() => revoke.mutate(d.id)}
              >
                {t("Remover")}
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
  const t = useT();
  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-600 dark:text-slate-300">
        {t("Guarde estes códigos de recuperação num lugar seguro. Cada um funciona uma única vez e serve para entrar ou desativar o 2FA se você perder o aplicativo autenticador.")}
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
              .then(() => toast("ok", t("Códigos copiados")))
              .catch(() => toast("err", t("Não foi possível copiar")));
          }}
        >
          {t("Copiar")}
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
          {t("Baixar .txt")}
        </Button>
      </div>
    </div>
  );
}

export function TwoFactorModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { user, refresh } = useAuth();
  const toast = useToast();
  const t = useT();
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
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : t("Erro ao iniciar o 2FA")),
  });

  const confirmEnable = useMutation({
    mutationFn: () => api.post<{ detail: string } & RecoveryOut>("/auth/mfa/enable", { code }),
    onSuccess: async (res) => {
      toast("ok", t("2FA ativado"));
      await refresh();
      setRecoveryCodes(res.recovery_codes);
      setCode("");
      setPassword("");
      setError(null);
      setStep("recovery");
    },
    onError: (e) => setError(e instanceof ApiError ? e.detail : t("Código inválido")),
  });

  const regenerate = useMutation({
    mutationFn: () =>
      api.post<RecoveryOut>("/auth/mfa/recovery-codes/regenerate", { password, code }),
    onSuccess: (res) => {
      toast("ok", t("Novos códigos gerados"));
      setRecoveryCodes(res.recovery_codes);
      setCode("");
      setPassword("");
      setError(null);
      setStep("recovery");
    },
    onError: (e) => setError(e instanceof ApiError ? e.detail : t("Senha ou código inválido")),
  });

  const confirmDisable = useMutation({
    mutationFn: () => api.post("/auth/mfa/disable", { password, code }),
    onSuccess: async () => {
      toast("ok", t("2FA desativado"));
      await refresh();
      close();
    },
    onError: (e) => setError(e instanceof ApiError ? e.detail : t("Senha ou código inválido")),
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
    <Modal open={open} onClose={close} title={t("Autenticação em duas etapas (2FA)")}>
      {step === "status" && (
        <div className="space-y-4">
          {user?.mfa_enabled ? (
            <>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                {t("O 2FA está ativo na sua conta.")}
              </p>
              <div className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-slate-600 dark:text-slate-300">
                    {t("Códigos de recuperação restantes:")}{" "}
                    <strong className={remaining <= 2 ? "text-red-600 dark:text-red-400" : ""}>
                      {remaining}
                    </strong>
                  </span>
                  <Button variant="ghost" onClick={() => setStep("regenerate")}>
                    {t("Gerar novos")}
                  </Button>
                </div>
                {remaining <= 2 && (
                  <p className="mt-2 text-xs text-red-600 dark:text-red-400">
                    {t("Você está quase sem códigos — gere um lote novo e guarde-o.")}
                  </p>
                )}
              </div>
              <TrustedDevices />
              <div className="flex justify-end gap-2">
                <Button variant="ghost" onClick={close}>
                  {t("Fechar")}
                </Button>
                <Button variant="danger" onClick={() => setStep("disable")}>
                  {t("Desativar 2FA")}
                </Button>
              </div>
            </>
          ) : (
            <>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                {t("O 2FA está desativado. Ative para exigir um código do seu aplicativo autenticador (Google Authenticator, Authy, 1Password…) a cada login.")}
              </p>
              <div className="flex justify-end gap-2">
                <Button variant="ghost" onClick={close}>
                  {t("Fechar")}
                </Button>
                <Button loading={startSetup.isPending} onClick={() => startSetup.mutate()}>
                  {t("Ativar 2FA")}
                </Button>
              </div>
            </>
          )}
        </div>
      )}

      {step === "setup" && setup && (
        <form className="space-y-4" onSubmit={submit(() => confirmEnable.mutate())}>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            {t('No seu aplicativo autenticador, escaneie o QR code abaixo — ou adicione a conta manualmente com esta chave ("chave baseada em tempo"):')}
          </p>
          <div className="flex justify-center">
            <img
              src={setup.qr_svg}
              alt={t("QR code para configurar o 2FA no aplicativo autenticador")}
              className="h-48 w-48 rounded-lg border border-slate-200 bg-white p-2 dark:border-slate-700"
            />
          </div>
          <div className="break-all rounded-lg border border-slate-200 bg-slate-50 p-3 text-center font-mono text-sm tracking-wider dark:border-slate-800 dark:bg-slate-800/50">
            {setup.secret}
          </div>
          <p className="text-xs text-slate-400 dark:text-slate-500">
            {t("Alguns apps aceitam colar o link diretamente:")}{" "}
            <span className="break-all font-mono">{setup.otpauth_uri}</span>
          </p>
          <Field label={t("Código gerado pelo app")} error={error ?? undefined}>
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
              {t("Cancelar")}
            </Button>
            <Button type="submit" loading={confirmEnable.isPending} disabled={code.length !== 6}>
              {t("Confirmar e ativar")}
            </Button>
          </div>
        </form>
      )}

      {step === "recovery" && recoveryCodes && (
        <div className="space-y-4">
          <RecoveryCodes codes={recoveryCodes} />
          <div className="flex justify-end">
            <Button onClick={close}>{t("Já guardei os códigos")}</Button>
          </div>
        </div>
      )}

      {step === "regenerate" && (
        <form className="space-y-3" onSubmit={submit(() => regenerate.mutate())}>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            {t("Confirme sua senha e um código atual (do autenticador ou um código de recuperação ainda válido). Os códigos anteriores deixam de funcionar.")}
          </p>
          <Field label={t("Senha atual")}>
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
          <Field label={t("Código do autenticador ou de recuperação")} error={error ?? undefined}>
            <input
              className="input text-center font-mono text-lg tracking-widest"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              required
            />
          </Field>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={() => setStep("status")}>
              {t("Cancelar")}
            </Button>
            <Button
              type="submit"
              loading={regenerate.isPending}
              disabled={code.trim().length < 6 || !password}
            >
              {t("Gerar novos códigos")}
            </Button>
          </div>
        </form>
      )}

      {step === "disable" && (
        <form className="space-y-3" onSubmit={submit(() => confirmDisable.mutate())}>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            {t("Confirme sua senha e um código para desativar o 2FA — pode ser o código atual do autenticador ou um dos seus códigos de recuperação.")}
          </p>
          <Field label={t("Senha atual")}>
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
          <Field label={t("Código do autenticador ou de recuperação")} error={error ?? undefined}>
            <input
              className="input text-center font-mono text-lg tracking-widest"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              required
            />
          </Field>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={close}>
              {t("Cancelar")}
            </Button>
            <Button
              type="submit"
              variant="danger"
              loading={confirmDisable.isPending}
              disabled={code.trim().length < 6 || !password}
            >
              {t("Desativar 2FA")}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}
