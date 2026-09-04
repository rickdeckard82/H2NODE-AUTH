import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { AppFooter } from "../../components/AppFooter";
import { Logo } from "../../components/Logo";
import { Button, Field } from "../../components/ui";
import { ApiError } from "../../lib/api";
import { useAuth } from "../../lib/auth";

export default function LoginPage() {
  const { user, loading, login, verifyMfa } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [code, setCode] = useState("");
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
      setError(err instanceof ApiError ? err.detail : "Falha ao entrar");
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
      await verifyMfa(mfaToken, code);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Código inválido");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-100 dark:bg-slate-950">
      <div className="flex flex-1 items-center justify-center p-4">
        {mfaToken ? (
          <form onSubmit={onSubmitCode} className="card w-full max-w-sm p-6">
            <div className="mb-6 flex flex-col items-center gap-3">
              <Logo className="h-24 w-24" />
              <div className="text-xl font-bold">Pulse RADIUS</div>
            </div>
            <p className="mb-3 text-sm text-slate-500 dark:text-slate-400">
              Digite o código de 6 dígitos do seu aplicativo autenticador.
            </p>
            <Field label="Código de verificação" error={error ?? undefined}>
              <input
                className="input text-center font-mono text-lg tracking-widest"
                inputMode="numeric"
                pattern="\d{6}"
                maxLength={6}
                autoComplete="one-time-code"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                required
                autoFocus
              />
            </Field>
            <Button type="submit" className="mt-5 w-full" loading={busy} disabled={code.length !== 6}>
              Verificar
            </Button>
            <button
              type="button"
              className="mt-3 w-full text-center text-sm text-slate-500 hover:underline dark:text-slate-400"
              onClick={() => {
                setMfaToken(null);
                setCode("");
                setError(null);
              }}
            >
              Voltar
            </button>
          </form>
        ) : (
          <form onSubmit={onSubmitPassword} className="card w-full max-w-sm p-6">
            <div className="mb-6 flex flex-col items-center gap-3">
              <Logo className="h-24 w-24" />
              <div className="text-xl font-bold">Pulse RADIUS</div>
            </div>

            <div className="space-y-3">
              <Field label="Utilizador">
                <input
                  className="input"
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  autoFocus
                />
              </Field>
              <Field label="Senha" error={error ?? undefined}>
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
              Entrar
            </Button>
          </form>
        )}
      </div>

      <AppFooter className="px-4 py-4 text-center" />
    </div>
  );
}
