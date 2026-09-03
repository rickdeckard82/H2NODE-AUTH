import { useState, type ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { AppFooter } from "../components/AppFooter";
import { ICONS, type IconName } from "../components/icons";
import { Logo } from "../components/Logo";
import { Button } from "../components/ui";
import { useAuth, type Role } from "../lib/auth";

interface NavLeaf {
  to: string;
  label: string;
  icon: IconName;
  roles?: Role[];
}

interface NavGroup {
  label: string;
  icon: IconName;
  children: NavLeaf[];
}

type NavEntry = NavLeaf | NavGroup;

const isGroup = (e: NavEntry): e is NavGroup => "children" in e;

const NAV: NavEntry[] = [
  { to: "/", label: "Painel", icon: "home" },
  {
    label: "Equipamentos",
    icon: "server",
    children: [
      { to: "/equipment", label: "Equipamentos", icon: "server" },
      { to: "/manufacturers", label: "Grupo de equipamentos", icon: "layers", roles: ["admin"] },
    ],
  },
  {
    label: "Usuários",
    icon: "users",
    children: [
      { to: "/auth-users", label: "Usuários de autenticação", icon: "idCard" },
      { to: "/user-groups", label: "Grupos de usuário", icon: "users" },
      { to: "/profiles", label: "Perfis de privilégio", icon: "shield", roles: ["admin"] },
    ],
  },
  {
    label: "Relatórios",
    icon: "barChart",
    children: [
      { to: "/auth-log", label: "Authentication", icon: "activity" },
      { to: "/authz-log", label: "Authorization", icon: "shield" },
      { to: "/accounting", label: "Accounting", icon: "barChart" },
      { to: "/audit", label: "Auditoria", icon: "clipboard" },
    ],
  },
  {
    label: "Configuração",
    icon: "settings",
    children: [
      { to: "/system-users", label: "Utilizadores do sistema", icon: "userCog", roles: ["superadmin"] },
      { to: "/backup", label: "Backup e restauração", icon: "database", roles: ["superadmin"] },
    ],
  },
];

const leafClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium ${
    isActive
      ? "bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300"
      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white"
  }`;

export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout, can } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const canSee = (roles?: Role[]) => !roles || can(...roles);

  // grupos visíveis, já filtrados por permissão
  const entries: NavEntry[] = NAV.map((e) => {
    if (!isGroup(e)) return e;
    return { ...e, children: e.children.filter((c) => canSee(c.roles)) };
  }).filter((e) => !isGroup(e) || e.children.length > 0);

  // grupos começam abertos; o toggle apenas recolhe/expande
  const isOpen = (g: NavGroup) => !collapsed[g.label];
  const toggle = (label: string) => setCollapsed((c) => ({ ...c, [label]: !c[label] }));

  async function doLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-screen lg:flex">
      <aside
        className={`${
          open ? "flex" : "hidden"
        } w-full shrink-0 flex-col border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 lg:flex lg:h-screen lg:w-64 lg:sticky lg:top-0`}
      >
        <div className="flex items-center gap-2.5 px-4 py-4">
          <Logo className="h-14 w-14 shrink-0" />
          <span className="text-lg font-bold tracking-tight">Pulse RADIUS</span>
        </div>

        <nav className="flex flex-1 flex-col gap-1 overflow-y-auto px-3 pb-6">
          {entries.map((e) => {
            if (!isGroup(e)) {
              const Icon = ICONS[e.icon];
              return (
                <NavLink
                  key={e.to}
                  to={e.to}
                  end={e.to === "/"}
                  onClick={() => setOpen(false)}
                  className={leafClass}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {e.label}
                </NavLink>
              );
            }
            const GroupIcon = ICONS[e.icon];
            return (
              <div key={e.label} className="mt-2">
                <button
                  type="button"
                  onClick={() => toggle(e.label)}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300"
                  aria-expanded={isOpen(e)}
                >
                  <GroupIcon className="h-4 w-4 shrink-0" />
                  <span className="flex-1 text-left">{e.label}</span>
                  <svg
                    className={`h-3.5 w-3.5 transition-transform ${isOpen(e) ? "rotate-90" : ""}`}
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path d="M7 5l6 5-6 5V5z" />
                  </svg>
                </button>
                {isOpen(e) && (
                  <div className="mt-0.5 flex flex-col gap-0.5 border-l border-slate-200 pl-2 dark:border-slate-800">
                    {e.children.map((c) => {
                      const Icon = ICONS[c.icon];
                      return (
                        <NavLink
                          key={c.to}
                          to={c.to}
                          onClick={() => setOpen(false)}
                          className={leafClass}
                        >
                          <Icon className="h-4 w-4 shrink-0" />
                          {c.label}
                        </NavLink>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        <AppFooter className="px-4 py-3" />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
          <button
            className="rounded-lg border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 lg:hidden"
            onClick={() => setOpen((v) => !v)}
          >
            ☰
          </button>
          <div className="ml-auto flex items-center gap-3 text-sm">
            <div className="text-right">
              <div className="font-semibold text-slate-800 dark:text-slate-100">{user?.full_name}</div>
              <div className="text-xs uppercase tracking-wide text-slate-400 dark:text-slate-500">{user?.role}</div>
            </div>
            <Button variant="ghost" onClick={doLogout}>
              Sair
            </Button>
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
