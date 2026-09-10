import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api } from "./api";
import { normalizeLang, useI18n, type Lang } from "./i18n";

export type Role = "superadmin" | "admin" | "operator" | "auditor";

export interface Me {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  timezone: string;
  language: Lang;
  mfa_enabled: boolean;
  mfa_recovery_codes_remaining: number;
  last_login_at: string | null;
}

export interface LoginResult {
  mfaRequired: boolean;
  mfaToken?: string;
}

interface SessionResponse {
  user: Me | null;
  csrf_token: string | null;
  mfa_required: boolean;
  mfa_token: string | null;
}

interface AuthCtx {
  user: Me | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<LoginResult>;
  verifyMfa: (mfaToken: string, code: string, rememberDevice?: boolean) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  /** Persiste o idioma no perfil do usuário e aplica na UI. */
  setLanguage: (lang: Lang) => Promise<void>;
  /** true se o papel do usuário é >= ao menor papel informado (hierárquico). */
  can: (...roles: Role[]) => boolean;
}

const Ctx = createContext<AuthCtx | null>(null);

const RANK: Record<Role, number> = { auditor: 1, operator: 2, admin: 3, superadmin: 4 };

export function AuthProvider({ children }: { children: ReactNode }) {
  const { setLang } = useI18n();
  const [user, setUser] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<Me>("/auth/me")
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  // idioma da UI segue o do usuário logado
  useEffect(() => {
    if (user?.language) setLang(normalizeLang(user.language));
  }, [user?.language, setLang]);

  const login = useCallback(async (username: string, password: string): Promise<LoginResult> => {
    const res = await api.post<SessionResponse>("/auth/login", { username, password });
    if (res.mfa_required) return { mfaRequired: true, mfaToken: res.mfa_token ?? undefined };
    setUser(res.user);
    return { mfaRequired: false };
  }, []);

  const verifyMfa = useCallback(
    async (mfaToken: string, code: string, rememberDevice = false) => {
      const res = await api.post<SessionResponse>("/auth/mfa/verify", {
        mfa_token: mfaToken,
        code,
        remember_device: rememberDevice,
      });
      setUser(res.user);
    },
    [],
  );

  const logout = useCallback(async () => {
    await api.post("/auth/logout").catch(() => undefined);
    setUser(null);
  }, []);

  const refresh = useCallback(async () => {
    const me = await api.get<Me>("/auth/me").catch(() => null);
    setUser(me);
  }, []);

  const setLanguage = useCallback(
    async (lang: Lang) => {
      setLang(lang); // aplica já
      const me = await api.patch<Me>("/auth/me", { language: lang }).catch(() => null);
      if (me) setUser(me);
    },
    [setLang],
  );

  const can = useCallback(
    (...roles: Role[]) => {
      if (!user) return false;
      if (user.role === "superadmin") return true;
      const min = Math.min(...roles.map((r) => RANK[r]));
      return RANK[user.role] >= min;
    },
    [user],
  );

  const value = useMemo(
    () => ({ user, loading, login, verifyMfa, logout, refresh, setLanguage, can }),
    [user, loading, login, verifyMfa, logout, refresh, setLanguage, can],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth fora do AuthProvider");
  return ctx;
}
