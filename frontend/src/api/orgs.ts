import { api } from "./client";
import type {
  Invitation,
  InvitationCreated,
  Member,
  MemberRole,
  MyOrganization,
  Organization,
  Page,
  User,
} from "@/types";

export const orgsApi = {
  create: (body: { name: string; slug?: string }) => api.post<Organization>("/organizations", body),
  mine: () => api.get<MyOrganization[]>("/organizations/mine"),

  listInvitations: () => api.get<Invitation[]>("/org/invitations"),
  createInvitation: (body: { email: string; role: MemberRole }) =>
    api.post<InvitationCreated>("/org/invitations", body),
  revokeInvitation: (id: string) => api.del<void>(`/org/invitations/${id}`),
  acceptInvitation: (token: string) => api.post<Organization>("/invitations/accept", { token }),

  listMembers: () => api.get<Member[]>("/org/members"),
  changeRole: (userId: string, role: MemberRole) =>
    api.patch<Member>(`/org/members/${userId}/role`, { role }),
  removeMember: (userId: string) => api.del<void>(`/org/members/${userId}`),
};

export const platformApi = {
  listOrganizations: (params: { status?: string; name?: string; page?: number; page_size?: number }) =>
    api.get<Page<Organization>>("/platform/organizations", params),
  setStatus: (id: string, status: "active" | "suspended") =>
    api.patch<Organization>(`/platform/organizations/${id}/status`, { status }),
  stats: () => api.get<Record<string, number>>("/platform/stats"),
};

export type { User };
