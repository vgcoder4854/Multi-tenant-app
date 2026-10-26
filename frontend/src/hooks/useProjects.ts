import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { projectsApi } from "@/api/tasks";
import { useAuth } from "@/lib/auth";

function useOrgId(): string {
  return useAuth().activeOrgId ?? "none";
}

export function useProjects() {
  const orgId = useOrgId();
  return useQuery({ queryKey: ["projects", orgId], queryFn: projectsApi.list });
}

export function useProject(id: string | undefined) {
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["project", orgId, id],
    queryFn: () => projectsApi.get(id as string),
    enabled: Boolean(id),
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  const orgId = useOrgId();
  return useMutation({
    mutationFn: projectsApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects", orgId] }),
  });
}

export function useUpdateProject(id: string) {
  const qc = useQueryClient();
  const orgId = useOrgId();
  return useMutation({
    mutationFn: (body: { name?: string; description?: string }) => projectsApi.update(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects", orgId] });
      qc.invalidateQueries({ queryKey: ["project", orgId, id] });
    },
  });
}

export function useArchiveProject() {
  const qc = useQueryClient();
  const orgId = useOrgId();
  return useMutation({
    mutationFn: (id: string) => projectsApi.archive(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects", orgId] }),
  });
}

export function useProjectMembers(id: string | undefined) {
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["project-members", orgId, id],
    queryFn: () => projectsApi.members(id as string),
    enabled: Boolean(id),
  });
}

export function useAddProjectMember(projectId: string) {
  const qc = useQueryClient();
  const orgId = useOrgId();
  return useMutation({
    mutationFn: (userId: string) => projectsApi.addMember(projectId, userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["project-members", orgId, projectId] });
      qc.invalidateQueries({ queryKey: ["project", orgId, projectId] });
    },
  });
}

export function useRemoveProjectMember(projectId: string) {
  const qc = useQueryClient();
  const orgId = useOrgId();
  return useMutation({
    mutationFn: (userId: string) => projectsApi.removeMember(projectId, userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["project-members", orgId, projectId] });
      qc.invalidateQueries({ queryKey: ["project", orgId, projectId] });
    },
  });
}
