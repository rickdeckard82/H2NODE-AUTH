import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { RefreshButton } from "../../components/RefreshButton";
import { Badge, Card, Modal, PageHeader, Pagination, Spinner } from "../../components/ui";
import { api, type Page } from "../../lib/api";
import { useFmtDate } from "../../lib/datetime";
import type { AuditEntry } from "../../lib/types";
import { shortUA } from "../../lib/ua";

type Tone = "green" | "amber" | "red" | "blue" | "slate";

const ACTION_TONE: Record<string, Tone> = {
  create: "green",
  update: "amber",
  delete: "red",
  login: "blue",
  reset_password: "amber",
  trust_device: "green",
  revoke_trusted_device: "amber",
  revoke_trusted_devices: "red",
};

type View = "actions" | "devices";

function safeParse(json: string | null): Record<string, unknown> {
  if (!json) return {};
  try {
    const v = JSON.parse(json);
    return v && typeof v === "object" ? v : {};
  } catch {
    return {};
  }
}

function pretty(json: string | null) {
  if (!json) return "—";
  try {
    return JSON.stringify(JSON.parse(json), null, 2);
  } catch {
    return json;
  }
}

/** Rótulo + tom para um evento de dispositivo 2FA. */
function deviceEvent(e: AuditEntry): { label: string; tone: Tone } {
  const meta = { ...safeParse(e.after_json), ...safeParse(e.before_json) };
  const reason = meta.reason as string | undefined;
  const why =
    reason === "mfa_disabled"
      ? " · 2FA desativado"
      : reason === "password_changed"
        ? " · senha alterada"
        : "";
  if (e.action === "trust_device") return { label: "Memorizado", tone: "green" };
  if (e.action === "revoke_trusted_device") return { label: `Removido${why}`, tone: "amber" };
  if (e.action === "revoke_trusted_devices") {
    const n = meta.count ? ` (${meta.count})` : "";
    return { label: `Removidos todos${n}${why}`, tone: "red" };
  }
  return { label: e.action, tone: "slate" };
}

function deviceLabel(e: AuditEntry): string {
  const meta = { ...safeParse(e.after_json), ...safeParse(e.before_json) };
  const ua = meta.user_agent as string | undefined;
  return ua ? shortUA(ua) : "—";
}

export default function AuditPage() {
  const fmtDate = useFmtDate();
  const [view, setView] = useState<View>("actions");
  const [entityType, setEntityType] = useState("");
  const [action, setAction] = useState("");
  const [actor, setActor] = useState("");
  const [page, setPage] = useState(1);
  const [detail, setDetail] = useState<AuditEntry | null>(null);

  const isDevices = view === "devices";

  const list = useQuery({
    queryKey: ["audit", view, entityType, action, actor, page],
    queryFn: () =>
      api.get<Page<AuditEntry>>("/audit", {
        entity_type: isDevices ? "mfa_trusted_device" : entityType,
        action: isDevices ? "" : action,
        actor,
        page,
        page_size: 30,
      }),
  });

  function switchView(v: View) {
    setView(v);
    setPage(1);
  }

  const tabs: [View, string][] = [
    ["actions", "Ações administrativas"],
    ["devices", "Dispositivos 2FA"],
  ];

  return (
    <div>
      <PageHeader
        title="Auditoria"
        subtitle={
          isDevices
            ? "Histórico de dispositivos memorizados no 2FA (memorização e remoção)"
            : "Todas as ações administrativas realizadas no painel"
        }
        actions={<RefreshButton keys={["audit"]} />}
      />

      <div className="mb-4 flex gap-1 border-b border-slate-200 dark:border-slate-800">
        {tabs.map(([v, label]) => (
          <button
            key={v}
            onClick={() => switchView(v)}
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

      <Card className="mb-3 flex flex-wrap gap-2">
        <input
          className="input max-w-[180px]"
          placeholder={isDevices ? "Utilizador" : "Autor"}
          value={actor}
          onChange={(e) => {
            setActor(e.target.value);
            setPage(1);
          }}
        />
        {!isDevices && (
          <>
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
              <option value="mfa_trusted_device">mfa_trusted_device</option>
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
          </>
        )}
      </Card>

      <Card className="overflow-x-auto p-0">
        <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
          <thead className="bg-slate-50 dark:bg-slate-800/50">
            <tr>
              <th className="th">Data</th>
              <th className="th">{isDevices ? "Utilizador" : "Autor"}</th>
              <th className="th">{isDevices ? "Evento" : "Ação"}</th>
              {isDevices ? (
                <th className="th">Dispositivo</th>
              ) : (
                <>
                  <th className="th">Entidade</th>
                  <th className="th">ID</th>
                </>
              )}
              <th className="th">Origem</th>
              <th className="th" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {list.isLoading && (
              <tr>
                <td className="td" colSpan={isDevices ? 5 : 7}>
                  <Spinner className="h-5 w-5 text-brand-600" />
                </td>
              </tr>
            )}
            {list.data?.items.map((e) => {
              const ev = isDevices ? deviceEvent(e) : null;
              return (
                <tr key={e.id}>
                  <td className="td">{fmtDate(e.created_at)}</td>
                  <td className="td font-medium">{e.actor_username || "—"}</td>
                  <td className="td">
                    <Badge tone={ev ? ev.tone : (ACTION_TONE[e.action] ?? "slate")}>
                      {ev ? ev.label : e.action}
                    </Badge>
                  </td>
                  {isDevices ? (
                    <td className="td">{deviceLabel(e)}</td>
                  ) : (
                    <>
                      <td className="td">{e.entity_type}</td>
                      <td className="td">{e.entity_id || "—"}</td>
                    </>
                  )}
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
              );
            })}
            {list.data?.items.length === 0 && (
              <tr>
                <td className="td text-slate-400 dark:text-slate-500" colSpan={isDevices ? 5 : 7}>
                  {isDevices ? "Nenhum dispositivo memorizado ainda." : "Nenhum registro."}
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
