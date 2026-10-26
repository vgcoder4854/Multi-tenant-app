import { Link } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui";
import { NotificationBell } from "./NotificationBell";
import { WorkspaceSwitcher } from "./WorkspaceSwitcher";

export function Topbar() {
  const { user, logout } = useAuth();
  return (
    <header className="flex items-center justify-between gap-4 border-b border-slate-200 bg-white px-4 py-2">
      <Link to="/dashboard" className="font-semibold text-brand-700">
        Workflow Platform
      </Link>
      <div className="flex items-center gap-3">
        <WorkspaceSwitcher />
        <NotificationBell />
        <div className="flex items-center gap-2 border-l border-slate-200 pl-3">
          <span className="hidden text-sm text-slate-600 sm:inline">{user?.full_name}</span>
          <Button variant="ghost" onClick={logout}>
            Log out
          </Button>
        </div>
      </div>
    </header>
  );
}
