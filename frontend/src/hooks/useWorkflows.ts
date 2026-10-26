import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { approvalsApi, workflowsApi } from "@/api/workflows";
import { useAuth } from "@/lib/auth";
import type { DecisionType } from "@/types";

function useOrgId(): string {
  return useAuth().activeOrgId ?? "none";
}

export function useWorkflowTemplates() {
  const orgId = useOrgId();
  return useQuery({ queryKey: ["templates", orgId], queryFn: workflowsApi.list });
}

export function useCreateTemplate() {
  const qc = useQueryClient();
  const orgId = useOrgId();
  return useMutation({
    mutationFn: workflowsApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["templates", orgId] }),
  });
}

export function useDeactivateTemplate() {
  const qc = useQueryClient();
  const orgId = useOrgId();
  return useMutation({
    mutationFn: (id: string) => workflowsApi.deactivate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["templates", orgId] }),
  });
}

export function useMyRequests() {
  const orgId = useOrgId();
  return useQuery({ queryKey: ["requests", "mine", orgId], queryFn: approvalsApi.mine });
}

export function usePendingForMe() {
  const orgId = useOrgId();
  return useQuery({ queryKey: ["requests", "pending", orgId], queryFn: approvalsApi.pendingForMe });
}

export function useApprovalRequest(id: string | undefined) {
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["request", orgId, id],
    queryFn: () => approvalsApi.get(id as string),
    enabled: Boolean(id),
  });
}

function invalidateRequests(qc: ReturnType<typeof useQueryClient>, orgId: string) {
  qc.invalidateQueries({ queryKey: ["requests", orgId] });
  qc.invalidateQueries({ queryKey: ["requests"] });
  qc.invalidateQueries({ queryKey: ["request", orgId] });
  qc.invalidateQueries({ queryKey: ["dashboard", orgId] });
  qc.invalidateQueries({ queryKey: ["notifications", orgId] });
}

export function useSubmitRequest() {
  const qc = useQueryClient();
  const orgId = useOrgId();
  return useMutation({
    mutationFn: approvalsApi.submit,
    onSuccess: () => invalidateRequests(qc, orgId),
  });
}

export function useDecideRequest(id: string) {
  const qc = useQueryClient();
  const orgId = useOrgId();
  return useMutation({
    mutationFn: (body: { decision: DecisionType; comment?: string }) => approvalsApi.decide(id, body),
    onSuccess: () => invalidateRequests(qc, orgId),
  });
}

export function useCancelRequest() {
  const qc = useQueryClient();
  const orgId = useOrgId();
  return useMutation({
    mutationFn: (id: string) => approvalsApi.cancel(id),
    onSuccess: () => invalidateRequests(qc, orgId),
  });
}
