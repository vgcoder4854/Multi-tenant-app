import { api } from "./client";
import type {
  Page,
  Project,
  ProjectDetail,
  ProjectMember,
  Task,
  TaskDetail,
  TaskPriority,
  TaskStatus,
} from "@/types";

export const projectsApi = {
  list: () => api.get<Project[]>("/projects"),
  get: (id: string) => api.get<ProjectDetail>(`/projects/${id}`),
  create: (body: { name: string; description?: string }) => api.post<Project>("/projects", body),
  update: (id: string, body: { name?: string; description?: string }) =>
    api.patch<Project>(`/projects/${id}`, body),
  archive: (id: string) => api.post<Project>(`/projects/${id}/archive`),
  members: (id: string) => api.get<ProjectMember[]>(`/projects/${id}/members`),
  addMember: (id: string, userId: string) =>
    api.post<void>(`/projects/${id}/members`, { user_id: userId }),
  removeMember: (id: string, userId: string) => api.del<void>(`/projects/${id}/members/${userId}`),
};

export interface TaskFilters {
  project_id?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
  assignee_id?: string;
  due_from?: string;
  due_to?: string;
  search?: string;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

export const tasksApi = {
  list: (filters: TaskFilters = {}) => api.get<Page<Task>>("/tasks", filters as Record<string, never>),
  get: (id: string) => api.get<TaskDetail>(`/tasks/${id}`),
  create: (body: {
    project_id: string;
    title: string;
    description?: string;
    priority?: TaskPriority;
    assignee_id?: string | null;
    due_date?: string | null;
  }) => api.post<Task>("/tasks", body),
  update: (
    id: string,
    body: {
      title?: string;
      description?: string;
      priority?: TaskPriority;
      assignee_id?: string | null;
      due_date?: string | null;
    },
  ) => api.patch<Task>(`/tasks/${id}`, body),
  changeStatus: (id: string, status: TaskStatus) => api.patch<Task>(`/tasks/${id}/status`, { status }),
};
