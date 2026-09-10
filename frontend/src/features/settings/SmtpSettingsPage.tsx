import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Button, Card, Field, PageHeader, Spinner, useToast } from "../../components/ui";
import { api, ApiError } from "../../lib/api";
import type { SmtpSettings } from "../../lib/types";
import { useT } from "../../lib/i18n";

interface FormState {
  host: string;
  port: number;
  username: string;
  password: string;
  clear_password: boolean;
  use_tls: boolean;
  use_ssl: boolean;
  from_email: string;
  from_name: string;
}

const empty: FormState = {
  host: "",
  port: 587,
  username: "",
  password: "",
  clear_password: false,
  use_tls: true,
  use_ssl: false,
  from_email: "",
  from_name: "",
};

export default function SmtpSettingsPage() {
  const t = useT();
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState<FormState>(empty);
  const [testTo, setTestTo] = useState("");

  const query = useQuery({
    queryKey: ["smtp-settings"],
    queryFn: () => api.get<SmtpSettings | null>("/settings/smtp"),
  });

  useEffect(() => {
    const cfg = query.data;
    if (cfg) {
      setForm({
        host: cfg.host,
        port: cfg.port,
        username: cfg.username ?? "",
        password: "",
        clear_password: false,
        use_tls: cfg.use_tls,
        use_ssl: cfg.use_ssl,
        from_email: cfg.from_email,
        from_name: cfg.from_name ?? "",
      });
    }
  }, [query.data]);

  const save = useMutation({
    mutationFn: (f: FormState) =>
      api.put<SmtpSettings>("/settings/smtp", {
        host: f.host,
        port: f.port,
        username: f.username || null,
        password: f.password || null,
        clear_password: f.clear_password,
        use_tls: f.use_tls,
        use_ssl: f.use_ssl,
        from_email: f.from_email,
        from_name: f.from_name || null,
      }),
    onSuccess: () => {
      toast("ok", "Configuração SMTP salva");
      qc.invalidateQueries({ queryKey: ["smtp-settings"] });
    },
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : t("Erro ao salvar")),
  });

  const test = useMutation({
    mutationFn: () => api.post<{ detail: string }>("/settings/smtp/test", { to: testTo }),
    onSuccess: (r) => toast("ok", r.detail),
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : "Falha ao enviar"),
  });

  if (query.isLoading) return <Spinner className="h-6 w-6 text-brand-600" />;

  return (
    <div>
      <PageHeader
        title={t("Servidor SMTP")}
        subtitle={t("Usado para enviar o convite de registro (criação de senha) aos usuários do painel")}
      />

      <Card className="mb-4">
        <form
          className="grid grid-cols-2 gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate(form);
          }}
        >
          <Field label="Servidor (host)">
            <input
              className="input"
              value={form.host}
              onChange={(e) => setForm({ ...form, host: e.target.value })}
              required
            />
          </Field>
          <Field label="Porta">
            <input
              className="input"
              type="number"
              value={form.port}
              onChange={(e) => setForm({ ...form, port: Number(e.target.value) })}
              required
            />
          </Field>
          <Field label="Usuário (opcional)" hint="em branco = servidor sem autenticação">
            <input
              className="input"
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
            />
          </Field>
          <Field
            label={query.data?.has_password ? "Senha (em branco = manter)" : "Senha"}
            hint="Guardada cifrada (Fernet)."
          >
            <input
              className="input"
              type="password"
              value={form.password}
              disabled={form.clear_password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
          </Field>
          {query.data?.has_password && (
            <label className="col-span-2 -mt-2 flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
              <input
                type="checkbox"
                checked={form.clear_password}
                onChange={(e) =>
                  setForm({ ...form, clear_password: e.target.checked, password: "" })
                }
              />
              Remover a senha (autenticar sem senha)
            </label>
          )}
          <Field label="E-mail do remetente">
            <input
              className="input"
              type="email"
              value={form.from_email}
              onChange={(e) => setForm({ ...form, from_email: e.target.value })}
              required
            />
          </Field>
          <Field label="Nome do remetente (opcional)">
            <input
              className="input"
              value={form.from_name}
              onChange={(e) => setForm({ ...form, from_name: e.target.value })}
              placeholder="Pulse RADIUS"
            />
          </Field>
          <div className="col-span-2 flex flex-wrap gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.use_tls}
                onChange={(e) =>
                  setForm({ ...form, use_tls: e.target.checked, use_ssl: e.target.checked ? false : form.use_ssl })
                }
              />
              STARTTLS (porta 587 tipicamente)
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.use_ssl}
                onChange={(e) =>
                  setForm({ ...form, use_ssl: e.target.checked, use_tls: e.target.checked ? false : form.use_tls })
                }
              />
              SSL/TLS implícito (porta 465 tipicamente)
            </label>
          </div>
          <div className="col-span-2 flex justify-end">
            <Button type="submit" loading={save.isPending}>
              {t("Salvar")}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Enviar e-mail de teste</h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Salve a configuração acima antes de testar.
        </p>
        <div className="mt-3 flex flex-wrap items-end gap-2">
          <Field label="Enviar para">
            <input
              className="input"
              type="email"
              value={testTo}
              onChange={(e) => setTestTo(e.target.value)}
              placeholder="voce@exemplo.com"
            />
          </Field>
          <Button
            variant="ghost"
            disabled={!testTo}
            loading={test.isPending}
            onClick={() => test.mutate()}
          >
            Enviar teste
          </Button>
        </div>
      </Card>
    </div>
  );
}
