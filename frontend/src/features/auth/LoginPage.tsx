import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { AppFooter } from "../../components/AppFooter";
import { Logo } from "../../components/Logo";
import { Button, Field } from "../../components/ui";
import { ApiError } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { useT } from "../../lib/i18n";

export default function LoginPage() {
  const { user, loading, login, verifyMfa } = useAuth();
  const t = useT();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [rememberDevice, setRememberDevice] = useState(false);
  const [useRecovery, setUseRecovery] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!loading && user) return <Navigate to="/" replace />;

  async function onSubmitPassword(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await login(username.trim(), password);
      if (res.mfaRequired && res.mfaToken) {
        setMfaToken(res.mfaToken);
      } else {
        navigate("/", { replace: true });
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("Falha ao entrar"));
    } finally {
      setBusy(false);
    }
  }

  async function onSubmitCode(e: FormEvent) {
    e.preventDefault();
    if (!mfaToken) return;
    setBusy(true);
    setError(null);
    try {
      await verifyMfa(mfaToken, code, rememberDevice);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("Código inválido"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden bg-slate-100 dark:bg-slate-950">
      <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
        <svg
          className="animate-wave-drift absolute bottom-0 left-0 h-56 w-[200%] text-brand-600/[0.10] dark:text-brand-400/[0.12]"
          style={{ animationDuration: "26s" }}
          viewBox="0 0 2880 320"
          preserveAspectRatio="none"
          fill="currentColor"
        >
          <path d="M0,160 C240,220 480,100 720,160 C960,220 1200,100 1440,160 C1680,220 1920,100 2160,160 C2400,220 2640,100 2880,160 L2880,320 L0,320 Z" />
        </svg>
        <svg
          className="animate-wave-drift absolute bottom-0 left-0 h-40 w-[200%] text-brand-500/[0.08] dark:text-brand-300/[0.08]"
          style={{ animationDuration: "38s", animationDirection: "reverse" }}
          viewBox="0 0 2880 320"
          preserveAspectRatio="none"
          fill="currentColor"
        >
          <path d="M0,180 C240,120 480,240 720,180 C960,120 1200,240 1440,180 C1680,120 1920,240 2160,180 C2400,120 2640,240 2880,180 L2880,320 L0,320 Z" />
        </svg>
        <svg
          className="animate-wave-drift absolute bottom-0 left-0 h-72 w-[200%] text-brand-700/[0.06] dark:text-brand-200/[0.06]"
          style={{ animationDuration: "32s" }}
          viewBox="0 0 2880 320"
          preserveAspectRatio="none"
          fill="currentColor"
        >
          <path d="M0,140 C240,200 480,80 720,140 C960,200 1200,80 1440,140 C1680,200 1920,80 2160,140 C2400,200 2640,80 2880,140 L2880,320 L0,320 Z" />
        </svg>
      </div>

      <div className="relative z-10 flex flex-1 items-center justify-center p-4">
        {mfaToken ? (
          <form onSubmit={onSubmitCode} className="card w-full max-w-sm p-6">
            <div className="mb-6 flex flex-col items-center gap-3">
              <Logo className="h-24 w-24" />
              <div className="text-xl font-bold">Pulse RADIUS</div>
            </div>
            <p className="mb-3 text-sm text-slate-500 dark:text-slate-400">
              {useRecovery
                ? t("Digite um dos seus códigos de recuperação (uso único).")
                : t("Digite o código de 6 dígitos do seu aplicativo autenticador.")}
            </p>
            <Field
              label={useRecovery ? t("Código de recuperação") : t("Código de verificação")}
              error={error ?? undefined}
            >
              <input
                className="input text-center font-mono text-lg tracking-widest"
                inputMode={useRecovery ? "text" : "numeric"}
                autoComplete="one-time-code"
                maxLength={useRecovery ? 13 : 6}
                value={code}
                onChange={(e) =>
                  setCode(useRecovery ? e.target.value.toUpperCase() : e.target.value.replace(/\D/g, ""))
                }
                required
                autoFocus
              />
            </Field>
            <label className="mt-3 flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
              <input
                type="checkbox"
                checked={rememberDevice}
                onChange={(e) => setRememberDevice(e.target.checked)}
              />
              {t("Confiar neste dispositivo (não pedir o código por 30 dias)")}
            </label>
            <Button
              type="submit"
              className="mt-4 w-full"
              loading={busy}
              disabled={useRecovery ? code.trim().length < 6 : code.length !== 6}
            >
              {t("Verificar")}
            </Button>
            <button
              type="button"
              className="mt-3 w-full text-center text-sm text-slate-500 hover:underline dark:text-slate-400"
              onClick={() => {
                setUseRecovery((v) => !v);
                setCode("");
                setError(null);
              }}
            >
              {useRecovery ? t("Usar o código do autenticador") : t("Usar um código de recuperação")}
            </button>
            <button
              type="button"
              className="mt-2 w-full text-center text-sm text-slate-500 hover:underline dark:text-slate-400"
              onClick={() => {
                setMfaToken(null);
                setCode("");
                setError(null);
                setUseRecovery(false);
                setRememberDevice(false);
              }}
            >
              {t("Voltar")}
            </button>
          </form>
        ) : (
          <form onSubmit={onSubmitPassword} className="card w-full max-w-sm p-6">
            <div className="mb-6 flex flex-col items-center gap-3">
              <Logo className="h-24 w-24" />
              <div className="text-xl font-bold">Pulse RADIUS</div>
            </div>

            <div className="space-y-3">
              <Field label={t("Usuário")}>
                <input
                  className="input"
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  autoFocus
                />
              </Field>
              <Field label={t("Senha")} error={error ?? undefined}>
                <input
                  className="input"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </Field>
            </div>

            <Button type="submit" className="mt-5 w-full" loading={busy}>
              {t("Entrar")}
            </Button>
          </form>
        )}
      </div>

      <AppFooter className="relative z-10 px-4 py-4 text-center" />
    </div>
  );
}
