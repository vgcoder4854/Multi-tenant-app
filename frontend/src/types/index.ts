// Shared TypeScript types mirroring the backend Pydantic schemas exactly.

export type MemberRole = "org_admin" | "manager" | "employee";
export type MemberStatus = "active" | "removed";
export type OrgStatus = "active" | "suspended";
export type InvitationStatus = "pending" | "accepted" | "revoked" | "expired";
export type ProjectStatus = "active" | "archived";
export type TaskPriority = "low" | "medium" | "high" | "critical";
export type TaskStatus = "todo" | "in_progress" | "blocked" | "completed";
export type ApproverType = "role" | "user";
export type RequestStatus = "pending" | "approved" | "rejected" | "cancelled";
export type DecisionType = "approved" | "rejected";
export type NotificationType =
  | "task_assigned"
  | "task_status_changed"
  | "approval_requested"
  | "approval_decided"
  | "task_due_soon"
  | "task_overdue";

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_platform_admin: boolean;
  is_active: boolean;
  created_at: string;
}

export interface Membership {
  org_id: string;
  org_name: string;
  org_slug: string;
  role: MemberRole;
  status: MemberStatus;
}

export interface Me extends User {
  memberships: Membership[];
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  status: OrgStatus;
  created_at: string;
}

export interface MyOrganization extends Organization {
  role: MemberRole;
}

export interface Invitation {
  id: string;
  email: string;
  role: MemberRole;
  status: InvitationStatus;
  expires_at: string;
  created_at: string;
}

export interface InvitationCreated extends Invitation {
  token: string;
}

export interface Member {
  user_id: string;
  email: string;
  full_name: string;
  role: MemberRole;
  status: MemberStatus;
  created_at: string;
}

export interface Project {
  id: string;
  org_id: string;
  name: string;
  description: string | null;
  status: ProjectStatus;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectMember {
  user_id: string;
  full_name: string;
  email: string;
}

export interface ProjectDetail extends Project {
  members: ProjectMember[];
}

export interface Task {
  id: string;
  org_id: string;
  project_id: string;
  title: string;
  description: string | null;
  priority: TaskPriority;
  status: TaskStatus;
  assignee_id: string | null;
  created_by: string | null;
  due_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskStatusHistory {
  id: string;
  from_status: TaskStatus | null;
  to_status: TaskStatus;
  changed_by: string | null;
  changed_at: string;
}

export interface TaskDetail extends Task {
  history: TaskStatusHistory[];
}

export interface WorkflowStep {
  id: string;
  step_order: number;
  name: string;
  approver_type: ApproverType;
  approver_role: MemberRole | null;
  approver_user_id: string | null;
}

export interface WorkflowTemplate {
  id: string;
  org_id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  steps: WorkflowStep[];
}

export interface ApprovalRequest {
  id: string;
  org_id: string;
  template_id: string;
  template_name: string;
  requester_id: string;
  requester_name: string;
  title: string;
  details: Record<string, unknown>;
  status: RequestStatus;
  current_step_order: number;
  submitted_at: string;
  completed_at: string | null;
}

export interface ApprovalDecision {
  id: string;
  step_order: number;
  step_id: string | null;
  decided_by: string | null;
  decision: DecisionType;
  comment: string | null;
  decided_at: string;
}

export interface ApprovalRequestDetail extends ApprovalRequest {
  steps: WorkflowStep[];
  decisions: ApprovalDecision[];
  current_step: WorkflowStep | null;
  can_decide: boolean;
}

export interface AppNotification {
  id: string;
  org_id: string;
  type: NotificationType;
  title: string;
  body: string | null;
  resource_type: string | null;
  resource_id: string | null;
  is_read: boolean;
  created_at: string;
  read_at: string | null;
}

export interface AuditLog {
  id: string;
  org_id: string | null;
  actor_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ProjectsSummary {
  total: number;
  active: number;
  archived: number;
}

export interface TasksByStatus {
  todo: number;
  in_progress: number;
  blocked: number;
  completed: number;
}

export interface ApprovalsSummary {
  pending_total: number;
  awaiting_my_action: number;
  my_submitted_pending: number;
}

export interface DashboardSummary {
  projects: ProjectsSummary;
  tasks_by_status: TasksByStatus;
  my_tasks: number;
  overdue_tasks: number;
  approvals: ApprovalsSummary;
}

export interface PlatformStats {
  organizations: number;
  active_organizations: number;
  users: number;
  projects: number;
  tasks: number;
  audit_events: number;
}
