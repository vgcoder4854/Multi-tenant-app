import { Link } from "react-router-dom";
import { useUnreadCount } from "@/hooks/useNotifications";

export function NotificationBell() {
  const { data } = useUnreadCount();
  const unread = data?.unread ?? 0;
  return (
    <Link
      to="/notifications"
      aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`}
      className="relative rounded-md p-2 text-slate-500 hover:bg-slate-100"
    >
      <span aria-hidden>🔔</span>
      {unread > 0 && (
        <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-bold text-white">
          {unread > 99 ? "99+" : unread}
        </span>
      )}
    </Link>
  );
}
