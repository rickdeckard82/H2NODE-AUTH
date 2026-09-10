import type { ReactNode } from "react";
import { Card } from "../../components/ui";
import { useT } from "../../lib/i18n";

export interface ReportFilterState {
  username: string;
  nasIp: string;
  since: string;
  until: string;
}

export const emptyFilters: ReportFilterState = { username: "", nasIp: "", since: "", until: "" };

/** `datetime-local` (fuso do navegador) → ISO UTC para a query. */
export function toIso(local: string): string | undefined {
  if (!local) return undefined;
  const d = new Date(local);
  return Number.isNaN(d.getTime()) ? undefined : d.toISOString();
}

export function ReportFilters({
  value,
  onChange,
  showNas = false,
  right,
}: {
  value: ReportFilterState;
  onChange: (next: ReportFilterState) => void;
  showNas?: boolean;
  right?: ReactNode;
}) {
  const set = (patch: Partial<ReportFilterState>) => onChange({ ...value, ...patch });
  const t = useT();

  return (
    <Card className="mb-3 flex flex-wrap items-end gap-2">
      <label className="block">
        <span className="label">{t("Usuário")}</span>
        <input
          className="input max-w-[180px]"
          placeholder={t("Usuário")}
          value={value.username}
          onChange={(e) => set({ username: e.target.value })}
        />
      </label>
      {showNas && (
        <label className="block">
          <span className="label">{t("IP do NAS")}</span>
          <input
            className="input max-w-[160px]"
            placeholder="10.0.0.1"
            value={value.nasIp}
            onChange={(e) => set({ nasIp: e.target.value })}
          />
        </label>
      )}
      <label className="block">
        <span className="label">{t("De")}</span>
        <input
          type="datetime-local"
          className="input max-w-[210px]"
          value={value.since}
          onChange={(e) => set({ since: e.target.value })}
        />
      </label>
      <label className="block">
        <span className="label">{t("Até")}</span>
        <input
          type="datetime-local"
          className="input max-w-[210px]"
          value={value.until}
          onChange={(e) => set({ until: e.target.value })}
        />
      </label>
      {right && <div className="ml-auto flex items-end gap-2">{right}</div>}
    </Card>
  );
}
