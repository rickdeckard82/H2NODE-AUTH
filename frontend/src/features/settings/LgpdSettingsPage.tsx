import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Button, Card, Field, PageHeader, Spinner, useToast } from "../../components/ui";
import { api, ApiError } from "../../lib/api";
import { useFmtDate } from "../../lib/datetime";
import { useT } from "../../lib/i18n";

interface LgpdSettings {
  org_name: string;
  dpo_email: string;
  accounting_retention_days: number;
  audit_retention_days: number;
  auth_user_retention_days: number;
  last_purge_at: string | null;
  updated_at: string | null;
}

interface FormState {
  org_name: string;
  dpo_email: string;
  accounting_retention_days: number;
  audit_retention_days: number;
  auth_user_retention_days: number;
}

const empty: FormState = {
  org_name: "",
  dpo_email: "",
  accounting_retention_days: 0,
  audit_retention_days: 0,
  auth_user_retention_days: 0,
};

function RetentionField({
  label,
  hint,
  value,
  onChange,
}: {
  label: string;
  hint: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <Field label={label} hint={hint}>
      <div className="flex items-center gap-2">
        <input
          className="input max-w-[120px]"
          type="number"
          min={0}
          max={36500}
          value={value}
          onChange={(e) => onChange(Math.max(0, Math.floor(Number(e.target.value) || 0)))}
        />
        <span className="text-sm text-slate-500 dark:text-slate-400">
          dias{value > 0 ? ` (~${Math.round((value / 30) * 10) / 10} meses)` : ""}
        </span>
      </div>
    </Field>
  );
}

export default function LgpdSettingsPage() {
  const t = useT();
  const qc = useQueryClient();
  const toast = useToast();
  const fmtDate = useFmtDate();
  const [form, setForm] = useState<FormState>(empty);

  const query = useQuery({
    queryKey: ["lgpd-settings"],
    queryFn: () => api.get<LgpdSettings>("/settings/lgpd"),
  });

  useEffect(() => {
    const cfg = query.data;
    if (cfg) {
      setForm({
        org_name: cfg.org_name,
        dpo_email: cfg.dpo_email,
        accounting_retention_days: cfg.accounting_retention_days,
        audit_retention_days: cfg.audit_retention_days,
        auth_user_retention_days: cfg.auth_user_retention_days,
      });
    }
  }, [query.data]);

  const save = useMutation({
    mutationFn: (f: FormState) => api.put<LgpdSettings>("/settings/lgpd", f),
    onSuccess: () => {
      toast("ok", "Configuração LGPD salva");
      qc.invalidateQueries({ queryKey: ["lgpd-settings"] });
    },
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : t("Erro ao salvar")),
  });

  if (query.isLoading) return <Spinner className="h-6 w-6 text-brand-600" />;

  return (
    <div>
      <PageHeader
        title={t("LGPD")}
        subtitle={t("Identificação do controlador exibida no Aviso de Privacidade e prazos de retenção de dados")}
      />

      <Card className="mb-4">
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate(form);
          }}
        >
          <div>
            <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Controlador dos dados
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Aparece no{" "}
              <a
                className="text-brand-600 hover:underline dark:text-brand-400"
                href="/privacidade"
                target="_blank"
                rel="noreferrer"
              >
                Aviso de Privacidade
              </a>{" "}
              (link no rodapé, acessível sem login).
            </p>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <Field label="Nome / razão social da empresa">
                <input
                  className="input"
                  value={form.org_name}
                  maxLength={190}
                  onChange={(e) => setForm({ ...form, org_name: e.target.value })}
                  required
                />
              </Field>
              <Field
                label="E-mail do Encarregado (DPO)"
                hint="Para onde os titulares enviam pedidos sobre seus dados."
              >
                <input
                  className="input"
                  type="email"
                  value={form.dpo_email}
                  maxLength={190}
                  onChange={(e) => setForm({ ...form, dpo_email: e.target.value })}
                  required
                />
              </Field>
            </div>
          </div>

          <div className="border-t border-slate-100 pt-4 dark:border-slate-800">
            <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Retenção e exclusão automática
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Dados mais antigos que o prazo são apagados automaticamente, uma vez por dia.
              <strong> 0 = sem exclusão automática</strong> (mantidos enquanto necessários).
            </p>
            <div className="mt-3 space-y-3">
              <RetentionField
                label="Logins / accounting"
                hint="Eventos de autenticação (radpostauth), comandos e sessões encerradas (radacct)."
                value={form.accounting_retention_days}
                onChange={(v) => setForm({ ...form, accounting_retention_days: v })}
              />
              <RetentionField
                label="Auditoria do painel"
                hint="Log de ações administrativas (app_audit_log)."
                value={form.audit_retention_days}
                onChange={(v) => setForm({ ...form, audit_retention_days: v })}
              />
              <RetentionField
                label="Usuários de autenticação"
                hint="Apaga contas RADIUS/TACACS+ desativadas e sem autenticar há mais que o prazo. Contas ativas nunca são removidas."
                value={form.auth_user_retention_days}
                onChange={(v) => setForm({ ...form, auth_user_retention_days: v })}
              />
            </div>
            {query.data?.last_purge_at && (
              <p className="mt-3 text-xs text-slate-400 dark:text-slate-500">
                Último expurgo automático: {fmtDate(query.data.last_purge_at)}
              </p>
            )}
          </div>

          <div className="flex justify-end">
            <Button type="submit" loading={save.isPending}>
              {t("Salvar")}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
