import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { RefreshButton } from "../../components/RefreshButton";
import { Badge, Button, Card, PageHeader, Pagination, Spinner } from "../../components/ui";
import { api, type Page } from "../../lib/api";
import { useFmtDate } from "../../lib/datetime";
import { fmtBytes, fmtDuration } from "../../lib/format";
import type { CommandEvent, Session } from "../../lib/types";
import { emptyFilters, ReportFilters, toIso, type ReportFilterState } from "../reports/ReportFilters";
import { useT } from "../../lib/i18n";

type View = "commands" | "sessions";

export default function AccountingPage() {
  const t = useT();
  const fmt = useFmtDate();
  const [view, setView] = useState<View>("commands");
  const [filters, setFilters] = useState<ReportFilterState>(emptyFilters);
  const [active, setActive] = useState<"" | "true" | "false">("");
  const [page, setPage] = useState(1);

  const range = { since: toIso(filters.since), until: toIso(filters.until) };
  const cmdQuery = { username: filters.username, nas_ip: filters.nasIp, ...range };
  const sessQuery = { username: filters.username, nas_ip: filters.nasIp, active: active || undefined, ...range };

  const commands = useQuery({
    queryKey: ["acct-commands", cmdQuery, page],
    queryFn: () =>
      api.get<Page<CommandEvent>>("/accounting/commands", { ...cmdQuery, page, page_size: 25 }),
    enabled: view === "commands",
  });

  const sessions = useQuery({
    queryKey: ["acct-sessions", sessQuery, page],
    queryFn: () =>
      api.get<Page<Session>>("/accounting/sessions", { ...sessQuery, page, page_size: 25 }),
    enabled: view === "sessions",
  });

  function onFilters(next: ReportFilterState) {
    setFilters(next);
    setPage(1);
  }

  async function downloadCsv() {
    const path = view === "commands" ? "/accounting/commands.csv" : "/accounting/sessions.csv";
    const q = view === "commands" ? cmdQuery : sessQuery;
    const blob = await api.blob(path, q);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = view === "commands" ? "commands.csv" : "sessions.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <PageHeader
        title={t("Accounting")}
        subtitle={t("Comandos executados nos equipamentos e sessões de login (radacct)")}
        actions={<RefreshButton keys={["acct-commands", "acct-sessions"]} />}
      />

      <div className="mb-4 flex gap-1 border-b border-slate-200 dark:border-slate-800">
        {(
          [
            ["commands", "Comandos"],
            ["sessions", "Sessões"],
          ] as const
        ).map(([v, label]) => (
          <button
            key={v}
            onClick={() => {
              setView(v);
              setPage(1);
            }}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
              view === v
                ? "border-brand-600 text-brand-700 dark:text-brand-300"
                : "border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <ReportFilters
        value={filters}
        onChange={onFilters}
        showNas
        right={
          <>
            {view === "sessions" && (
              <label className="block">
                <span className="label">Estado</span>
                <select
                  className="input max-w-[150px]"
                  value={active}
                  onChange={(e) => {
                    setActive(e.target.value as "" | "true" | "false");
                    setPage(1);
                  }}
                >
                  <option value="">Todas</option>
                  <option value="true">Ativas</option>
                  <option value="false">Encerradas</option>
                </select>
              </label>
            )}
            <Button variant="ghost" onClick={downloadCsv}>
              {t("Exportar CSV")}
            </Button>
          </>
        }
      />

      {view === "commands" ? (
        <Card className="overflow-x-auto p-0">
          <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
            <thead className="bg-slate-50 dark:bg-slate-800/50">
              <tr>
                <th className="th">{t("Data")}</th>
                <th className="th">{t("NAS")}</th>
                <th className="th">{t("Usuário")}</th>
                <th className="th">{t("Ação")}</th>
                <th className="th">{t("Comando")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {commands.isLoading && (
                <tr>
                  <td className="td" colSpan={5}>
                    <Spinner className="h-5 w-5 text-brand-600" />
                  </td>
                </tr>
              )}
              {commands.data?.items.map((c) => (
                <tr key={c.id}>
                  <td className="td whitespace-nowrap">{fmt(c.event_time)}</td>
                  <td className="td">
                    <span className="font-mono text-xs">{c.nasipaddress}</span>
                    {c.nas_name && (
                      <div className="text-xs text-slate-400 dark:text-slate-500">{c.nas_name}</div>
                    )}
                  </td>
                  <td className="td font-medium">{c.username || "—"}</td>
                  <td className="td text-xs">{c.action || "—"}</td>
                  <td className="td">
                    <code className="text-xs">{c.command || "—"}</code>
                  </td>
                </tr>
              ))}
              {commands.data?.items.length === 0 && (
                <tr>
                  <td className="td text-slate-400 dark:text-slate-500" colSpan={5}>
                    Nenhum comando registrado. Os equipamentos precisam enviar o comando via
                    Accounting (ver docs/device-config).
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          {commands.data && (
            <Pagination
              page={page}
              pageSize={commands.data.page_size}
              total={commands.data.total}
              onPage={setPage}
            />
          )}
        </Card>
      ) : (
        <Card className="overflow-x-auto p-0">
          <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
            <thead className="bg-slate-50 dark:bg-slate-800/50">
              <tr>
                <th className="th">{t("Usuário")}</th>
                <th className="th">{t("NAS")}</th>
                <th className="th">{t("Início")}</th>
                <th className="th">{t("Fim")}</th>
                <th className="th">{t("Duração")}</th>
                <th className="th">{t("In / Out")}</th>
                <th className="th">{t("Origem")}</th>
                <th className="th">{t("Causa")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {sessions.isLoading && (
                <tr>
                  <td className="td" colSpan={8}>
                    <Spinner className="h-5 w-5 text-brand-600" />
                  </td>
                </tr>
              )}
              {sessions.data?.items.map((s) => (
                <tr key={s.id}>
                  <td className="td font-medium">{s.username}</td>
                  <td className="td">
                    <span className="font-mono text-xs">{s.nasipaddress}</span>
                    {s.nas_name && (
                      <div className="text-xs text-slate-400 dark:text-slate-500">{s.nas_name}</div>
                    )}
                  </td>
                  <td className="td whitespace-nowrap">{fmt(s.acctstarttime)}</td>
                  <td className="td whitespace-nowrap">
                    {s.active ? <Badge tone="green">ativa</Badge> : fmt(s.acctstoptime)}
                  </td>
                  <td className="td font-mono text-xs">{fmtDuration(s.acctsessiontime)}</td>
                  <td className="td text-xs">
                    {fmtBytes(s.acctinputoctets)} / {fmtBytes(s.acctoutputoctets)}
                  </td>
                  <td className="td font-mono text-xs">{s.callingstationid || "—"}</td>
                  <td className="td text-xs">{s.acctterminatecause || "—"}</td>
                </tr>
              ))}
              {sessions.data?.items.length === 0 && (
                <tr>
                  <td className="td text-slate-400 dark:text-slate-500" colSpan={8}>
                    Sem sessões para o filtro.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          {sessions.data && (
            <Pagination
              page={page}
              pageSize={sessions.data.page_size}
              total={sessions.data.total}
              onPage={setPage}
            />
          )}
        </Card>
      )}
    </div>
  );
}
