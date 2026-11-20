import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Badge, Button, Card, Field, Spinner, useToast } from "../../components/ui";
import { api, ApiError } from "../../lib/api";
import { TIMEZONES, useFmtDate } from "../../lib/datetime";
import { useT } from "../../lib/i18n";
import type { BackupSchedule } from "../../lib/types";

interface FormState {
  enabled: boolean;
  run_time: string;
  timezone: string;
  include_accounting: boolean;
  encrypted: boolean;
  keep_count: number;
  ftp_host: string;
  ftp_port: number;
  ftp_user: string;
  ftp_password: string;
  clear_ftp_password: boolean;
  ftp_directory: string;
  ftp_tls: boolean;
  ftp_write_only: boolean;
}

function formFrom(cfg: BackupSchedule): FormState {
  return {
    enabled: cfg.enabled,
    run_time: cfg.run_time,
    timezone: cfg.timezone,
    include_accounting: cfg.include_accounting,
    encrypted: cfg.encrypted,
    keep_count: cfg.keep_count,
    ftp_host: cfg.ftp_host ?? "",
    ftp_port: cfg.ftp_port,
    ftp_user: cfg.ftp_user ?? "",
    ftp_password: "",
    clear_ftp_password: false,
    ftp_directory: cfg.ftp_directory ?? "",
    ftp_tls: cfg.ftp_tls,
    ftp_write_only: cfg.ftp_write_only,
  };
}

function payloadFrom(f: FormState) {
  return { ...f, ftp_password: f.ftp_password || null };
}

const STATUS_TONE = { success: "green", error: "red", running: "blue" } as const;
const STATUS_LABEL = { success: "Sucesso", error: "Erro", running: "Em andamento" } as const;

