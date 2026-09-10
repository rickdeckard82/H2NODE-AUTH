import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { api, ApiError } from "../lib/api";
import { useT } from "../lib/i18n";
import { Button, Field, Modal, useToast } from "./ui";

export function ChangePasswordModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const toast = useToast();
  const t = useT();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setCurrent("");
    setNext("");
    setConfirm("");
    setError(null);
  }

  const save = useMutation({
    mutationFn: () => api.patch("/auth/me/password", { current_password: current, new_password: next }),
    onSuccess: () => {
      toast("ok", t("Senha alterada"));
      reset();
      onClose();
    },
    onError: (e) => setError(e instanceof ApiError ? e.detail : t("Erro ao alterar a senha")),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (next !== confirm) {
      setError(t("As senhas não coincidem"));
      return;
    }
    save.mutate();
  }

  return (
    <Modal
      open={open}
      onClose={() => {
        reset();
        onClose();
      }}
      title={t("Alterar senha")}
    >
      <form className="space-y-3" onSubmit={onSubmit}>
        <Field label={t("Senha atual")}>
          <input
            className="input"
            type="password"
            autoComplete="current-password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            required
            autoFocus
          />
        </Field>
        <Field label={t("Nova senha")} hint={t("Mínimo 10 caracteres.")}>
          <input
            className="input"
            type="password"
            minLength={10}
            autoComplete="new-password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            required
          />
        </Field>
        <Field label={t("Confirmar nova senha")} error={error ?? undefined}>
          <input
            className="input"
            type="password"
            minLength={10}
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
          />
        </Field>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            {t("Cancelar")}
          </Button>
          <Button type="submit" loading={save.isPending}>
            {t("Salvar")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
