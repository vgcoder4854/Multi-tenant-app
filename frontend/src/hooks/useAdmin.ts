import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi, auditApi, dashboardApi } from "@/api/misc";
import type { AuditFilters, DashboardFilters } from "@/api/misc";
import { orgsApi, platformApi } from "@/api/orgs";
import { useAuth } from "@/lib/auth";
import type { MemberRole } from "@/types";

function useOrgId(): string {
  return useAuth().activeOrgId ?? "none";
}

export function useDashboardSummary(filters: DashboardFilters = {}) {
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["dashboard", orgId, filters],
    queryFn: () => dashboardApi.summary(filters),
  });
}

export function useAuditLogs(filters: AuditFilters = {}) {
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["audit", orgId, filters],
    queryFn: () => auditApi.list(filters),
    placeholderData: (prev) => prev,
  });
}

export function useMembers() {
  const orgId = useOrgId();
  return useQuery({ queryKey: ["members", orgId], queryFn: orgsApi.listMembers });
}

export function useInvitations() {
  const orgId = useOrgId();
  return useQuery({ queryKey: ["invitations", orgId], queryFn: orgsApi.listInvitations });
}

export function useInviteMember() {
  const qc = useQueryClient();
  const orgId = useOrgId();
  return useMutation({
    mutationFn: (body: { email: string; role: MemberRole }) => orgsApi.createInvitation(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["invitations", orgId] }),
  });
}

export function useRevokeInvitation() {
  const qc = useQueryClient();
  const orgId = useOrgId();
  return useMutation({
    mutationFn: (id: string) => orgsApi.revokeInvitation(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["invitations", orgId] }),
  });
}

export function useChangeMemberRole() {
  const qc = useQueryClient();
  const orgId = useOrgId();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: MemberRole }) =>
      orgsApi.changeRole(userId, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["members", orgId] }),
  });
}

export function useRemoveMember() {
  const qc = useQueryClient();
  const orgId = useOrgId();
  return useMutation({
    mutationFn: (userId: string) => orgsApi.removeMember(userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["members", orgId] }),
  });
}

export function useRunDueScan() {
  const qc = useQueryClient();
  const orgId = useOrgId();
  return useMutation({
    mutationFn: adminApi.runDueScan,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications", orgId] }),
  });
}

export function usePlatformOrganizations(params: {
  status?: string;
  name?: string;
  page?: number;
  page_size?: number;
}) {
  return useQuery({
    queryKey: ["platform-orgs", params],
    queryFn: () => platformApi.listOrganizations(params),
  });
}

export function useSetOrgStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: "active" | "suspended" }) =>
      platformApi.setStatus(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["platform-orgs"] }),
  });
}

export function usePlatformStats() {
  return useQuery({ queryKey: ["platform-stats"], queryFn: platformApi.stats });
}
