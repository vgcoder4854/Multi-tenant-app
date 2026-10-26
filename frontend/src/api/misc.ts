import { api, downloadCsv } from "./client";
import type {
  AppNotification,
  AuditLog,
  DashboardSummary,
  Page,
  TaskPriority,
  TaskStatus,
} from "@/types";

export const notificationsApi = {
  list: (params: { unread_only?: boolean; page?: number; page_size?: number } = {}) =>
    api.get<Page<AppNotification>>("/notifications", params),
  unreadCount: () => api.get<{ unread: number }>("/notifications/unread-count"),
  markRead: (id: string) => api.post<AppNotification>(`/notifications/${id}/read`),
  markAllRead: () => api.post<{ unread: number }>("/notifications/read-all"),
};

export interface AuditFilters {
  actor_id?: string;
  action?: string;
  resource_type?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

export const auditApi = {
  list: (filters: AuditFilters = {}) => api.get<Page<AuditLog>>("/audit-logs", filters as Record<string, never>),
  platformList: (filters: AuditFilters & { org_id?: string } = {}) =>
    api.get<Page<AuditLog>>("/platform/audit-logs", filters as Record<string, never>),
};

export interface DashboardFilters {
  project_id?: string;
  assignee_id?: string;
  status?: TaskStatus;
  date_from?: string;
  date_to?: string;
}

export const dashboardApi = {
  summary: (filters: DashboardFilters = {}) =>
    api.get<DashboardSummary>("/dashboard/summary", filters as Record<string, never>),
  exportCsv: (filters: DashboardFilters = {}) =>
    downloadCsv("/dashboard/export.csv", "tasks.csv", filters as Record<string, never>),
};

export const adminApi = {
  runDueScan: () => api.post<{ scanned: number; notified: number }>("/admin/run-due-scan"),
};

export type { TaskPriority };
