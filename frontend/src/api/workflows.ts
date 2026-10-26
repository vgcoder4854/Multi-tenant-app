import { api } from "./client";
import type {
  ApprovalRequest,
  ApprovalRequestDetail,
  ApproverType,
  DecisionType,
  MemberRole,
  WorkflowTemplate,
} from "@/types";

export interface StepInput {
  name: string;
  approver_type: ApproverType;
  approver_role?: MemberRole | null;
  approver_user_id?: string | null;
}

export const workflowsApi = {
  list: () => api.get<WorkflowTemplate[]>("/workflow-templates"),
  get: (id: string) => api.get<WorkflowTemplate>(`/workflow-templates/${id}`),
  create: (body: { name: string; description?: string; steps: StepInput[] }) =>
    api.post<WorkflowTemplate>("/workflow-templates", body),
  update: (
    id: string,
    body: { name?: string; description?: string; is_active?: boolean; steps?: StepInput[] },
  ) => api.patch<WorkflowTemplate>(`/workflow-templates/${id}`, body),
  deactivate: (id: string) => api.post<WorkflowTemplate>(`/workflow-templates/${id}/deactivate`),
};

export const approvalsApi = {
  submit: (body: { template_id: string; title: string; details?: Record<string, unknown> }) =>
    api.post<ApprovalRequest>("/approval-requests", body),
  mine: () => api.get<ApprovalRequest[]>("/approval-requests/mine"),
  pendingForMe: () => api.get<ApprovalRequest[]>("/approval-requests/pending-for-me"),
  get: (id: string) => api.get<ApprovalRequestDetail>(`/approval-requests/${id}`),
  decide: (id: string, body: { decision: DecisionType; comment?: string }) =>
    api.post<ApprovalRequest>(`/approval-requests/${id}/decision`, body),
  cancel: (id: string) => api.post<ApprovalRequest>(`/approval-requests/${id}/cancel`),
};
