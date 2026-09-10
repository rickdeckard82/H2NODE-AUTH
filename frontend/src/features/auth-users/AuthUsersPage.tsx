import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Field,
  Modal,
  PageHeader,
  Pagination,
  Spinner,
  useToast,
} from "../../components/ui";
import { api, ApiError, type Page } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { fmtDate } from "../../lib/format";
import type { AuthGroup, AuthUser, PrivilegeProfile } from "../../lib/types";
import { useT } from "../../lib/i18n";

interface FormState {
  id?: number;
  username: string;
  full_name: string;
  email: string;
  privilege_profile_id: number | "";
  auth_group_id: number | "";
  is_active: boolean;
  expires_at: string;
  password: string;
}

const empty: FormState = {
  username: "",
  full_name: "",
  email: "",
  privilege_profile_id: "",
  auth_group_id: "",
  is_active: true,
  expires_at: "",
  password: "",
};

export default function AuthUsersPage() {
  const t = useT();
  const { can } = useAuth();
  const canDelete = can("admin");
  const qc = useQueryClient();
  const toast = useToast();
  const writable = can("operator");

  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [form, setForm] = useState<FormState | null>(null);
  const [pwTarget, setPwTarget] = useState<AuthUser | null>(null);
  const [newPw, setNewPw] = useState("");

  const profiles = useQuery({
    queryKey: ["profiles"],
    queryFn: () => api.get<PrivilegeProfile[]>("/privilege-profiles"),
  });

  const groups = useQuery({
    queryKey: ["auth-groups"],
    queryFn: () => api.get<AuthGroup[]>("/auth-groups"),
  });

  const list = useQuery({
    queryKey: ["auth-users", q, page],
    queryFn: () =>
      api.get<Page<AuthUser>>("/auth-users", { q, page, page_size: 20 }),
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["auth-users"] });

  const save = useMutation({
    mutationFn: (f: FormState) => {
      const body: Record<string, unknown> = {
        full_name: f.full_name || null,
        email: f.email || null,
        privilege_profile_id: f.privilege_profile_id,
        // "" => sem grupo. No PATCH mandamos 0 para desvincular.
        auth_group_id: f.auth_group_id === "" ? (f.id ? 0 : null) : f.auth_group_id,
        is_active: f.is_active,
        expires_at: f.expires_at ? new Date(f.expires_at).toISOString() : null,
      };
      if (f.id) return api.patch(`/auth-users/${f.id}`, body);
      return api.post("/auth-users", { ...body, username: f.username, password: f.password });
    },
    onSuccess: () => {
      toast("ok", t("Usuário salvo"));
      setForm(null);
      invalidate();
    },
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : t("Erro ao salvar")),
  });

  const toggle = useMutation({
    mutationFn: (u: AuthUser) => api.patch(`/auth-users/${u.id}`, { is_active: !u.is_active }),
    onSuccess: invalidate,
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : t("Erro")),
  });

  const remove = useMutation({
    mutationFn: (u: AuthUser) => api.del(`/auth-users/${u.id}`),
    onSuccess: () => {
      toast("ok", t("Usuário removido"));
      invalidate();
    },
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : t("Erro ao remover")),
  });

  const resetPw = useMutation({
    mutationFn: () => api.post(`/auth-users/${pwTarget!.id}/reset-password`, { password: newPw }),
    onSuccess: () => {
      toast("ok", t("Senha redefinida"));
      setPwTarget(null);
      setNewPw("");
    },
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : t("Erro")),
  });

  return (
    <div>
      <PageHeader
        title={t("Usuários de autenticação")}
        subtitle={t("Contas que autenticam nos equipamentos via RADIUS")}
        actions={
          writable && (
            <Button onClick={() => setForm({ ...empty })}>{t("Novo usuário")}</Button>
          )
        }
      />

      <Card className="mb-3">
        <input
          className="input max-w-xs"
          placeholder={t("Buscar por login, nome ou e-mail…")}
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setPage(1);
          }}
        />
      </Card>

      <Card className="overflow-x-auto p-0">
        <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
          <thead className="bg-slate-50 dark:bg-slate-800/50">
            <tr>
              <th className="th">{t("Login")}</th>
              <th className="th">{t("Nome")}</th>
              <th className="th">{t("Perfil")}</th>
              <th className="th">{t("Grupo")}</th>
              <th className="th">{t("Estado")}</th>
              <th className="th">{t("Expira")}</th>
              <th className="th">{t("Último acesso")}</th>
              <th className="th" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {list.isLoading && (
              <tr>
                <td className="td" colSpan={8}>
                  <Spinner className="h-5 w-5 text-brand-600" />
                </td>
              </tr>
            )}
            {list.data?.items.map((u) => (
              <tr key={u.id}>
                <td className="td font-medium">{u.username}</td>
                <td className="td">{u.full_name || "—"}</td>
                <td className="td">
                  <Badge tone="blue">{u.profile_name}</Badge>
                </td>
                <td className="td">
                  {u.auth_group_name ? (
                    <Badge tone="amber">{u.auth_group_name}</Badge>
                  ) : (
                    <span className="text-slate-400 dark:text-slate-500">—</span>
                  )}
                </td>
                <td className="td">
                  {u.is_active ? (
                    <Badge tone="green">{t("ativo")}</Badge>
                  ) : (
                    <Badge tone="red">{t("inativo")}</Badge>
                  )}
                </td>
                <td className="td">{u.expires_at ? fmtDate(u.expires_at) : "—"}</td>
                <td className="td">{fmtDate(u.last_auth_at)}</td>
                <td className="td text-right">
                  {writable && (
                    <div className="flex justify-end gap-2">
                      <button
                        className="text-brand-600 hover:underline dark:text-brand-400"
                        onClick={() =>
                          setForm({
                            id: u.id,
                            username: u.username,
                            full_name: u.full_name ?? "",
                            email: u.email ?? "",
                            privilege_profile_id: u.privilege_profile_id,
                            auth_group_id: u.auth_group_id ?? "",
                            is_active: u.is_active,
                            expires_at: u.expires_at ? u.expires_at.slice(0, 16) : "",
                            password: "",
                          })
                        }
                      >
                        {t("Editar")}
                      </button>
                      <button
                        className="text-slate-600 hover:underline dark:text-slate-300"
                        onClick={() => setPwTarget(u)}
                      >
                        {t("Senha")}
                      </button>
                      <button
                        className="text-amber-600 hover:underline dark:text-amber-400"
                        onClick={() => toggle.mutate(u)}
                      >
                        {u.is_active ? t("Desativar") : t("Ativar")}
                      </button>
                      {canDelete && (
                        <button
                          className="text-rose-600 hover:underline dark:text-rose-400"
                          onClick={() => {
                            if (confirm(t("Remover {nome}?", { nome: u.username }))) remove.mutate(u);
                          }}
                        >
                          {t("Excluir")}
                        </button>
                      )}
                    </div>
                  )}
                </td>
              </tr>
            ))}
            {list.data?.items.length === 0 && (
              <tr>
                <td className="td text-slate-400 dark:text-slate-500" colSpan={8}>
                  {t("Nenhum usuário encontrado.")}
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

      <Modal
        open={!!form}
        onClose={() => setForm(null)}
        title={form?.id ? t("Editar usuário") : t("Novo usuário de autenticação")}
      >
        {form && (
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              save.mutate(form);
            }}
          >
            <Field label={t("Login (username no equipamento)")}>
              <input
                className="input"
                value={form.username}
                disabled={!!form.id}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
                required
                pattern="[a-zA-Z0-9._@\-]+"
              />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label={t("Nome completo")}>
                <input
                  className="input"
                  value={form.full_name}
                  onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                />
              </Field>
              <Field label={t("E-mail")}>
                <input
                  className="input"
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                />
              </Field>
            </div>
            <Field label={t("Perfil de privilégio")}>
              <select
                className="input"
                value={form.privilege_profile_id}
                onChange={(e) =>
                  setForm({ ...form, privilege_profile_id: Number(e.target.value) })
                }
                required
              >
                <option value="" disabled>
                  {t("Selecione…")}
                </option>
                {profiles.data?.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} — {p.description}
                  </option>
                ))}
              </select>
            </Field>
            <Field
              label={t("Grupo de usuário (restrição de IP de origem)")}
              hint={t("Opcional. Se definido, só autentica de IPs nas faixas do grupo.")}
            >
              <select
                className="input"
                value={form.auth_group_id}
                onChange={(e) =>
                  setForm({
                    ...form,
                    auth_group_id: e.target.value === "" ? "" : Number(e.target.value),
                  })
                }
              >
                <option value="">{t("— sem grupo (sem restrição de IP) —")}</option>
                {groups.data?.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.name}
                    {g.cidrs.length ? ` (${g.cidrs.length} faixa${g.cidrs.length === 1 ? "" : "s"})` : " — sem faixas!"}
                  </option>
                ))}
              </select>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label={t("Expira em (opcional)")}>
                <input
                  className="input"
                  type="datetime-local"
                  value={form.expires_at}
                  onChange={(e) => setForm({ ...form, expires_at: e.target.value })}
                />
              </Field>
              <label className="mt-6 flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                />
                {t("Conta ativa")}
              </label>
            </div>
            {!form.id && (
              <Field label={t("Senha")} hint={t("Mínimo 12 caracteres. Armazenada como hash SSHA2-512.")}>
                <input
                  className="input"
                  type="password"
                  value={form.password}
                  minLength={12}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  required
                />
              </Field>
            )}
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="ghost" onClick={() => setForm(null)}>
                {t("Cancelar")}
              </Button>
              <Button type="submit" loading={save.isPending}>
                {t("Salvar")}
              </Button>
            </div>
          </form>
        )}
      </Modal>

      <Modal
        open={!!pwTarget}
        onClose={() => setPwTarget(null)}
        title={t("Redefinir senha — {nome}", { nome: pwTarget?.username ?? "" })}
      >
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            resetPw.mutate();
          }}
        >
          <Field label={t("Nova senha")} hint={t("Mínimo 12 caracteres.")}>
            <input
              className="input"
              type="password"
              minLength={12}
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              required
            />
          </Field>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => setPwTarget(null)}>
              {t("Cancelar")}
            </Button>
            <Button type="submit" loading={resetPw.isPending}>
              {t("Redefinir")}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
