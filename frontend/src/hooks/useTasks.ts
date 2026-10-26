import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { tasksApi } from "@/api/tasks";
import type { TaskFilters } from "@/api/tasks";
import { useAuth } from "@/lib/auth";
import type { TaskStatus } from "@/types";

function useOrgId(): string {
  return useAuth().activeOrgId ?? "none";
}

export function useTasks(filters: TaskFilters = {}) {
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["tasks", orgId, filters],
    queryFn: () => tasksApi.list(filters),
    placeholderData: (prev) => prev,
  });
}

export function useTask(id: string | undefined) {
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["task", orgId, id],
    queryFn: () => tasksApi.get(id as string),
    enabled: Boolean(id),
  });
}

function invalidateTasks(qc: ReturnType<typeof useQueryClient>, orgId: string) {
  qc.invalidateQueries({ queryKey: ["tasks", orgId] });
  qc.invalidateQueries({ queryKey: ["task", orgId] });
  qc.invalidateQueries({ queryKey: ["dashboard", orgId] });
  qc.invalidateQueries({ queryKey: ["notifications", orgId] });
}

export function useCreateTask() {
  const qc = useQueryClient();
  const orgId = useOrgId();
  return useMutation({
    mutationFn: tasksApi.create,
    onSuccess: () => invalidateTasks(qc, orgId),
  });
}

export function useUpdateTask(id: string) {
  const qc = useQueryClient();
  const orgId = useOrgId();
  return useMutation({
    mutationFn: (body: Parameters<typeof tasksApi.update>[1]) => tasksApi.update(id, body),
    onSuccess: () => invalidateTasks(qc, orgId),
  });
}

export function useChangeTaskStatus(id: string) {
  const qc = useQueryClient();
  const orgId = useOrgId();
  return useMutation({
    mutationFn: (status: TaskStatus) => tasksApi.changeStatus(id, status),
    onSuccess: () => invalidateTasks(qc, orgId),
  });
}

/** Change the status of any task by id (used by the inline row selector). */
export function useChangeTaskStatusById() {
  const qc = useQueryClient();
  const orgId = useOrgId();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: TaskStatus }) => tasksApi.changeStatus(id, status),
    onSuccess: () => invalidateTasks(qc, orgId),
  });
}
