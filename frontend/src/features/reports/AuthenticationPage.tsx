import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { RefreshButton } from "../../components/RefreshButton";
import { Badge, Button, Card, PageHeader, Pagination, Spinner } from "../../components/ui";
import { api, type Page } from "../../lib/api";
import { useFmtDate } from "../../lib/datetime";
import type { AuthEvent } from "../../lib/types";
import { emptyFilters, ReportFilters, toIso, type ReportFilterState } from "./ReportFilters";
import { useT } from "../../lib/i18n";

export default function AuthenticationPage() {
  const t = useT();
  const fmt = useFmtDate();
  const [filters, setFilters] = useState<ReportFilterState>(emptyFilters);
  const [accepted, setAccepted] = useState<"" | "true" | "false">("");
  const [protocol, setProtocol] = useState<"" | "radius" | "tacacs">("");
  const [source, setSource] = useState("");
  const [dest, setDest] = useState("");
  const [page, setPage] = useState(1);

  const query = {
    username: filters.username,
    accepted: accepted || undefined,
    protocol: protocol || undefined,
    since: toIso(filters.since),
    until: toIso(filters.until),
    source: source.trim() || undefined,
    dest: dest.trim() || undefined,
  };

  const list = useQuery({
    queryKey: ["authn", query, page],
    queryFn: () =>
      api.get<Page<AuthEvent>>("/accounting/authentication", { ...query, page, page_size: 25 }),
  });

  function onFilters(next: ReportFilterState) {
    setFilters(next);
    setPage(1);
  }

  async function downloadCsv() {
    const blob = await api.blob("/accounting/authentication.csv", query);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "authentication.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <PageHeader
        title={t("Autenticação")}
        subtitle={t("Tentativas de login nos equipamentos (RADIUS e TACACS+), com IP de origem e destino")}
        actions={<RefreshButton keys={["authn"]} />}
      />

      <ReportFilters
        value={filters}
        onChange={onFilters}
        extra={
          <>
            <label className="block">
              <span className="label">{t("Origem")}</span>
              <input
                className="input max-w-[160px]"
                placeholder="186.233.16.9"
                value={source}
                onChange={(e) => {
                  setSource(e.target.value);
                  setPage(1);
                }}
              />
            </label>
            <label className="block">
              <span className="label">{t("Destino")}</span>
              <input
                className="input max-w-[180px]"
                placeholder={t("IP ou nome")}
                value={dest}
                onChange={(e) => {
                  setDest(e.target.value);
                  setPage(1);
                }}
              />
            </label>
          </>
        }
        right={
          <>
            <label className="block">
              <span className="label">{t("Protocolo")}</span>
              <select
                className="input max-w-[130px]"
                value={protocol}
                onChange={(e) => {
                  setProtocol(e.target.value as "" | "radius" | "tacacs");
                  setPage(1);
                }}
              >
                <option value="">{t("Todos")}</option>
                <option value="radius">{t("RADIUS")}</option>
                <option value="tacacs">{t("TACACS+")}</option>
              </select>
            </label>
            <label className="block">
              <span className="label">{t("Resultado")}</span>
              <select
                className="input max-w-[150px]"
                value={accepted}
                onChange={(e) => {
                  setAccepted(e.target.value as "" | "true" | "false");
                  setPage(1);
                }}
              >
                <option value="">{t("Todos")}</option>
                <option value="true">{t("Aceitos")}</option>
                <option value="false">{t("Negados")}</option>
              </select>
            </label>
            <Button variant="ghost" onClick={downloadCsv}>
              {t("Exportar CSV")}
            </Button>
          </>
        }
      />

      <Card className="overflow-x-auto p-0">
        <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
          <thead className="bg-slate-50 dark:bg-slate-800/50">
            <tr>
              <th className="th">{t("Data")}</th>
              <th className="th">{t("Protocolo")}</th>
              <th className="th">{t("Usuário")}</th>
              <th className="th">{t("Origem")}</th>
              <th className="th">{t("Destino")}</th>
              <th className="th">{t("Resultado")}</th>
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
            {list.data?.items.map((e) => (
              <tr key={e.id}>
                <td className="td whitespace-nowrap">{fmt(e.authdate)}</td>
                <td className="td">
                  <Badge tone={e.protocol === "tacacs" ? "amber" : "blue"}>
                    {e.protocol === "tacacs" ? "TACACS+" : "RADIUS"}
                  </Badge>
                </td>
                <td className="td font-medium">{e.username || "—"}</td>
                <td className="td font-mono text-xs">{e.source_ip || "—"}</td>
                <td className="td">
                  <span className="font-mono text-xs">{e.dest_ip || "—"}</span>
                  {e.nas_name && (
                    <div className="text-xs text-slate-400 dark:text-slate-500">{e.nas_name}</div>
                  )}
                </td>
                <td className="td">
                  {e.accepted ? (
                    <Badge tone="green">{e.reply || "Access-Accept"}</Badge>
                  ) : (
                    <Badge tone="red">{e.reply || "Access-Reject"}</Badge>
                  )}
                </td>
              </tr>
            ))}
            {list.data?.items.length === 0 && (
              <tr>
                <td className="td text-slate-400 dark:text-slate-500" colSpan={6}>
                  Nenhum evento para o filtro.
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
