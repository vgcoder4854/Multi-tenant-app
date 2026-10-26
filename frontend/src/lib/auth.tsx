import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { authApi } from "@/api/auth";
import { setAccessToken, setUnauthorizedHandler } from "@/api/client";
import type { Me, MemberRole } from "@/types";

export interface AuthState {
  user: Me | null;
  activeOrgId: string | null;
  role: MemberRole | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
  switchOrganization: (orgId: string) => Promise<void>;
  refreshUser: () => Promise<void>;
  hasRole: (...roles: MemberRole[]) => boolean;
}

// Exported so tests can inject a fake auth state without the real provider.
export const AuthContext = createContext<AuthState | null>(null);

const ORG_KEY = "mta_org";

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<Me | null>(null);
  const [activeOrgId, setActiveOrgId] = useState<string | null>(sessionStorage.getItem(ORG_KEY));
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    setAccessToken(null);
    setUser(null);
    setActiveOrgId(null);
    sessionStorage.removeItem(ORG_KEY);
    queryClient.clear();
  }, [queryClient]);

  const refreshUser = useCallback(async () => {
    const me = await authApi.me();
    setUser(me);
  }, []);

  // Restore session on first load and register the global 401 handler.
  useEffect(() => {
    setUnauthorizedHandler(() => logout());
    (async () => {
      try {
        if (sessionStorage.getItem("mta_token")) await refreshUser();
      } catch {
        logout();
      } finally {
        setLoading(false);
      }
    })();
    return () => setUnauthorizedHandler(null);
  }, [refreshUser, logout]);

  const login = useCallback(
    async (email: string, password: string) => {
      const token = await authApi.login({ email, password });
      setAccessToken(token.access_token);
      await refreshUser();
    },
    [refreshUser],
  );

  const register = useCallback(
    async (email: string, password: string, fullName: string) => {
      await authApi.register({ email, password, full_name: fullName });
      await login(email, password);
    },
    [login],
  );

  const switchOrganization = useCallback(
    async (orgId: string) => {
      const token = await authApi.switchOrganization(orgId);
      setAccessToken(token.access_token);
      setActiveOrgId(orgId);
      sessionStorage.setItem(ORG_KEY, orgId);
      queryClient.clear();
    },
    [queryClient],
  );

  const role = useMemo<MemberRole | null>(() => {
    if (!user || !activeOrgId) return null;
    return user.memberships.find((m) => m.org_id === activeOrgId)?.role ?? null;
  }, [user, activeOrgId]);

  const hasRole = useCallback(
    (...roles: MemberRole[]) => (role ? roles.includes(role) : false),
    [role],
  );

  const value: AuthState = {
    user,
    activeOrgId,
    role,
    isAuthenticated: Boolean(user),
    loading,
    login,
    register,
    logout,
    switchOrganization,
    refreshUser,
    hasRole,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
