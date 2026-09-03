import { useQuery } from "@tanstack/react-query";
import { Card, PageHeader, Spinner } from "../../components/ui";
import { api, type Page } from "../../lib/api";
import { fmtDate } from "../../lib/format";

interface Stats {
  active_sessions: number;
  sessions_last_24h: number;
  accepts_last_24h: number;
  rejects_last_24h: number;
  top_users_24h: { username: string; sessions: number }[];
}
interface AuthEvent {
  id: number;
  username: string;
  reply: string;
  authdate: string;
  accepted: boolean;
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return (
    <Card className="flex flex-col gap-1">
      <span className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</span>
      <span className={`text-3xl font-bold ${tone ?? "text-slate-900 dark:text-slate-100"}`}>{value}</span>
    </Card>
  );
}

export default function DashboardPage() {
  const stats = useQuery({ queryKey: ["stats"], queryFn: () => api.get<Stats>("/accounting/stats") });
  const failures = useQuery({
    queryKey: ["recent-failures"],
    queryFn: () =>
      api.get<Page<AuthEvent>>("/accounting/auth-events", { accepted: false, page_size: 8 }),
  });

  return (
    <div>
      <PageHeader title="Painel" subtitle="Visão geral do AAA" />
      {stats.isLoading ? (
        <Spinner className="h-6 w-6 text-brand-600" />
      ) : (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Stat label="Sessões ativas" value={stats.data!.active_sessions} tone="text-emerald-600" />
          <Stat label="Sessões (24h)" value={stats.data!.sessions_last_24h} />
          <Stat label="Logins aceitos (24h)" value={stats.data!.accepts_last_24h} tone="text-brand-600" />
          <Stat label="Logins negados (24h)" value={stats.data!.rejects_last_24h} tone="text-rose-600" />
        </div>
      )}

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card>
          <h3 className="mb-3 font-semibold">Top utilizadores (24h)</h3>
          <ul className="divide-y divide-slate-100 dark:divide-slate-800 text-sm">
            {stats.data?.top_users_24h.length ? (
              stats.data.top_users_24h.map((u) => (
                <li key={u.username} className="flex justify-between py-2">
                  <span className="font-medium text-slate-700 dark:text-slate-200">{u.username}</span>
                  <span className="text-slate-500 dark:text-slate-400">{u.sessions} sessões</span>
                </li>
              ))
            ) : (
              <li className="py-2 text-slate-400 dark:text-slate-500 dark:text-slate-400">Sem dados</li>
            )}
          </ul>
        </Card>

        <Card>
          <h3 className="mb-3 font-semibold">Falhas de autenticação recentes</h3>
          <ul className="divide-y divide-slate-100 dark:divide-slate-800 text-sm">
            {failures.data?.items.length ? (
              failures.data.items.map((e) => (
                <li key={e.id} className="flex justify-between py-2">
                  <span className="font-medium text-slate-700 dark:text-slate-200">{e.username || "—"}</span>
                  <span className="text-xs text-slate-400 dark:text-slate-500 dark:text-slate-400">{fmtDate(e.authdate)}</span>
                </li>
              ))
            ) : (
              <li className="py-2 text-slate-400 dark:text-slate-500 dark:text-slate-400">Nenhuma falha recente</li>
            )}
          </ul>
        </Card>
      </div>
    </div>
  );
}
