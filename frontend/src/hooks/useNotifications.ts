import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notificationsApi } from "@/api/misc";
import { useAuth } from "@/lib/auth";

function useOrgId(): string {
  return useAuth().activeOrgId ?? "none";
}

export function useNotifications(unreadOnly = false) {
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["notifications", orgId, { unreadOnly }],
    queryFn: () => notificationsApi.list({ unread_only: unreadOnly }),
  });
}

export function useUnreadCount() {
  const orgId = useOrgId();
  return useQuery({
    queryKey: ["notifications", orgId, "unread-count"],
    queryFn: notificationsApi.unreadCount,
    refetchInterval: 30_000, // poll every 30s for the bell badge
  });
}

export function useMarkRead() {
  const qc = useQueryClient();
  const orgId = useOrgId();
  return useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications", orgId] }),
  });
}

export function useMarkAllRead() {
  const qc = useQueryClient();
  const orgId = useOrgId();
  return useMutation({
    mutationFn: notificationsApi.markAllRead,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications", orgId] }),
  });
}
