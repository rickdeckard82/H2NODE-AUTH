import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { RevealSecretButton } from "../../components/RevealSecret";
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
import type { AaaProtocol, Equipment, Manufacturer } from "../../lib/types";

interface FormState {
  id?: number;
  name: string;
  mgmt_ip: string;
  manufacturer_id: number | "";
  model: string;
  site: string;
  shortname: string;
  coa_port: number;
  status: Equipment["status"];
  description: string;
  radius_secret: string;
  inherit_secret: boolean;
  aaa_protocol: "" | AaaProtocol;
  tacacs_key: string;
  inherit_tacacs_key: boolean;
  radius_require_message_authenticator: boolean;
}

const empty: FormState = {
  name: "",
  mgmt_ip: "",
  manufacturer_id: "",
  model: "",
  site: "",
  shortname: "",
  coa_port: 3799,
  status: "active",
  description: "",
  radius_secret: "",
  inherit_secret: false,
  aaa_protocol: "",
  tacacs_key: "",
  inherit_tacacs_key: false,
  radius_require_message_authenticator: true,
};

const STATUS_TONE: Record<Equipment["status"], "green" | "amber" | "red"> = {
  active: "green",
  maintenance: "amber",
  disabled: "red",
};

export default function EquipmentPage() {
  const { can } = useAuth();
  const canDelete = can("admin");
  const qc = useQueryClient();
  const toast = useToast();
  const writable = can("operator");

  const [manufacturerFilter, setManufacturerFilter] = useState<number | "all">("all");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [form, setForm] = useState<FormState | null>(null);

  const manufacturers = useQuery({
    queryKey: ["manufacturers"],
    queryFn: () => api.get<Manufacturer[]>("/manufacturers"),
  });

  const list = useQuery({
    queryKey: ["equipment", manufacturerFilter, q, page],
    queryFn: () =>
      api.get<Page<Equipment>>("/equipment", {
        manufacturer_id: manufacturerFilter === "all" ? undefined : manufacturerFilter,
        q,
        page,
        page_size: 20,
      }),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["equipment"] });
    qc.invalidateQueries({ queryKey: ["manufacturers"] });
  };

  const save = useMutation({
    mutationFn: (f: FormState) => {
      const body: Record<string, unknown> = {
        name: f.name,
        mgmt_ip: f.mgmt_ip,
        manufacturer_id: f.manufacturer_id,
        model: f.model || null,
        site: f.site || null,
        shortname: f.shortname,
        coa_port: f.coa_port,
        status: f.status,
        description: f.description || null,
        radius_require_message_authenticator: f.radius_require_message_authenticator,
      };
      if (f.id && f.inherit_secret) body.inherit_secret = true;
      else if (f.radius_secret) body.radius_secret = f.radius_secret;
      if (f.aaa_protocol) body.aaa_protocol = f.aaa_protocol;
      else if (f.id) body.inherit_protocol = true;
      if (f.id && f.inherit_tacacs_key) body.inherit_tacacs_key = true;
      else if (f.tacacs_key) body.tacacs_key = f.tacacs_key;
      if (f.id) return api.patch(`/equipment/${f.id}`, body);
      return api.post("/equipment", body);
    },
    onSuccess: () => {
      toast("ok", "Equipamento salvo");
      setForm(null);
      invalidate();
    },
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : "Erro ao salvar"),
  });

  const remove = useMutation({
    mutationFn: (eq: Equipment) => api.del(`/equipment/${eq.id}`),
    onSuccess: () => {
      toast("ok", "Equipamento removido");
      invalidate();
    },
    onError: (e) => toast("err", e instanceof ApiError ? e.detail : "Erro ao remover"),
  });

  const orderedManufacturers = [...(manufacturers.data ?? [])].sort((a, b) =>
    a.display_name.localeCompare(b.display_name),
  );

  const selectedManufacturer =
    form && form.manufacturer_id !== ""
      ? manufacturers.data?.find((m) => m.id === form.manufacturer_id)
      : undefined;
  // protocolo efetivo já resolvida a herança do grupo
  const effProto: AaaProtocol =
    (form?.aaa_protocol as AaaProtocol) || selectedManufacturer?.aaa_protocol || "radius";
  const secretRequired =
    !!form && !form.id && !form.inherit_secret && !selectedManufacturer?.has_secret &&
    effProto === "radius";
  const tacacsKeyRequired =
    !!form && !form.id && !form.inherit_tacacs_key && !selectedManufacturer?.has_tacacs_key &&
    effProto === "tacacs";

  return (
    <div>
      <PageHeader
        title="Equipamentos"
        subtitle="Clientes RADIUS (NAS)"
        actions={
          writable && (
            <Button
              onClick={() =>
                setForm({
                  ...empty,
                  manufacturer_id:
                    typeof manufacturerFilter === "number" ? manufacturerFilter : "",
                })
              }
            >
              Novo equipamento
            </Button>
          )
        }
      />

      <Card className="mb-3 flex flex-wrap gap-2">
        <input
          className="input max-w-xs"
          placeholder="Buscar por nome, IP, site…"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setPage(1);
          }}
        />
        <select
          className="input max-w-[220px]"
          value={manufacturerFilter}
          onChange={(e) => {
            const v = e.target.value;
            setManufacturerFilter(v === "all" ? "all" : Number(v));
            setPage(1);
          }}
        >
          <option value="all">Todos os fabricantes</option>
          {orderedManufacturers.map((m) => (
            <option key={m.id} value={m.id}>
              {m.display_name}
            </option>
          ))}
        </select>
      </Card>

      <Card className="overflow-x-auto p-0">
        <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
          <thead className="bg-slate-50 dark:bg-slate-800/50">
            <tr>
              <th className="th">Nome</th>
              <th className="th">IP de gerência</th>
              <th className="th">Fabricante</th>
              <th className="th">AAA</th>
              <th className="th">Segredo</th>
              <th className="th">Site</th>
              <th className="th">Estado</th>
              <th className="th">Atualizado</th>
              <th className="th" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {list.isLoading && (
              <tr>
                <td className="td" colSpan={9}>
                  <Spinner className="h-5 w-5 text-brand-600" />
                </td>
              </tr>
            )}
            {list.data?.items.map((eq) => (
              <tr key={eq.id}>
                <td className="td font-medium">{eq.name}</td>
                <td className="td font-mono text-xs">{eq.mgmt_ip}</td>
                <td className="td">
                  <Badge tone="blue">{eq.manufacturer_display}</Badge>
                </td>
                <td className="td">
                  <div className="flex flex-wrap gap-1">
                    <Badge tone={eq.effective_protocol === "tacacs" ? "amber" : "slate"}>
                      {eq.effective_protocol}
                    </Badge>
                    {eq.effective_protocol === "radius" &&
                      !eq.radius_require_message_authenticator && (
                        <Badge tone="amber">sem Message-Authenticator</Badge>
                      )}
                  </div>
                </td>
                <td className="td">
                  {eq.effective_protocol === "tacacs" ? (
                    <>
                      {eq.tacacs_key_source === "equipment" && (
                        <Badge tone="slate">chave própria</Badge>
                      )}
                      {eq.tacacs_key_source === "manufacturer" && (
                        <Badge tone="green">chave herdada do grupo</Badge>
                      )}
                      {eq.tacacs_key_source === "none" && (
                        <Badge tone="red">sem chave TACACS+</Badge>
                      )}
                    </>
                  ) : (
                    <>
                      {eq.secret_source === "equipment" && <Badge tone="slate">próprio</Badge>}
                      {eq.secret_source === "manufacturer" && (
                        <Badge tone="green">herdado do fabricante</Badge>
                      )}
                      {eq.secret_source === "none" && <Badge tone="red">sem segredo</Badge>}
                    </>
                  )}
                </td>
                <td className="td">{eq.site || "—"}</td>
                <td className="td">
                  <Badge tone={STATUS_TONE[eq.status]}>{eq.status}</Badge>
                </td>
                <td className="td">{fmtDate(eq.updated_at)}</td>
                <td className="td text-right">
                  {writable && (
                    <div className="flex justify-end gap-2">
                      {eq.effective_protocol === "radius" && eq.secret_source !== "none" && (
                        <RevealSecretButton
                          title={`Segredo RADIUS — ${eq.name}`}
                          hint="Esta consulta fica registrada na auditoria."
                          load={() => api.get(`/equipment/${eq.id}/secret`)}
                        />
                      )}
                      <button
                        className="text-brand-600 hover:underline dark:text-brand-400"
                        onClick={() =>
                          setForm({
                            id: eq.id,
                            name: eq.name,
                            mgmt_ip: eq.mgmt_ip,
                            manufacturer_id: eq.manufacturer_id,
                            model: eq.model ?? "",
                            site: eq.site ?? "",
                            shortname: eq.shortname,
                            coa_port: eq.coa_port,
                            status: eq.status,
                            description: eq.description ?? "",
                            radius_secret: "",
                            inherit_secret: false,
                            aaa_protocol: eq.aaa_protocol ?? "",
                            tacacs_key: "",
                            inherit_tacacs_key: false,
                            radius_require_message_authenticator:
                              eq.radius_require_message_authenticator,
                          })
                        }
                      >
                        Editar
                      </button>
                      {canDelete && (
                        <button
                          className="text-rose-600 hover:underline dark:text-rose-400"
                          onClick={() => {
                            if (confirm(`Remover ${eq.name}?`)) remove.mutate(eq);
                          }}
                        >
                          Excluir
                        </button>
                      )}
                    </div>
                  )}
                </td>
              </tr>
            ))}
            {list.data?.items.length === 0 && (
              <tr>
                <td className="td text-slate-400 dark:text-slate-500" colSpan={9}>
                  Nenhum equipamento neste grupo.
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
        title={form?.id ? "Editar equipamento" : "Novo equipamento"}
        wide
      >
        {form && (
          <form
            className="grid grid-cols-2 gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              save.mutate(form);
            }}
          >
            <Field label="Nome">
              <input
                className="input"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
              />
            </Field>
            <Field label="IP de gerência" hint="Deve bater com o NAS-IP-Address do request">
              <input
                className="input font-mono"
                value={form.mgmt_ip}
                onChange={(e) => setForm({ ...form, mgmt_ip: e.target.value })}
                required
              />
            </Field>
            <Field
              label="Fabricante"
              hint={
                selectedManufacturer
                  ? selectedManufacturer.has_secret
                    ? "tem segredo RADIUS padrão"
                    : "sem segredo padrão — informe um abaixo"
                  : undefined
              }
            >
              <select
                className="input"
                value={form.manufacturer_id}
                onChange={(e) => setForm({ ...form, manufacturer_id: Number(e.target.value) })}
                required
              >
                <option value="" disabled>
                  Selecione…
                </option>
                {orderedManufacturers.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.display_name}
                    {m.has_secret ? "  ·  segredo padrão" : ""}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Shortname (identificador RADIUS)">
              <input
                className="input"
                value={form.shortname}
                pattern="[a-zA-Z0-9._\-]+"
                onChange={(e) => setForm({ ...form, shortname: e.target.value })}
                required
              />
            </Field>
            <Field label="Modelo">
              <input
                className="input"
                value={form.model}
                onChange={(e) => setForm({ ...form, model: e.target.value })}
              />
            </Field>
            <Field label="Site / localização">
              <input
                className="input"
                value={form.site}
                onChange={(e) => setForm({ ...form, site: e.target.value })}
              />
            </Field>
            <Field label="Porta CoA">
              <input
                className="input"
                type="number"
                value={form.coa_port}
                onChange={(e) => setForm({ ...form, coa_port: Number(e.target.value) })}
              />
            </Field>
            <Field label="Estado">
              <select
                className="input"
                value={form.status}
                onChange={(e) =>
                  setForm({ ...form, status: e.target.value as Equipment["status"] })
                }
              >
                <option value="active">active</option>
                <option value="maintenance">maintenance</option>
                <option value="disabled">disabled</option>
              </select>
            </Field>
            <Field
              label="Protocolo AAA"
              hint={
                form.aaa_protocol
                  ? undefined
                  : `herda do grupo (${selectedManufacturer?.aaa_protocol ?? "radius"})`
              }
            >
              <select
                className="input"
                value={form.aaa_protocol}
                onChange={(e) =>
                  setForm({ ...form, aaa_protocol: e.target.value as "" | AaaProtocol })
                }
              >
                <option value="">herdar do grupo</option>
                <option value="radius">radius</option>
                <option value="tacacs">tacacs</option>
              </select>
            </Field>
            <div className="col-span-2">
              <Field
                label="Segredo RADIUS"
                hint={
                  form.inherit_secret
                    ? "vai herdar o segredo padrão do fabricante"
                    : selectedManufacturer && !selectedManufacturer.has_secret
                      ? "o fabricante não tem segredo padrão — este campo é obrigatório"
                      : "em branco = herda o segredo padrão do fabricante. Guardado cifrado (Fernet)."
                }
              >
                <input
                  className="input font-mono"
                  type="password"
                  value={form.radius_secret}
                  minLength={6}
                  disabled={form.inherit_secret}
                  onChange={(e) => setForm({ ...form, radius_secret: e.target.value })}
                  required={secretRequired}
                />
              </Field>
              {form.id && (
                <label className="mt-2 flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={form.inherit_secret}
                    onChange={(e) =>
                      setForm({ ...form, inherit_secret: e.target.checked, radius_secret: "" })
                    }
                  />
                  Voltar a herdar o segredo do fabricante
                </label>
              )}
            </div>
            {effProto === "radius" && (
              <div className="col-span-2">
                <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={form.radius_require_message_authenticator}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        radius_require_message_authenticator: e.target.checked,
                      })
                    }
                  />
                  Exigir Message-Authenticator (proteção contra BlastRADIUS)
                </label>
                {!form.radius_require_message_authenticator && (
                  <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">
                    Desmarque só para equipamentos com firmware antigo que ainda não enviam esse
                    atributo (ex.: RouterOS anterior aos patches de 2024) — reduz a proteção
                    contra o ataque BlastRADIUS só para este NAS. Prefira atualizar o firmware.
                  </p>
                )}
              </div>
            )}
            {effProto === "tacacs" && (
              <div className="col-span-2">
                <Field
                  label="Chave TACACS+"
                  hint={
                    form.inherit_tacacs_key
                      ? "vai herdar a chave padrão do grupo"
                      : "em branco = herda a chave padrão do grupo. Guardada cifrada (Fernet)."
                  }
                >
                  <input
                    className="input font-mono"
                    type="password"
                    value={form.tacacs_key}
                    minLength={6}
                    disabled={form.inherit_tacacs_key}
                    onChange={(e) => setForm({ ...form, tacacs_key: e.target.value })}
                    required={tacacsKeyRequired}
                  />
                </Field>
                {form.id && (
                  <label className="mt-2 flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                    <input
                      type="checkbox"
                      checked={form.inherit_tacacs_key}
                      onChange={(e) =>
                        setForm({ ...form, inherit_tacacs_key: e.target.checked, tacacs_key: "" })
                      }
                    />
                    Voltar a herdar a chave do grupo
                  </label>
                )}
              </div>
            )}
            <div className="col-span-2">
              <Field label="Descrição">
                <input
                  className="input"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                />
              </Field>
            </div>
            <div className="col-span-2 flex justify-end gap-2 pt-2">
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
