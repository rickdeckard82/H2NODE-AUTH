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
import type { Manufacturer, PrivilegeProfile, ProfileAttr } from "../../lib/types";
import { useT } from "../../lib/i18n";

interface FormState {
  id?: number;
  name: string;
  description: string;
  is_builtin: boolean;
  attrs: ProfileAttr[];
  tacacs_priv_level: number;
  tacacs_extra_avpairs: string;
}

export default function PrivilegeProfilesPage() {
  const t = useT();
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState<FormState | null>(null);

  const manufacturers = useQuery({
    queryKey: ["manufacturers"],
    queryFn: () => api.get<Manufacturer[]>("/manufacturers"),
  });
  const profiles = useQuery({
    queryKey: ["profiles"],
    queryFn: () => api.get<PrivilegeProfile[]>("/privilege-profiles"),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["profiles"] });
  };

  const save = useMutation({
    mutationFn: (f: FormState) => {
      const body: Record<string, unknown> = {
        name: f.name,
        description: f.description || null,
        tacacs_priv_level: f.tacacs_priv_level,
        tacacs_extra_avpairs: f.tacacs_extra_avpairs || null,
        attrs: f.attrs.map((a) => ({
          manufacturer_id: a.manufacturer_id,
          attribute: a.attribute,
          op: a.op || ":=",
          value: a.value,
        })),
      };
      return f.id
        ? api.patch(`/privilege-profiles/${f.id}`, body)
        : api.post("/privilege-profiles", body);
    },
    onSuccess: () => {
      toast("ok", t("Perfil salvo — radgroupreply regenerado"));
      setForm(null);
      invalidate();
    },
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : t("Erro ao salvar")),
  });

  const remove = useMutation({
    mutationFn: (p: PrivilegeProfile) => api.del(`/privilege-profiles/${p.id}`),
    onSuccess: () => {
      toast("ok", t("Perfil removido"));
      invalidate();
    },
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : t("Erro ao remover")),
  });

  function mfrName(id: number) {
    return manufacturers.data?.find((m) => m.id === id)?.display_name ?? `#${id}`;
  }

  function addRow() {
    if (!form) return;
    const mid = manufacturers.data?.[0]?.id ?? 1;
    setForm({
      ...form,
      attrs: [...form.attrs, { manufacturer_id: mid, attribute: "", op: ":=", value: "" }],
    });
  }

  return (
    <div>
      <PageHeader
        title={t("Perfis de privilégio")}
        subtitle={t("Mapeiam um perfil abstrato para atributos RADIUS de cada fabricante (radgroupreply)")}
        actions={
          <Button
            onClick={() =>
              setForm({ name: "", description: "", is_builtin: false, attrs: [], tacacs_priv_level: 1, tacacs_extra_avpairs: "" })
            }
          >{t("Novo perfil")}</Button>
        }
      />

      {profiles.isLoading ? (
        <Spinner className="h-6 w-6 text-brand-600" />
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {profiles.data?.map((p) => (
            <Card key={p.id}>
              <div className="mb-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold">{p.name}</h3>
                  {p.is_builtin && <Badge>{t("interno")}</Badge>}
                </div>
                <code className="text-xs text-slate-400 dark:text-slate-500 dark:text-slate-400">{p.group_name}</code>
              </div>
              <p className="mb-3 text-sm text-slate-500 dark:text-slate-400">{p.description ? t(p.description) : "—"}</p>
              <div className="space-y-1 text-xs">
                {p.attrs.map((a) => (
                  <div key={a.id} className="flex gap-2 font-mono text-slate-600 dark:text-slate-300">
                    <span className="w-16 shrink-0 text-slate-400 dark:text-slate-500 dark:text-slate-400">{mfrName(a.manufacturer_id)}</span>
                    <span>
                      {a.attribute} {a.op} {a.value}
                    </span>
                  </div>
                ))}
                {p.attrs.length === 0 && <span className="text-slate-400 dark:text-slate-500 dark:text-slate-400">{t("Sem atributos")}</span>}
              </div>
              <div className="mt-3 flex gap-2">
                <Button
                  variant="ghost"
                  onClick={() =>
                    setForm({
                      id: p.id,
                      name: p.name,
                      description: p.description ?? "",
                      tacacs_priv_level: p.tacacs_priv_level,
                      tacacs_extra_avpairs: p.tacacs_extra_avpairs ?? "",
                      is_builtin: p.is_builtin,
                      attrs: p.attrs.map((a) => ({ ...a })),
                    })
                  }
                >
                  {t("Editar")}
                </Button>
                {!p.is_builtin && (
                  <Button
                    variant="danger"
                    onClick={() => {
                      if (confirm(t("Remover o perfil {nome}?", { nome: p.name }))) remove.mutate(p);
                    }}
                  >
                    {t("Excluir")}
                  </Button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal
        open={!!form}
        onClose={() => setForm(null)}
        title={form?.id ? t("Editar perfil") : t("Novo perfil de privilégio")}
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
              <Field label={t("Nome (gera o grupo profile_<nome>)")}>
                <input
                  className="input"
                  value={form.name}
                  disabled={form.is_builtin}
                  pattern="[a-zA-Z0-9._\-]+"
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                />
              </Field>
              <Field label={t("Descrição")}>
                <input
                  className="input"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                />
              </Field>
            </div>

            <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
              <div className="label mb-2">TACACS+ (Huawei / Juniper / Datacom)</div>
              <div className="grid grid-cols-2 gap-3">
                <Field label={t("priv-lvl (exec)")} hint="0–15">
                  <input
                    className="input"
                    type="number"
                    min={0}
                    max={15}
                    value={form.tacacs_priv_level}
                    onChange={(e) =>
                      setForm({ ...form, tacacs_priv_level: Number(e.target.value) })
                    }
                  />
                </Field>
                <Field label={t("AV pairs extra")} hint={t("um por linha, ex.: shell:roles=network-admin")}>
                  <textarea
                    className="input h-[38px] font-mono"
                    rows={2}
                    value={form.tacacs_extra_avpairs}
                    onChange={(e) =>
                      setForm({ ...form, tacacs_extra_avpairs: e.target.value })
                    }
                  />
                </Field>
              </div>
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between">
                <span className="label mb-0">{t("Atributos por fabricante")}</span>
                <Button type="button" variant="ghost" onClick={addRow}>
                  + Linha
                </Button>
              </div>
              <div className="space-y-2">
                {form.attrs.map((a, idx) => (
                  <div key={idx} className="grid grid-cols-12 gap-2">
                    <select
                      className="input col-span-3"
                      value={a.manufacturer_id}
                      onChange={(e) => {
                        const attrs = [...form.attrs];
                        attrs[idx] = { ...a, manufacturer_id: Number(e.target.value) };
                        setForm({ ...form, attrs });
                      }}
                    >
                      {manufacturers.data?.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.display_name}
                        </option>
                      ))}
                    </select>
                    <input
                      className="input col-span-5 font-mono"
                      placeholder={t("Atributo (ex.: Huawei-Exec-Privilege)")}
                      value={a.attribute}
                      onChange={(e) => {
                        const attrs = [...form.attrs];
                        attrs[idx] = { ...a, attribute: e.target.value };
                        setForm({ ...form, attrs });
                      }}
                      required
                    />
                    <input
                      className="input col-span-1 text-center font-mono"
                      value={a.op}
                      onChange={(e) => {
                        const attrs = [...form.attrs];
                        attrs[idx] = { ...a, op: e.target.value };
                        setForm({ ...form, attrs });
                      }}
                    />
                    <input
                      className="input col-span-2 font-mono"
                      placeholder={t("Valor")}
                      value={a.value}
                      onChange={(e) => {
                        const attrs = [...form.attrs];
                        attrs[idx] = { ...a, value: e.target.value };
                        setForm({ ...form, attrs });
                      }}
                      required
                    />
                    <button
                      type="button"
                      className="col-span-1 text-rose-500 hover:text-rose-700 dark:text-rose-400"
                      onClick={() =>
                        setForm({ ...form, attrs: form.attrs.filter((_, i) => i !== idx) })
                      }
                    >
                      ✕
                    </button>
                  </div>
                ))}
                {form.attrs.length === 0 && (
                  <p className="text-sm text-slate-400 dark:text-slate-500 dark:text-slate-400">
                    Nenhum atributo. Adicione ao menos um por fabricante que for usar.
                  </p>
                )}
              </div>
            </div>

            <div className="flex justify-end gap-2">
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
    </div>
  );
}
