import { Link, Outlet } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui";

/** Minimal shell for platform-level pages that do NOT require an active workspace
 * (e.g. the platform admin, who is usually not a member of any organization). */
export function PlatformShell() {
  const { logout } = useAuth();
  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-2">
        <span className="font-semibold text-brand-700">Workflow Platform · Platform Admin</span>
        <div className="flex items-center gap-2">
          <Link to="/workspaces">
            <Button variant="ghost">Workspaces</Button>
          </Link>
          <Button variant="ghost" onClick={logout}>
            Log out
          </Button>
        </div>
      </header>
      <main className="p-4 md:p-6">
        <Outlet />
      </main>
    </div>
  );
}
