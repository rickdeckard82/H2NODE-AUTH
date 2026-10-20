import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Button, Card, Field, PageHeader, useToast } from "../../components/ui";
import { api, ApiError } from "../../lib/api";
import { useT } from "../../lib/i18n";
import BackupSchedulePanel from "./BackupSchedulePanel";

interface RestoreResult {
  statements: number;
  dump_schema_version: string | null;
  warning?: string;
}

export default function BackupPage() {
  const t = useT();
  const CONFIRM_WORD = t("RESTAURAR");
  const toast = useToast();
  const [includeAccounting, setIncludeAccounting] = useState(true);
  const [encryptExport, setEncryptExport] = useState(true);
  const [file, setFile] = useState<File | null>(null);
  const [confirm, setConfirm] = useState("");
  const [result, setResult] = useState<RestoreResult | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const download = useMutation({
    mutationFn: async () => {
      const blob = await api.blob("/backup/export", {
        include_accounting: includeAccounting,
        encrypted: encryptExport,
      });
      const d = new Date();
      const p = (n: number) => String(n).padStart(2, "0");
      const stamp = `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `pulse-radius-backup-${stamp}.sql${encryptExport ? ".enc" : ""}`;
      a.click();
      URL.revokeObjectURL(url);
    },
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : t("Falha ao gerar o backup")),
  });

  const restore = useMutation({
    mutationFn: async () => {
      const fd = new FormData();
      fd.append("file", file as File);
      fd.append("confirm", confirm);
      return api.upload<RestoreResult>("/backup/import", fd);
    },
    onSuccess: (r) => {
      setResult(r);
      setConfirm("");
      setFile(null);
      if (fileRef.current) fileRef.current.value = "";
      toast(r.warning ? "err" : "ok", r.warning ?? t("Backup restaurado. Faça login novamente."));
    },
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : t("Falha ao restaurar")),
  });

  const canRestore = !!file && confirm === CONFIRM_WORD && !restore.isPending;

  return (
    <div>
      <PageHeader
        title={t("Backup e restauração")}
        subtitle={t("Cópia completa do banco (RADIUS + painel) para recuperação em caso de falha")}
      />

      <BackupSchedulePanel />

      <Card className="mb-4">
        <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{t("Baixar backup")}</h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          {t(
            "Gera um arquivo .sql com o esquema e os dados de todas as tabelas (usuários de autenticação, equipamentos, fabricantes, perfis, grupos, usuários do painel e auditoria).",
          )}{" "}
          <strong>{t("Não inclui")}</strong>{" "}
          {t(
            "os segredos do .env (JWT_SECRET, FERNET_KEY, senhas do MySQL) — guarde-os à parte.",
          )}
        </p>
        <label className="mt-3 flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={includeAccounting}
            onChange={(e) => setIncludeAccounting(e.target.checked)}
          />
          {t("Incluir histórico de accounting (radacct / radpostauth) — pode ser grande")}
        </label>
        <label className="mt-2 flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={encryptExport}
            onChange={(e) => setEncryptExport(e.target.checked)}
          />
          {t(
            "Cifrar o arquivo com o FERNET_KEY do servidor (recomendado — o dump contém senhas e segredos RADIUS em claro)",
          )}
        </label>
        <div className="mt-4">
          <Button onClick={() => download.mutate()} loading={download.isPending}>
            {t("Baixar backup")} {encryptExport ? "(.sql.enc)" : "(.sql)"}
          </Button>
        </div>
      </Card>

      <Card>
        <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{t("Restaurar backup")}</h2>

        <div className="mt-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300">
          <p className="font-semibold">{t("Operação destrutiva e irreversível.")}</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-5">
            <li>{t("Todas as tabelas são apagadas e recriadas a partir do arquivo.")}</li>
            <li>{t("Baixe um backup atual antes de continuar.")}</li>
            <li>
              {t(
                "Restaure apenas em um stack com o mesmo FERNET_KEY; caso contrário os segredos RADIUS dos equipamentos ficam ilegíveis.",
              )}
            </li>
            <li>{t("Ao terminar, a sua sessão pode ser invalidada — faça login novamente.")}</li>
          </ul>
        </div>

        <div className="mt-3 space-y-3">
          <Field label={t("Arquivo de backup (.sql, .sql.gz ou .sql.enc)")}>
            <div className="flex items-center gap-3">
              <input
                ref={fileRef}
                type="file"
                accept=".sql,.gz,.enc,application/sql,application/gzip,application/octet-stream,text/plain"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <Button type="button" variant="ghost" onClick={() => fileRef.current?.click()}>
                {t("Escolher arquivo")}
              </Button>
              <span className="truncate text-sm text-slate-500 dark:text-slate-400">
                {file?.name ?? t("Nenhum arquivo escolhido")}
              </span>
            </div>
          </Field>
          <Field label={t("Digite {palavra} para confirmar", { palavra: CONFIRM_WORD })}>
            <input
              className="input max-w-xs"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder={CONFIRM_WORD}
              autoComplete="off"
            />
          </Field>
          <Button
            variant="danger"
            disabled={!canRestore}
            loading={restore.isPending}
            onClick={() => {
              if (window.confirm(t("Confirma a restauração? O banco atual será substituído."))) {
                restore.mutate();
              }
            }}
          >
            {t("Restaurar backup")}
          </Button>
        </div>

        {result && (
          <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm dark:border-slate-800 dark:bg-slate-800/50">
            <p>
              {t("Restauração concluída: {n} instruções aplicadas", { n: result.statements })}
              {result.dump_schema_version && ` (schema ${result.dump_schema_version})`}.
            </p>
            {result.warning && (
              <p className="mt-1 text-amber-700 dark:text-amber-400">{result.warning}</p>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
