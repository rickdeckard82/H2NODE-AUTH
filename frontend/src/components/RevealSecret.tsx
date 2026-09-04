import { useState } from "react";
import { ApiError } from "../lib/api";
import { Button, Modal, Spinner, useToast } from "./ui";

export function RevealSecretButton({
  title,
  hint,
  load,
}: {
  title: string;
  hint?: string;
  load: () => Promise<{ radius_secret: string | null }>;
}) {
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [secret, setSecret] = useState<string | null | undefined>(undefined);

  async function reveal() {
    setOpen(true);
    setLoading(true);
    setSecret(undefined);
    try {
      const res = await load();
      setSecret(res.radius_secret);
    } catch (e) {
      setOpen(false);
      toast("err", e instanceof ApiError ? e.detail : "Erro ao consultar o segredo");
    } finally {
      setLoading(false);
    }
  }

  async function copy() {
    if (!secret) return;
    await navigator.clipboard.writeText(secret);
    toast("ok", "Copiado");
  }

  return (
    <>
      <button
        type="button"
        className="text-brand-600 hover:underline dark:text-brand-400"
        onClick={reveal}
      >
        Ver senha
      </button>
      <Modal open={open} onClose={() => setOpen(false)} title={title}>
        {loading ? (
          <Spinner className="h-6 w-6 text-brand-600" />
        ) : secret ? (
          <div className="space-y-3">
            <div className="break-all rounded-lg border border-slate-200 bg-slate-50 p-3 font-mono text-sm dark:border-slate-800 dark:bg-slate-800/50">
              {secret}
            </div>
            {hint && <p className="text-xs text-slate-400 dark:text-slate-500">{hint}</p>}
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setOpen(false)}>
                Fechar
              </Button>
              <Button onClick={copy}>Copiar</Button>
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-500 dark:text-slate-400">Nenhum segredo definido.</p>
        )}
      </Modal>
    </>
  );
}
