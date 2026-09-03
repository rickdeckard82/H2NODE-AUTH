import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Badge, Card, Modal, PageHeader, Pagination, Spinner } from "../../components/ui";
import { api, type Page } from "../../lib/api";
import { useFmtDate } from "../../lib/datetime";
import type { AuditEntry } from "../../lib/types";

const ACTION_TONE: Record<string, "green" | "amber" | "red" | "blue" | "slate"> = {
  create: "green",
  update: "amber",
  delete: "red",
  login: "blue",
  reset_password: "amber",
};

function pretty(json: string | null) {
  if (!json) return "—";
  try {
    return JSON.stringify(JSON.parse(json), null, 2);
  } catch {
    return json;
  }
}

export default function AuditPage() {
  const fmtDate = useFmtDate();
  const [entityType, setEntityType] = useState("");
  const [action, setAction] = useState("");
  const [actor, setActor] = useState("");
  const [page, setPage] = useState(1);
  const [detail, setDetail] = useState<AuditEntry | null>(null);

  const list = useQuery({
    queryKey: ["audit", entityType, action, actor, page],
    queryFn: () =>
      api.get<Page<AuditEntry>>("/audit", {
        entity_type: entityType,
        action,
        actor,
        page,
        page_size: 30,
      }),
  });

  return (
    <div>
      <PageHeader title="Auditoria" subtitle="Todas as ações administrativas realizadas no painel" />

      <Card className="mb-3 flex flex-wrap gap-2">
        <input
          className="input max-w-[160px]"
          placeholder="Autor"
          value={actor}
          onChange={(e) => {
            setActor(e.target.value);
            setPage(1);
          }}
        />
        <select
          className="input max-w-[190px]"
          value={entityType}
          onChange={(e) => {
            setEntityType(e.target.value);
            setPage(1);
          }}
        >
          <option value="">Toda entidade</option>
          <option value="auth_user">auth_user</option>
          <option value="equipment">equipment</option>
          <option value="privilege_profile">privilege_profile</option>
          <option value="system_user">system_user</option>
        </select>
        <select
          className="input max-w-[160px]"
          value={action}
          onChange={(e) => {
            setAction(e.target.value);
            setPage(1);
          }}
        >
          <option value="">Toda ação</option>
          <option value="create">create</option>
          <option value="update">update</option>
          <option value="delete">delete</option>
          <option value="login">login</option>
          <option value="reset_password">reset_password</option>
        </select>
      </Card>

      <Card className="overflow-x-auto p-0">
        <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
          <thead className="bg-slate-50 dark:bg-slate-800/50">
            <tr>
              <th className="th">Data</th>
              <th className="th">Autor</th>
              <th className="th">Ação</th>
              <th className="th">Entidade</th>
              <th className="th">ID</th>
              <th className="th">Origem</th>
              <th className="th" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {list.isLoading && (
              <tr>
                <td className="td" colSpan={7}>
                  <Spinner className="h-5 w-5 text-brand-600" />
                </td>
              </tr>
            )}
            {list.data?.items.map((e) => (
              <tr key={e.id}>
                <td className="td">{fmtDate(e.created_at)}</td>
                <td className="td font-medium">{e.actor_username || "—"}</td>
                <td className="td">
                  <Badge tone={ACTION_TONE[e.action] ?? "slate"}>{e.action}</Badge>
                </td>
                <td className="td">{e.entity_type}</td>
                <td className="td">{e.entity_id || "—"}</td>
                <td className="td font-mono text-xs">{e.ip_address || "—"}</td>
                <td className="td text-right">
                  <button
                    className="text-brand-600 hover:underline dark:text-brand-400"
                    onClick={() => setDetail(e)}
                  >
                    Detalhes
                  </button>
                </td>
              </tr>
            ))}
            {list.data?.items.length === 0 && (
              <tr>
                <td className="td text-slate-400 dark:text-slate-500 dark:text-slate-400" colSpan={7}>
                  Nenhum registro.
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

      <Modal open={!!detail} onClose={() => setDetail(null)} title="Detalhe da auditoria" wide>
        {detail && (
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <div className="label">Antes</div>
              <pre className="max-h-80 overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
                {pretty(detail.before_json)}
              </pre>
            </div>
            <div>
              <div className="label">Depois</div>
              <pre className="max-h-80 overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
                {pretty(detail.after_json)}
              </pre>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
