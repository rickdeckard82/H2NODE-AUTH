import { useEffect, useState, type FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { AppFooter } from "../../components/AppFooter";
import { Logo } from "../../components/Logo";
import { Button, Field, Spinner } from "../../components/ui";
import { api, ApiError } from "../../lib/api";
import { useAuth } from "../../lib/auth";

interface InviteInfo {
  username: string;
  email: string;
  full_name: string;
}

export default function SetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const navigate = useNavigate();
  const { user, refresh } = useAuth();

  const [invite, setInvite] = useState<InviteInfo | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!token) {
      setLoadError("Link inválido: token ausente.");
      return;
    }
    api
      .get<InviteInfo>(`/auth/invite/${token}`)
      .then(setInvite)
      .catch((e) =>
        setLoadError(e instanceof ApiError ? e.detail : "Convite inválido ou expirado"),
      );
  }, [token]);

  if (user) return <Navigate to="/" replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (password !== confirm) {
      setError("As senhas não coincidem");
      return;
    }
    setBusy(true);
    try {
      await api.post("/auth/invite/accept", { token, password });
      await refresh();
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Falha ao definir a senha");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-100 dark:bg-slate-950">
      <div className="flex flex-1 items-center justify-center p-4">
        <div className="card w-full max-w-sm p-6">
          <div className="mb-6 flex flex-col items-center gap-3">
            <Logo className="h-24 w-24" />
            <div className="text-xl font-bold">Pulse RADIUS</div>
          </div>

          {loadError && (
            <p className="text-center text-sm text-rose-600 dark:text-rose-400">{loadError}</p>
          )}

          {!loadError && !invite && <Spinner className="mx-auto h-6 w-6 text-brand-600" />}

          {invite && (
            <form onSubmit={onSubmit} className="space-y-3">
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Olá, <strong>{invite.full_name}</strong>. Defina a senha da sua conta (
                {invite.username}) para terminar o registo.
              </p>
              <Field label="Nova senha" hint="Mínimo 10 caracteres.">
                <input
                  className="input"
                  type="password"
                  minLength={10}
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoFocus
                />
              </Field>
              <Field label="Confirmar senha" error={error ?? undefined}>
                <input
                  className="input"
                  type="password"
                  minLength={10}
                  autoComplete="new-password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  required
                />
              </Field>
              <Button type="submit" className="w-full" loading={busy}>
                Criar senha e entrar
              </Button>
            </form>
          )}
        </div>
      </div>
      <AppFooter className="px-4 py-4 text-center" />
    </div>
  );
}
