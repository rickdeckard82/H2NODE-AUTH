import { useQuery } from "@tanstack/react-query";
import {
  AuthTrendChart,
  CompareBar,
  type DailyPoint,
  DonutChart,
  SessionsAreaChart,
} from "../../components/charts";
import { RefreshButton } from "../../components/RefreshButton";
import { Card, PageHeader, Spinner } from "../../components/ui";
import { api, type Page } from "../../lib/api";
import { useFmtDate } from "../../lib/datetime";
import { useT } from "../../lib/i18n";

interface Stats {
  active_sessions: number;
  sessions_7d: number;
  accepts_7d: number;
  rejects_7d: number;
  top_users_7d: { username: string; sessions: number }[];
  daily: DailyPoint[];
}
interface AuthEvent {
  id: number;
  username: string;
  reply: string;
  authdate: string;
  accepted: boolean;
  source_ip: string | null;
  nas_name: string | null;
}

function AuthEventList({
  title,
  tone,
  events,
  loading,
  emptyText,
}: {
  title: string;
  tone: "rose" | "emerald";
  events: AuthEvent[] | undefined;
  loading: boolean;
  emptyText: string;
}) {
  const fmtDate = useFmtDate();
  const dot = tone === "rose" ? "bg-rose-500" : "bg-emerald-500";
  return (
    <Card>
      <h3 className="mb-3 font-semibold">{title}</h3>
      <ul className="divide-y divide-slate-100 text-sm dark:divide-slate-800">
        {loading ? (
          <li className="py-2">
            <Spinner className="h-4 w-4 text-brand-600" />
          </li>
        ) : events && events.length ? (
          events.map((e) => (
            <li key={e.id} className="flex items-center justify-between gap-3 py-2">
              <span className="flex min-w-0 items-center gap-2 font-medium text-slate-700 dark:text-slate-200">
                <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${dot}`} />
                <span className="truncate">{e.username || "—"}</span>
              </span>
              <span className="flex shrink-0 flex-wrap items-baseline justify-end gap-x-2 text-xs text-slate-400 dark:text-slate-500">
                <span className="font-mono">{e.source_ip || "—"}</span>
                <span>{fmtDate(e.authdate)}</span>
              </span>
            </li>
          ))
        ) : (
          <li className="py-2 text-slate-400 dark:text-slate-500">{emptyText}</li>
        )}
      </ul>
    </Card>
  );
}

function Stat({
  label,
  value,
  accent = "bg-slate-300 dark:bg-slate-600",
  tone,
  hint,
}: {
  label: string;
  value: number;
  accent?: string;
  tone?: string;
  hint?: string;
}) {
  return (
    <Card className="relative overflow-hidden">
      <span className={`absolute inset-x-0 top-0 h-1 ${accent}`} />
      <span className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {label}
      </span>
      <div className="mt-1 flex items-baseline gap-2">
        <span className={`text-3xl font-bold tabular-nums ${tone ?? "text-slate-900 dark:text-slate-100"}`}>
          {value.toLocaleString("pt-BR")}
        </span>
        {hint && <span className="text-xs text-slate-400 dark:text-slate-500">{hint}</span>}
      </div>
    </Card>
  );
}

export default function DashboardPage() {
  const t = useT();
  const stats = useQuery({ queryKey: ["stats"], queryFn: () => api.get<Stats>("/accounting/stats") });
  const failures = useQuery({
    queryKey: ["recent-failures"],
    queryFn: () =>
      api.get<Page<AuthEvent>>("/accounting/authentication", { accepted: false, page_size: 8 }),
  });
  const successes = useQuery({
    queryKey: ["recent-successes"],
    queryFn: () =>
      api.get<Page<AuthEvent>>("/accounting/authentication", { accepted: true, page_size: 8 }),
  });

  const d = stats.data;
  const approval =
    d && d.accepts_7d + d.rejects_7d > 0
      ? Math.round((d.accepts_7d / (d.accepts_7d + d.rejects_7d)) * 100)
      : null;

  return (
    <div>
      <PageHeader
        title={t("Painel")}
        subtitle={t("Visão geral do AAA — últimos 7 dias")}
        actions={<RefreshButton keys={["stats", "recent-failures", "recent-successes"]} />}
      />

      {stats.isLoading || !d ? (
        <Spinner className="h-6 w-6 text-brand-600" />
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat
              label="Sessões ativas"
              value={d.active_sessions}
              tone="text-emerald-600 dark:text-emerald-400"
              accent="bg-emerald-500"
            />
            <Stat label="Sessões (7d)" value={d.sessions_7d} accent="bg-brand-500" />
            <Stat
              label="Logins aceitos (7d)"
              value={d.accepts_7d}
              tone="text-brand-600 dark:text-brand-400"
              accent="bg-brand-500"
              hint={approval !== null ? `${approval}% aprov.` : undefined}
            />
            <Stat
              label="Logins negados (7d)"
              value={d.rejects_7d}
              tone="text-rose-600 dark:text-rose-400"
              accent="bg-rose-500"
            />
          </div>

          <Card className="space-y-5">
            <AuthTrendChart data={d.daily} />
            <div className="border-t border-slate-100 pt-4 dark:border-slate-800">
              <CompareBar accepts={d.accepts_7d} rejects={d.rejects_7d} />
            </div>
          </Card>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <SessionsAreaChart data={d.daily} />
            </Card>

            <Card>
              <h3 className="mb-4 font-semibold">Top usuários · 7 dias</h3>
              <DonutChart
                data={d.top_users_7d.map((u) => ({ label: u.username, value: u.sessions }))}
                unit="sessões"
                empty="Sem sessões nos últimos 7 dias"
              />
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <AuthEventList
              title={t("Falhas de autenticação recentes")}
              tone="rose"
              events={failures.data?.items}
              loading={failures.isLoading}
              emptyText="Nenhuma falha recente"
            />
            <AuthEventList
              title={t("Sucessos de autenticação recentes")}
              tone="emerald"
              events={successes.data?.items}
              loading={successes.isLoading}
              emptyText="Nenhum sucesso recente"
            />
          </div>
        </div>
      )}
    </div>
  );
}
