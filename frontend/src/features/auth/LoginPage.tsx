import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { AppFooter } from "../../components/AppFooter";
import { Logo } from "../../components/Logo";
import { Button, Field } from "../../components/ui";
import { ApiError } from "../../lib/api";
import { useAuth } from "../../lib/auth";

export default function LoginPage() {
  const { user, loading, login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!loading && user) return <Navigate to="/" replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username.trim(), password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Falha ao entrar");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-100 dark:bg-slate-950">
      <div className="flex flex-1 items-center justify-center p-4">
        <form onSubmit={onSubmit} className="card w-full max-w-sm p-6">
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
      </div>

      <AppFooter className="px-4 py-4 text-center" />
    </div>
  );
}
