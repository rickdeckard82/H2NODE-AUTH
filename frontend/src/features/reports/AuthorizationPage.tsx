import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { RefreshButton } from "../../components/RefreshButton";
import { Button, Card, PageHeader, Pagination, Spinner } from "../../components/ui";
import { api, type Page } from "../../lib/api";
import { useFmtDate } from "../../lib/datetime";
import type { CommandEvent } from "../../lib/types";
import { emptyFilters, ReportFilters, toIso, type ReportFilterState } from "./ReportFilters";
import { useT } from "../../lib/i18n";

export default function AuthorizationPage() {
  const t = useT();
  const fmt = useFmtDate();
  const [filters, setFilters] = useState<ReportFilterState>(emptyFilters);
  const [page, setPage] = useState(1);

  const query = {
    username: filters.username,
    nas_ip: filters.nasIp,
    since: toIso(filters.since),
    until: toIso(filters.until),
  };

  const list = useQuery({
    queryKey: ["authz", query, page],
    queryFn: () =>
      api.get<Page<CommandEvent>>("/accounting/commands", { ...query, page, page_size: 25 }),
  });

  function onFilters(next: ReportFilterState) {
    setFilters(next);
    setPage(1);
  }

  async function downloadCsv() {
    const blob = await api.blob("/accounting/commands.csv", query);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "authorization.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <PageHeader
        title={t("Autorização")}
        subtitle={t("Comandos executados nos equipamentos, com o IP de origem de quem executou")}
        actions={<RefreshButton keys={["authz"]} />}
      />

      <ReportFilters
        value={filters}
        onChange={onFilters}
        showNas
        right={
          <Button variant="ghost" onClick={downloadCsv}>
            {t("Exportar CSV")}
          </Button>
        }
      />

      <Card className="overflow-x-auto p-0">
        <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
          <thead className="bg-slate-50 dark:bg-slate-800/50">
            <tr>
              <th className="th">{t("Data")}</th>
              <th className="th">{t("NAS")}</th>
              <th className="th">{t("Usuário")}</th>
              <th className="th">{t("Origem")}</th>
              <th className="th">{t("Ação")}</th>
              <th className="th">{t("Comando")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {list.isLoading && (
              <tr>
                <td className="td" colSpan={6}>
                  <Spinner className="h-5 w-5 text-brand-600" />
                </td>
              </tr>
            )}
            {list.data?.items.map((c) => (
              <tr key={c.id}>
                <td className="td whitespace-nowrap">{fmt(c.event_time)}</td>
                <td className="td">
                  <span className="font-mono text-xs">{c.nasipaddress}</span>
                  {c.nas_name && (
                    <div className="text-xs text-slate-400 dark:text-slate-500">{c.nas_name}</div>
                  )}
                </td>
                <td className="td font-medium">{c.username || "—"}</td>
                <td className="td font-mono text-xs">{c.callingstationid || "—"}</td>
                <td className="td text-xs">{c.action || "—"}</td>
                <td className="td">
                  <code className="text-xs">{c.command || "—"}</code>
                </td>
              </tr>
            ))}
            {list.data?.items.length === 0 && (
              <tr>
                <td className="td text-slate-400 dark:text-slate-500" colSpan={6}>
                  Nenhum comando registrado para o filtro. Os equipamentos precisam enviar o
                  comando via Accounting (ver docs/device-config).
                </td>
              </tr>
            )}
          </tbody>
        </table>
        {list.data && (
          <Pagination
            page={page}
            pageSize={list.data.page_size}
            total={list.data.total}
            onPage={setPage}
          />
        )}
      </Card>
    </div>
  );
}
