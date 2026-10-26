import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Spinner } from "@/components/ui";

/** Redirects to /login when there is no session, and to /workspaces when the
 * user has not chosen a workspace yet. */
export function ProtectedRoute({ children, requireOrg = true }: { children: ReactNode; requireOrg?: boolean }) {
  const { isAuthenticated, activeOrgId, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner className="h-6 w-6 text-brand-600" />
      </div>
    );
  }
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  if (requireOrg && !activeOrgId) return <Navigate to="/workspaces" replace />;
  return <>{children}</>;
}
