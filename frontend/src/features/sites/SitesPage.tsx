import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge, Button, Card, Field, Modal, PageHeader, Spinner, useToast } from "../../components/ui";
import { api, ApiError } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { useT } from "../../lib/i18n";
import type { Site } from "../../lib/types";

interface FormState {
  id?: number;
  name: string;
  description: string;
}

export default function SitesPage() {
  const t = useT();
  const { can } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState<FormState | null>(null);

  const list = useQuery({ queryKey: ["sites"], queryFn: () => api.get<Site[]>("/sites") });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["sites"] });
    qc.invalidateQueries({ queryKey: ["equipment"] });
  };

  const save = useMutation({
    mutationFn: (f: FormState) => {
      const body = { name: f.name.trim(), description: f.description || null };
      return f.id ? api.patch(`/sites/${f.id}`, body) : api.post("/sites", body);
    },
    onSuccess: () => {
      toast("ok", t("Site salvo"));
      setForm(null);
      invalidate();
    },
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : t("Erro ao salvar")),
  });

  const remove = useMutation({
    mutationFn: (s: Site) => api.del(`/sites/${s.id}`),
    onSuccess: () => {
      toast("ok", t("Site removido"));
      invalidate();
    },
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : t("Erro ao remover")),
  });

  return (
    <div>
      <PageHeader
        title={t("Site/Localização")}
        subtitle={t("Locais onde os equipamentos estão instalados")}
        actions={<Button onClick={() => setForm({ name: "", description: "" })}>{t("Novo site")}</Button>}
      />
      <Card className="overflow-x-auto p-0">
        <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
          <thead className="bg-slate-50 dark:bg-slate-800/50">
            <tr>
              <th className="th">{t("Nome")}</th>
              <th className="th">{t("Descrição")}</th>
              <th className="th">{t("Equipamentos")}</th>
              <th className="th" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {list.isLoading && (
              <tr>
                <td className="td" colSpan={4}>
                  <Spinner className="h-5 w-5 text-brand-600" />
                </td>
              </tr>
            )}
            {list.data?.map((s) => (
              <tr key={s.id}>
                <td className="td font-medium">{s.name}</td>
                <td className="td">{s.description || "—"}</td>
                <td className="td">
                  <Badge tone="blue">{s.equipment_count}</Badge>
                </td>
                <td className="td text-right">
                  <div className="flex justify-end gap-2">
                    <button
                      className="text-brand-600 hover:underline dark:text-brand-400"
                      onClick={() => setForm({ id: s.id, name: s.name, description: s.description ?? "" })}
                    >
                      {t("Editar")}
                    </button>
                    {can("admin") && (
                      <button
                        className="text-rose-600 hover:underline dark:text-rose-400"
                        onClick={() => {
                          if (confirm(t("Remover {nome}?", { nome: s.name }))) remove.mutate(s);
                        }}
                      >
                        {t("Excluir")}
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {list.data?.length === 0 && (
              <tr>
                <td className="td text-slate-400 dark:text-slate-500" colSpan={4}>
                  {t("Nenhum site cadastrado.")}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>

      <Modal
        open={!!form}
        onClose={() => setForm(null)}
        title={form?.id ? t("Editar site") : t("Novo site")}
      >
        {form && (
          <form
            className="grid gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              save.mutate(form);
            }}
          >
            <Field label={t("Nome")}>
              <input
                className="input"
                value={form.name}
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
    </div>
  );
}
