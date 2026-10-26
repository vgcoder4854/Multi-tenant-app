import { Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { orgsApi } from "@/api/orgs";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function Layout() {
  const { activeOrgId, logout } = useAuth();
  const { data: orgs } = useQuery({ queryKey: ["my-orgs"], queryFn: orgsApi.mine });
  const active = orgs?.find((o) => o.id === activeOrgId);

  if (active && active.status === "suspended") {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <div className="card max-w-md p-8 text-center">
          <h1 className="mb-2 text-xl font-semibold text-red-700">Workspace suspended</h1>
          <p className="mb-6 text-sm text-slate-600">
            <strong>{active.name}</strong> has been suspended by a platform administrator. All data is
            temporarily read-only/unavailable. Please contact support.
          </p>
          <Button variant="secondary" onClick={logout}>
            Log out
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col">
      <Topbar />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 overflow-x-hidden p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
