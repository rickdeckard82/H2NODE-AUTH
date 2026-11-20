import { useState } from "react";
import { Link } from "react-router-dom";
import { APP_VERSION } from "../lib/changelog";
import { useT } from "../lib/i18n";
import { ChangelogModal } from "./ChangelogModal";

/** Rodapé com copyright, link para as notas de versão e para a Política de Privacidade. */
export function AppFooter({ className = "" }: { className?: string }) {
  const [showChangelog, setShowChangelog] = useState(false);
  const t = useT();
  return (
    <div className={`text-xs leading-relaxed text-slate-400 dark:text-slate-500 ${className}`}>
      <div>
        © {new Date().getFullYear()} H2NODE Auth{" "}
        <button
          type="button"
          onClick={() => setShowChangelog(true)}
          className="font-medium text-brand-600 hover:underline dark:text-brand-400"
        >
          v{APP_VERSION}
        </button>
      </div>
      <Link to="/privacidade" className="hover:underline">
        {t("Política de Privacidade")}
      </Link>
      <ChangelogModal open={showChangelog} onClose={() => setShowChangelog(false)} />
    </div>
  );
}
