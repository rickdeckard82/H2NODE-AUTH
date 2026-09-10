import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Field,
  Modal,
  PageHeader,
  Spinner,
  useToast,
} from "../../components/ui";
import { api, ApiError } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { fmtDate } from "../../lib/format";
import type { AuthGroup, AuthGroupCidr } from "../../lib/types";

interface FormState {
  id?: number;
  name: string;
  description: string;
  cidrs: AuthGroupCidr[];
}

const empty: FormState = { name: "", description: "", cidrs: [] };

export default function UserGroupsPage() {
  const { can } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();
  const writable = can("admin"); // criar/editar/excluir grupo é só admin+

  const [form, setForm] = useState<FormState | null>(null);

  const list = useQuery({
    queryKey: ["auth-groups"],
    queryFn: () => api.get<AuthGroup[]>("/auth-groups"),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["auth-groups"] });
    qc.invalidateQueries({ queryKey: ["auth-users"] });
  };

  const save = useMutation({
    mutationFn: (f: FormState) => {
      const body = {
        name: f.name,
        description: f.description || null,
        cidrs: f.cidrs
          .filter((c) => c.cidr.trim())
          .map((c) => ({ cidr: c.cidr.trim(), note: c.note || null })),
      };
      return f.id ? api.patch(`/auth-groups/${f.id}`, body) : api.post("/auth-groups", body);
    },
    onSuccess: () => {
      toast("ok", "Grupo salvo");
      setForm(null);
      invalidate();
    },
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : "Erro ao salvar"),
  });

  const remove = useMutation({
    mutationFn: (g: AuthGroup) => api.del(`/auth-groups/${g.id}`),
    onSuccess: () => {
      toast("ok", "Grupo removido");
      invalidate();
    },
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : "Erro ao remover"),
  });

  function addRow() {
    if (form) setForm({ ...form, cidrs: [...form.cidrs, { cidr: "", note: null }] });
  }

  return (
    <div>
      <PageHeader
        title="Grupos de usuário"
        subtitle="Restringem a autenticação por IP de origem: fora das faixas do grupo, o RADIUS rejeita"
        actions={writable && <Button onClick={() => setForm({ ...empty })}>Novo grupo</Button>}
      />

      {list.isLoading ? (
        <Spinner className="h-6 w-6 text-brand-600" />
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {list.data?.map((g) => (
            <Card key={g.id}>
              <div className="mb-2 flex items-center justify-between">
                <h3 className="font-semibold">{g.name}</h3>
                <Badge tone={g.member_count ? "blue" : "slate"}>
                  {g.member_count} usuário{g.member_count === 1 ? "" : "s"}
                </Badge>
              </div>
              <p className="mb-3 text-sm text-slate-500 dark:text-slate-400">
                {g.description || "—"}
              </p>
              <div className="space-y-1 text-xs">
                {g.cidrs.length ? (
                  g.cidrs.map((c) => (
                    <div key={c.id} className="flex gap-2 font-mono text-slate-600 dark:text-slate-300">
                      <span>{c.cidr}</span>
                      {c.note && (
                        <span className="text-slate-400 dark:text-slate-500">— {c.note}</span>
                      )}
                    </div>
                  ))
                ) : (
                  <span className="text-rose-600 dark:text-rose-400">
                    sem faixas — nenhum IP autenticaria neste grupo
                  </span>
                )}
              </div>
              <div className="mt-3 flex items-center justify-between">
                <span className="text-xs text-slate-400 dark:text-slate-500">
                  {fmtDate(g.updated_at)}
                </span>
                {writable && (
                  <div className="flex gap-2">
                    <Button
                      variant="ghost"
                      onClick={() =>
                        setForm({
                          id: g.id,
                          name: g.name,
                          description: g.description ?? "",
                          cidrs: g.cidrs.map((c) => ({ ...c })),
                        })
                      }
                    >
                      Editar
                    </Button>
                    <Button
                      variant="danger"
                      onClick={() => {
                        if (confirm(`Remover o grupo ${g.name}?`)) remove.mutate(g);
                      }}
                    >
                      Excluir
                    </Button>
                  </div>
                )}
              </div>
            </Card>
          ))}
          {list.data?.length === 0 && (
            <p className="text-sm text-slate-400 dark:text-slate-500">Nenhum grupo cadastrado.</p>
          )}
        </div>
      )}

      <Modal
        open={!!form}
        onClose={() => setForm(null)}
        title={form?.id ? "Editar grupo" : "Novo grupo de usuário"}
        wide
      >
        {form && (
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              save.mutate(form);
            }}
          >
            <div className="grid grid-cols-2 gap-3">
              <Field label="Nome">
                <input
                  className="input"
                  value={form.name}
                  pattern="[a-zA-Z0-9._\-]+"
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                />
              </Field>
              <Field label="Descrição">
                <input
                  className="input"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                />
              </Field>
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between">
                <span className="label mb-0">IPs de origem permitidos</span>
                <Button type="button" variant="ghost" onClick={addRow}>
                  + Faixa
                </Button>
              </div>
              <div className="space-y-2">
                {form.cidrs.map((c, idx) => (
                  <div key={idx} className="grid grid-cols-12 gap-2">
                    <input
                      className="input col-span-5 font-mono"
                      placeholder="10.0.0.0/24  ou  192.168.1.5"
                      value={c.cidr}
                      onChange={(e) => {
                        const cidrs = [...form.cidrs];
                        cidrs[idx] = { ...c, cidr: e.target.value };
                        setForm({ ...form, cidrs });
                      }}
                      required
                    />
                    <input
                      className="input col-span-6"
                      placeholder="observação (opcional)"
                      value={c.note ?? ""}
                      onChange={(e) => {
                        const cidrs = [...form.cidrs];
                        cidrs[idx] = { ...c, note: e.target.value || null };
                        setForm({ ...form, cidrs });
                      }}
                    />
                    <button
                      type="button"
                      className="col-span-1 text-rose-500 hover:text-rose-700 dark:text-rose-400"
                      onClick={() =>
                        setForm({ ...form, cidrs: form.cidrs.filter((_, i) => i !== idx) })
                      }
                    >
                      ✕
                    </button>
                  </div>
                ))}
                {form.cidrs.length === 0 && (
                  <p className="text-sm text-amber-600 dark:text-amber-400">
                    Sem faixas: enquanto vazio, nenhum usuário do grupo consegue autenticar.
                  </p>
                )}
              </div>
              <p className="mt-2 text-xs text-slate-400 dark:text-slate-500">
                Aceita IPv4/IPv6, com ou sem máscara (IP simples = /32 ou /128). O IP
                comparado é o de origem do pacote RADIUS.
              </p>
            </div>

            <div className="flex justify-end gap-2">
              <Button type="button" variant="ghost" onClick={() => setForm(null)}>
                Cancelar
              </Button>
              <Button type="submit" loading={save.isPending}>
                Salvar
              </Button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
