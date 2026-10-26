import { NavLink } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { cn } from "@/components/ui";
import type { MemberRole } from "@/types";

interface NavItem {
  to: string;
  label: string;
  roles?: MemberRole[]; // undefined = everyone
  platformOnly?: boolean;
}

const ITEMS: NavItem[] = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/projects", label: "Projects" },
  { to: "/tasks", label: "Tasks" },
  { to: "/requests/mine", label: "My Requests" },
  { to: "/requests/pending", label: "Pending For Me" },
  { to: "/workflows", label: "Workflow Templates", roles: ["org_admin"] },
  { to: "/notifications", label: "Notifications" },
  { to: "/admin/members", label: "Members", roles: ["org_admin"] },
  { to: "/admin/audit", label: "Audit Log", roles: ["org_admin"] },
  { to: "/platform", label: "Platform Admin", platformOnly: true },
];

export function Sidebar() {
  const { hasRole, user } = useAuth();
  const visible = ITEMS.filter((item) => {
    if (item.platformOnly) return Boolean(user?.is_platform_admin);
    if (item.roles) return hasRole(...item.roles);
    return true;
  });

  return (
    <aside className="hidden w-60 shrink-0 border-r border-slate-200 bg-white p-3 md:block">
      <nav className="flex flex-col gap-1">
        {visible.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                "rounded-md px-3 py-2 text-sm",
                isActive ? "bg-brand-50 font-medium text-brand-700" : "text-slate-600 hover:bg-slate-100",
              )
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
