import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { en } from "./locales/en";

export type Lang = "pt-BR" | "en-US";

export const LANGS: { value: Lang; label: string }[] = [
  { value: "pt-BR", label: "Português (Brasil)" },
  { value: "en-US", label: "English (US)" },
];

export const DEFAULT_LANG: Lang = "pt-BR";

const LS_KEY = "pr_lang";

// pt-BR não tem dicionário: as chaves JÁ são o texto pt-BR (identidade).
const DICT: Record<Lang, Record<string, string>> = { "pt-BR": {}, "en-US": en };

export function normalizeLang(v: string | null | undefined): Lang {
  return v === "en-US" || v === "pt-BR" ? v : DEFAULT_LANG;
}

export function readStoredLang(): Lang {
  try {
    return normalizeLang(localStorage.getItem(LS_KEY));
  } catch {
    return DEFAULT_LANG;
  }
}

interface I18nCtx {
  lang: Lang;
  /** Só troca o idioma da UI (+ localStorage). Persistir no perfil é com o auth. */
  setLang: (l: Lang) => void;
  /** Traduz `key` (que É o texto pt-BR); `{nome}` é interpolado por `vars`. */
  t: (key: string, vars?: Record<string, string | number>) => string;
}

const Ctx = createContext<I18nCtx | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(readStoredLang);

  const setLang = useCallback((l: Lang) => {
    const next = normalizeLang(l);
    setLangState(next);
    try {
      localStorage.setItem(LS_KEY, next);
    } catch {
      /* private mode / storage bloqueado */
    }
    try {
      document.documentElement.lang = next;
    } catch {
      /* SSR / ambiente sem document */
    }
  }, []);

  const t = useCallback<I18nCtx["t"]>(
    (key, vars) => {
      let s = DICT[lang][key] ?? key;
      if (vars) {
        for (const [k, v] of Object.entries(vars)) {
          s = s.split(`{${k}}`).join(String(v));
        }
      }
      return s;
    },
    [lang],
  );

  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useI18n(): I18nCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useI18n fora do I18nProvider");
  return ctx;
}

/** Atalho: só a função de tradução. */
export function useT(): I18nCtx["t"] {
  return useI18n().t;
}
