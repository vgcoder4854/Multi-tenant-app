import { api } from "./client";
import type { Me, TokenResponse, User } from "@/types";

export const authApi = {
  register: (body: { email: string; password: string; full_name: string }) =>
    api.post<User>("/auth/register", body),
  login: (body: { email: string; password: string }) =>
    api.post<TokenResponse>("/auth/login", body),
  me: () => api.get<Me>("/auth/me"),
  switchOrganization: (orgId: string) =>
    api.post<TokenResponse>("/auth/switch-organization", { org_id: orgId }),
};
