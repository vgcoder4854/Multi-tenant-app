import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMarkAllRead, useMarkRead, useNotifications } from "@/hooks/useNotifications";
import { Button, Card, EmptyState, ErrorBanner, Spinner, cn } from "@/components/ui";
import type { AppNotification } from "@/types";

export function Notifications() {
  const [unreadOnly, setUnreadOnly] = useState(false);
  const { data, isLoading, error } = useNotifications(unreadOnly);
  const markRead = useMarkRead();
  const markAll = useMarkAllRead();
  const navigate = useNavigate();

  const open = async (n: AppNotification) => {
    if (!n.is_read) await markRead.mutateAsync(n.id);
    if (n.resource_type === "task" && n.resource_id) navigate(`/tasks?open=${n.resource_id}`);
    else if (n.resource_type === "approval_request" && n.resource_id) navigate(`/requests/${n.resource_id}`);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Notifications</h1>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setUnreadOnly((v) => !v)}>
            {unreadOnly ? "Show all" : "Unread only"}
          </Button>
          <Button variant="secondary" onClick={() => markAll.mutate()} loading={markAll.isPending}>
            Mark all read
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner className="h-6 w-6 text-brand-600" />
        </div>
      ) : error ? (
        <ErrorBanner error={error} />
      ) : data && data.items.length > 0 ? (
        <Card className="p-0">
          <ul className="divide-y divide-slate-100">
            {data.items.map((n) => (
              <li key={n.id}>
                <button
                  onClick={() => open(n)}
                  className={cn(
                    "flex w-full flex-col items-start gap-1 px-4 py-3 text-left hover:bg-slate-50",
                    !n.is_read && "bg-brand-50/50",
                  )}
                >
                  <span className={cn("text-sm", !n.is_read && "font-semibold")}>{n.title}</span>
                  {n.body && <span className="text-xs text-slate-500">{n.body}</span>}
                  <span className="text-xs text-slate-400">
                    {n.type.replace(/_/g, " ")} · {new Date(n.created_at).toLocaleString()}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </Card>
      ) : (
        <Card>
          <EmptyState title="No notifications" />
        </Card>
      )}
    </div>
  );
}
