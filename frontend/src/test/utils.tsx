import type { ReactElement, ReactNode } from "react";
import { render } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { AuthContext, type AuthState } from "@/lib/auth";
import { ToastProvider } from "@/components/ui";
import type { Me, MemberRole } from "@/types";

export function makeUser(role: MemberRole = "employee", overrides: Partial<Me> = {}): Me {
  return {
    id: "user-1",
    email: "user@example.com",
    full_name: "Test User",
    is_platform_admin: false,
    is_active: true,
    created_at: new Date().toISOString(),
    memberships: [
      {
        org_id: "org-1",
        org_name: "Test Org",
        org_slug: "test-org",
        role,
        status: "active",
      },
    ],
    ...overrides,
  };
}

export function makeAuth(overrides: Partial<AuthState> = {}): AuthState {
  const role = overrides.role ?? "employee";
  const user = overrides.user ?? makeUser(role);
  return {
    user,
    activeOrgId: "org-1",
    role,
    isAuthenticated: true,
    loading: false,
    login: async () => {},
    register: async () => {},
    logout: () => {},
    switchOrganization: async () => {},
    refreshUser: async () => {},
    hasRole: (...roles: MemberRole[]) => roles.includes(role),
    ...overrides,
  };
}

export function renderWithProviders(
  ui: ReactElement,
  options: { route?: string; auth?: AuthState; wrap?: (node: ReactNode) => ReactNode } = {},
) {
  const { route = "/", auth = makeAuth() } = options;
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const tree = (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <AuthContext.Provider value={auth}>
          <ToastProvider>{options.wrap ? options.wrap(ui) : ui}</ToastProvider>
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>
  );
  return { ...render(tree), queryClient };
}