export default function BackupSchedulePanel() {
  const t = useT();
  const qc = useQueryClient();
  const toast = useToast();
  const fmtDate = useFmtDate();
  const [form, setForm] = useState<FormState | null>(null);

  const query = useQuery({
    queryKey: ["backup-schedule"],
    queryFn: () => api.get<BackupSchedule>("/backup/schedule"),
    // Acompanha a execução pedida em "Executar agora" até o worker terminar.
    refetchInterval: (q) => {
      const cfg = q.state.data;
      return cfg && (cfg.run_requested_at || cfg.last_status === "running") ? 5000 : false;
    },
  });

  useEffect(() => {
    if (query.data && form === null) setForm(formFrom(query.data));
  }, [query.data, form]);

  const save = useMutation({
    mutationFn: (f: FormState) => api.put<BackupSchedule>("/backup/schedule", payloadFrom(f)),
    onSuccess: (saved) => {
      qc.setQueryData(["backup-schedule"], saved);
      setForm(formFrom(saved));
      toast("ok", t("Backup automático salvo"));
    },
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : t("Erro ao salvar")),
  });

  const test = useMutation({
    mutationFn: (f: FormState) =>
      api.post<{ detail: string }>("/backup/schedule/test", payloadFrom(f)),
    onSuccess: (r) => toast("ok", r.detail),
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : t("Falha na conexão")),
  });

  const run = useMutation({
    mutationFn: () => api.post<BackupSchedule>("/backup/schedule/run"),
    onSuccess: (saved) => {
      qc.setQueryData(["backup-schedule"], saved);
      toast("ok", t("Backup pedido; o envio começa em até 30 segundos."));
    },
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : t("Falha ao pedir o backup")),
  });

  if (query.isLoading || !form || !query.data) {
    return (
      <Card className="mb-4">
        <Spinner className="h-6 w-6 text-brand-600" />
      </Card>
    );
  }

  const cfg = query.data;
  const set = (patch: Partial<FormState>) => setForm({ ...form, ...patch });
  const busy = save.isPending || test.isPending;
  const ext = form.encrypted ? ".sql.enc" : ".sql.gz";

  return (
    <Card className="mb-4">
      <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
        {t("Backup automático por FTP")}
      </h2>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        {t(
          "Envia todo dia, no horário escolhido, o mesmo backup do banco gerado em “Baixar backup” para um servidor FTP/FTPS — inclusive o H2NODE Backup. Nenhuma cópia fica neste servidor: o arquivo é apagado assim que enviado.",
        )}
      </p>

      <dl className="mt-3 grid grid-cols-1 gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm sm:grid-cols-3 dark:border-slate-800 dark:bg-slate-800/50">
        <div>
          <dt className="text-xs text-slate-500 dark:text-slate-400">{t("Última execução")}</dt>
          <dd className="flex flex-wrap items-center gap-2">
            {cfg.last_attempt_at ? fmtDate(cfg.last_attempt_at) : "—"}
            {cfg.last_status && (
              <Badge tone={STATUS_TONE[cfg.last_status]}>{t(STATUS_LABEL[cfg.last_status])}</Badge>
            )}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500 dark:text-slate-400">{t("Próxima execução")}</dt>
          <dd>
            {cfg.run_requested_at
              ? t("Pedida agora, aguardando o worker")
              : cfg.next_run_at
                ? fmtDate(cfg.next_run_at)
                : t("Agendamento desativado")}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500 dark:text-slate-400">{t("Último sucesso")}</dt>
          <dd>{cfg.last_success_at ? fmtDate(cfg.last_success_at) : "—"}</dd>
        </div>
        {cfg.last_message && (
          <div className="sm:col-span-3">
            <dt className="text-xs text-slate-500 dark:text-slate-400">{t("Resultado")}</dt>
            <dd
              className={
                cfg.last_status === "error"
                  ? "break-words text-rose-700 dark:text-rose-400"
                  : "break-words"
              }
            >
              {cfg.last_message}
            </dd>
          </div>
        )}
      </dl>

      <form
        className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate(form);
        }}
      >
        <label className="flex items-center gap-2 text-sm font-medium sm:col-span-2">
          <input
            type="checkbox"
            checked={form.enabled}
            onChange={(e) => set({ enabled: e.target.checked })}
          />
          {t("Ativar backup diário agendado")}
        </label>

        <Field label={t("Horário diário")}>
          <input
            className="input"
            type="time"
            required
            value={form.run_time}
            onChange={(e) => set({ run_time: e.target.value })}
          />
        </Field>
        <Field label={t("Fuso horário")}>
          <select
            className="input"
            value={form.timezone}
            onChange={(e) => set({ timezone: e.target.value })}
          >
            {(TIMEZONES.includes(form.timezone) ? TIMEZONES : [form.timezone, ...TIMEZONES]).map(
              (tz) => (
                <option key={tz} value={tz}>
                  {tz}
                </option>
              ),
            )}
          </select>
        </Field>

        <Field label={t("Servidor FTP")}>
          <input
            className="input"
            value={form.ftp_host}
            placeholder="ftp.exemplo.com.br"
            onChange={(e) => set({ ftp_host: e.target.value })}
          />
        </Field>
        <Field label={t("Porta")}>
          <input
            className="input"
            type="number"
            min={1}
            max={65535}
            required
            value={form.ftp_port}
            onChange={(e) => set({ ftp_port: Number(e.target.value) })}
          />
        </Field>
        <Field label={t("Usuário")}>
          <input
            className="input"
            autoComplete="off"
            value={form.ftp_user}
            onChange={(e) => set({ ftp_user: e.target.value })}
          />
        </Field>
        <Field
          label={cfg.has_ftp_password ? t("Senha (em branco = manter)") : t("Senha")}
          hint={t("Guardada cifrada (Fernet).")}
        >
          <input
            className="input"
            type="password"
            autoComplete="new-password"
            value={form.ftp_password}
            disabled={form.clear_ftp_password}
            onChange={(e) => set({ ftp_password: e.target.value })}
          />
        </Field>
        {cfg.has_ftp_password && (
          <label className="-mt-2 flex items-center gap-2 text-sm text-slate-600 sm:col-span-2 dark:text-slate-300">
            <input
              type="checkbox"
              checked={form.clear_ftp_password}
              onChange={(e) => set({ clear_ftp_password: e.target.checked, ftp_password: "" })}
            />
            {t("Remover a senha guardada")}
          </label>
        )}
        <Field label={t("Pasta no servidor")} hint={t("Criada se não existir.")}>
          <input
            className="input"
            value={form.ftp_directory}
            placeholder="/backups/h2node-auth"
            onChange={(e) => set({ ftp_directory: e.target.value })}
          />
        </Field>
        <Field
          label={t("Cópias mantidas no FTP")}
          hint={
            form.ftp_write_only
              ? t("Destino só de gravação: a retenção fica a cargo do servidor de backup.")
              : t("As mais antigas além deste número são apagadas após cada envio.")
          }
        >
          <input
            className="input"
            type="number"
            min={1}
            max={365}
            required
            disabled={form.ftp_write_only}
            value={form.keep_count}
            onChange={(e) => set({ keep_count: Number(e.target.value) })}
          />
        </Field>

        <div className="flex flex-col gap-2 sm:col-span-2">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.ftp_tls}
              onChange={(e) => set({ ftp_tls: e.target.checked })}
            />
            {t("Usar FTPS (TLS explícito)")}
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.ftp_write_only}
              onChange={(e) => set({ ftp_write_only: e.target.checked })}
            />
            {t("Destino só de gravação (H2NODE Backup)")}
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.encrypted}
              onChange={(e) => set({ encrypted: e.target.checked })}
            />
            {t("Cifrar o arquivo com o FERNET_KEY do servidor")}
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.include_accounting}
              onChange={(e) => set({ include_accounting: e.target.checked })}
            />
            {t("Incluir histórico de accounting (radacct / radpostauth) — pode ser grande")}
          </label>
        </div>

        <div className="space-y-1 text-xs text-slate-500 sm:col-span-2 dark:text-slate-400">
          <p>
            {t("Arquivo enviado:")}{" "}
            <code>h2node-auth-backup-AAAAMMDD-HHMMSS{ext}</code>.{" "}
            {t("Restaurável direto em “Restaurar backup” abaixo.")}
          </p>
          {!form.encrypted && (
            <p className="text-amber-700 dark:text-amber-400">
              {t(
                "Sem cifra, o .sql.gz contém hashes de senha e segredos RADIUS em claro. Use só com FTPS ou com um destino que cifre ao receber (o H2NODE Backup cifra e também confere se o dump chegou completo).",
              )}
            </p>
          )}
          {form.ftp_write_only && (
            <p>
              {t(
                "Destino só de gravação: o arquivo é enviado direto com o nome final (sem .part, conferência de tamanho ou renomeação) e nada é apagado no FTP. O histórico e a retenção ficam no servidor de backup.",
              )}
            </p>
          )}
          {!form.ftp_tls && (
            <p className="text-amber-700 dark:text-amber-400">
              {t("Sem FTPS, a senha FTP e o arquivo trafegam sem criptografia na rede.")}
            </p>
          )}
        </div>

        <div className="flex flex-wrap justify-end gap-2 sm:col-span-2">
          <Button
            type="button"
            variant="ghost"
            disabled={busy || !form.ftp_host}
            loading={test.isPending}
            onClick={() => test.mutate(form)}
          >
            {t("Testar conexão")}
          </Button>
          <Button
            type="button"
            variant="ghost"
            disabled={run.isPending || !!cfg.run_requested_at || cfg.last_status === "running" || !cfg.ftp_host}
            title={cfg.ftp_host ? undefined : t("Salve a configuração antes de executar")}
            loading={run.isPending}
            onClick={() => run.mutate()}
          >
            {t("Executar agora")}
          </Button>
          <Button type="submit" loading={save.isPending} disabled={busy}>
            {t("Salvar")}
          </Button>
        </div>
      </form>
    </Card>
  );
}
