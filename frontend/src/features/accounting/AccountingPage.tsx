import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Badge, Button, Card, PageHeader, Pagination, Spinner } from "../../components/ui";
import { api, type Page } from "../../lib/api";
import { fmtBytes, fmtDate, fmtDuration } from "../../lib/format";
import type { Session } from "../../lib/types";

interface AuthEvent {
  id: number;
  username: string;
  reply: string;
  authdate: string;
  accepted: boolean;
}

export default function AccountingPage() {
  const [view, setView] = useState<"sessions" | "events">("sessions");
  const [username, setUsername] = useState("");
  const [nasIp, setNasIp] = useState("");
  const [active, setActive] = useState<"" | "true" | "false">("");
  const [page, setPage] = useState(1);

  const params = { username, nas_ip: nasIp, active: active || undefined, page, page_size: 25 };

  const sessions = useQuery({
    queryKey: ["sessions", params],
    queryFn: () => api.get<Page<Session>>("/accounting/sessions", params),
    enabled: view === "sessions",
  });

  const events = useQuery({
    queryKey: ["auth-events", username, page],
    queryFn: () =>
      api.get<Page<AuthEvent>>("/accounting/auth-events", { username, page, page_size: 25 }),
    enabled: view === "events",
  });

  async function downloadCsv() {
    const blob = await api.blob("/accounting/sessions.csv", {
      username,
      nas_ip: nasIp,
      active: active || undefined,
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "sessions.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <PageHeader
        title="Accounting"
        subtitle="Sessões (radacct) e eventos de autenticação (radpostauth)"
        actions={
          view === "sessions" && (
            <Button variant="ghost" onClick={downloadCsv}>
              Exportar CSV
            </Button>
          )
        }
      />

      <div className="mb-4 flex gap-1 border-b border-slate-200 dark:border-slate-800">
        {(["sessions", "events"] as const).map((v) => (
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
            {v === "sessions" ? "Sessões" : "Eventos de auth"}
          </button>
        ))}
      </div>

      <Card className="mb-3 flex flex-wrap gap-2">
        <input
          className="input max-w-[180px]"
          placeholder="Usuário"
          value={username}
          onChange={(e) => {
            setUsername(e.target.value);
            setPage(1);
          }}
        />
        {view === "sessions" && (
          <>
            <input
              className="input max-w-[160px]"
              placeholder="IP do NAS"
              value={nasIp}
              onChange={(e) => {
                setNasIp(e.target.value);
                setPage(1);
              }}
            />
            <select
              className="input max-w-[160px]"
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
          </>
        )}
      </Card>

      {view === "sessions" ? (
        <Card className="overflow-x-auto p-0">
          <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
            <thead className="bg-slate-50 dark:bg-slate-800/50">
              <tr>
                <th className="th">Usuário</th>
                <th className="th">NAS</th>
                <th className="th">Início</th>
                <th className="th">Fim</th>
                <th className="th">Duração</th>
                <th className="th">In / Out</th>
                <th className="th">Origem</th>
                <th className="th">Causa</th>
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
                    {s.nas_name && <div className="text-xs text-slate-400 dark:text-slate-500 dark:text-slate-400">{s.nas_name}</div>}
                  </td>
                  <td className="td">{fmtDate(s.acctstarttime)}</td>
                  <td className="td">
                    {s.active ? <Badge tone="green">ativa</Badge> : fmtDate(s.acctstoptime)}
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
                  <td className="td text-slate-400 dark:text-slate-500 dark:text-slate-400" colSpan={8}>
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
      ) : (
        <Card className="overflow-x-auto p-0">
          <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
            <thead className="bg-slate-50 dark:bg-slate-800/50">
              <tr>
                <th className="th">Data</th>
                <th className="th">Usuário</th>
                <th className="th">Resultado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {events.isLoading && (
                <tr>
                  <td className="td" colSpan={3}>
                    <Spinner className="h-5 w-5 text-brand-600" />
                  </td>
                </tr>
              )}
              {events.data?.items.map((e) => (
                <tr key={e.id}>
                  <td className="td">{fmtDate(e.authdate)}</td>
                  <td className="td font-medium">{e.username || "—"}</td>
                  <td className="td">
                    {e.accepted ? (
                      <Badge tone="green">{e.reply || "Access-Accept"}</Badge>
                    ) : (
                      <Badge tone="red">{e.reply || "Access-Reject"}</Badge>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {events.data && (
            <Pagination
              page={page}
              pageSize={events.data.page_size}
              total={events.data.total}
              onPage={setPage}
            />
          )}
        </Card>
      )}
    </div>
  );
}
