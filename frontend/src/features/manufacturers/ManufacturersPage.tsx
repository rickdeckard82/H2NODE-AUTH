import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge, Button, Card, Field, Modal, PageHeader, Spinner, useToast } from "../../components/ui";
import { api, ApiError } from "../../lib/api";
import { fmtDate } from "../../lib/format";
import { VENDOR_KINDS, type Manufacturer, type VendorKind } from "../../lib/types";

interface FormState {
  id?: number;
  name: string;
  display_name: string;
  vendor_kind: VendorKind;
  radius_vendor_id: string;
  notes: string;
  radius_secret: string;
  clear_secret: boolean;
}

const empty: FormState = {
  name: "",
  display_name: "",
  vendor_kind: "generic",
  radius_vendor_id: "",
  notes: "",
  radius_secret: "",
  clear_secret: false,
};

const KIND_HINT: Record<VendorKind, string> = {
  huawei: "envia Huawei-Exec-Privilege",
  juniper: "envia Juniper-Local-User-Name",
  datacom: "envia Datacom-Privilege-Level",
  mikrotik: "envia Mikrotik-Group",
  generic: "não filtra VSA — envia todos os atributos do perfil",
};

export default function ManufacturersPage() {
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState<FormState | null>(null);

  const list = useQuery({
    queryKey: ["manufacturers"],
    queryFn: () => api.get<Manufacturer[]>("/manufacturers"),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["manufacturers"] });
    qc.invalidateQueries({ queryKey: ["equipment"] });
  };

  const save = useMutation({
    mutationFn: (f: FormState) => {
      const common = {
        display_name: f.display_name,
        vendor_kind: f.vendor_kind,
        radius_vendor_id: f.radius_vendor_id ? Number(f.radius_vendor_id) : null,
        notes: f.notes || null,
      };
      if (f.id) {
        const body: Record<string, unknown> = { ...common };
        if (f.clear_secret) body.clear_secret = true;
        else if (f.radius_secret) body.radius_secret = f.radius_secret;
        return api.patch(`/manufacturers/${f.id}`, body);
      }
      return api.post("/manufacturers", {
        ...common,
        name: f.name,
        radius_secret: f.radius_secret || null,
      });
    },
    onSuccess: () => {
      toast("ok", "Fabricante salvo");
      setForm(null);
      invalidate();
    },
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : "Erro ao salvar"),
  });

  const remove = useMutation({
    mutationFn: (m: Manufacturer) => api.del(`/manufacturers/${m.id}`),
    onSuccess: () => {
      toast("ok", "Fabricante removido");
      invalidate();
    },
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : "Erro ao remover"),
  });

  return (
    <div>
      <PageHeader
        title="Grupo de equipamentos"
        subtitle="Fabricante / grupo: define a tradução de VSA e o segredo RADIUS padrão herdado pelos equipamentos"
        actions={<Button onClick={() => setForm({ ...empty })}>Novo grupo</Button>}
      />

      {list.isLoading ? (
        <Spinner className="h-6 w-6 text-brand-600" />
      ) : (
        <Card className="overflow-x-auto p-0">
          <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
            <thead className="bg-slate-50 dark:bg-slate-800/50">
              <tr>
                <th className="th">Identificador</th>
                <th className="th">Nome</th>
                <th className="th">Família (VSA)</th>
                <th className="th">Vendor ID</th>
                <th className="th">Segredo padrão</th>
                <th className="th">Equipamentos</th>
                <th className="th">Atualizado</th>
                <th className="th" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {list.data?.map((m) => (
                <tr key={m.id}>
                  <td className="td font-mono text-xs">{m.name}</td>
                  <td className="td font-medium">{m.display_name}</td>
                  <td className="td">
                    <Badge tone={m.vendor_kind === "generic" ? "slate" : "blue"}>
                      {m.vendor_kind}
                    </Badge>
                  </td>
                  <td className="td">{m.radius_vendor_id ?? "—"}</td>
                  <td className="td">
                    {m.has_secret ? (
                      <Badge tone="green">definido</Badge>
                    ) : (
                      <Badge tone="amber">não definido</Badge>
                    )}
                  </td>
                  <td className="td">{m.equipment_count}</td>
                  <td className="td">{fmtDate(m.updated_at)}</td>
                  <td className="td text-right">
                    <div className="flex justify-end gap-2">
                      <button
                        className="text-brand-600 hover:underline dark:text-brand-400"
                        onClick={() =>
                          setForm({
                            id: m.id,
                            name: m.name,
                            display_name: m.display_name,
                            vendor_kind: m.vendor_kind,
                            radius_vendor_id: m.radius_vendor_id?.toString() ?? "",
                            notes: m.notes ?? "",
                            radius_secret: "",
                            clear_secret: false,
                          })
                        }
                      >
                        Editar
                      </button>
                      <button
                        className="text-rose-600 hover:underline dark:text-rose-400"
                        onClick={() => {
                          if (confirm(`Remover o fabricante ${m.display_name}?`)) remove.mutate(m);
                        }}
                      >
                        Excluir
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {list.data?.length === 0 && (
                <tr>
                  <td className="td text-slate-400 dark:text-slate-500" colSpan={8}>
                    Nenhum fabricante cadastrado.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </Card>
      )}

      <Modal
        open={!!form}
        onClose={() => setForm(null)}
        title={form?.id ? "Editar fabricante" : "Novo fabricante"}
      >
        {form && (
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              save.mutate(form);
            }}
          >
            <div className="grid grid-cols-2 gap-3">
              <Field label="Identificador (slug)" hint="minúsculas, sem espaços — imutável">
                <input
                  className="input font-mono"
                  value={form.name}
                  disabled={!!form.id}
                  pattern="[a-z0-9][a-z0-9_\-]*"
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                />
              </Field>
              <Field label="Nome de exibição">
                <input
                  className="input"
                  value={form.display_name}
                  onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                  required
                />
              </Field>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Família (tradução de VSA)" hint={KIND_HINT[form.vendor_kind]}>
                <select
                  className="input"
                  value={form.vendor_kind}
                  onChange={(e) =>
                    setForm({ ...form, vendor_kind: e.target.value as VendorKind })
                  }
                >
                  {VENDOR_KINDS.map((k) => (
                    <option key={k} value={k}>
                      {k}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="RADIUS Vendor ID (opcional)">
                <input
                  className="input"
                  type="number"
                  value={form.radius_vendor_id}
                  onChange={(e) => setForm({ ...form, radius_vendor_id: e.target.value })}
                />
              </Field>
            </div>

            <Field
              label={
                form.id ? "Segredo RADIUS padrão (em branco = manter)" : "Segredo RADIUS padrão"
              }
              hint="Shared secret herdado pelos equipamentos deste fabricante que não tiverem um próprio. Guardado cifrado."
            >
              <input
                className="input font-mono"
                type="password"
                value={form.radius_secret}
                minLength={6}
                disabled={form.clear_secret}
                onChange={(e) => setForm({ ...form, radius_secret: e.target.value })}
              />
            </Field>
            {form.id && (
              <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={form.clear_secret}
                  onChange={(e) =>
                    setForm({ ...form, clear_secret: e.target.checked, radius_secret: "" })
                  }
                />
                Remover o segredo padrão deste fabricante
              </label>
            )}

            <Field label="Notas">
              <input
                className="input"
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </Field>

            <div className="flex justify-end gap-2 pt-2">
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
