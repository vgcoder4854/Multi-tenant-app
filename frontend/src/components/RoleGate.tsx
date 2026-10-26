import type { ReactNode } from "react";
import { useAuth } from "@/lib/auth";
import type { MemberRole } from "@/types";

/** Renders children only when the active role is allowed. The backend is the real
 * security layer; this only hides UI for usability. */
export function RoleGate({
  roles,
  children,
  fallback = null,
}: {
  roles: MemberRole[];
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const { hasRole } = useAuth();
  return <>{hasRole(...roles) ? children : fallback}</>;
}
