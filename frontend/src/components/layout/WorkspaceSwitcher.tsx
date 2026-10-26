import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui";

export function WorkspaceSwitcher() {
  const { user, activeOrgId, switchOrganization } = useAuth();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  const active = user?.memberships.find((m) => m.org_id === activeOrgId);
  if (!user || user.memberships.length === 0) return null;

  const choose = async (orgId: string) => {
    setBusy(true);
    try {
      if (orgId !== activeOrgId) await switchOrganization(orgId);
      setOpen(false);
      navigate("/dashboard");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="relative">
      <Button variant="secondary" onClick={() => setOpen((v) => !v)} aria-haspopup="menu" aria-expanded={open}>
        <span className="font-medium">{active?.org_name ?? "Select workspace"}</span>
        <span className="text-xs text-slate-400">{active?.role}</span>
        <span aria-hidden>▾</span>
      </Button>
      {open && (
        <div role="menu" className="absolute right-0 z-40 mt-1 w-64 rounded-md border border-slate-200 bg-white py-1 shadow-lg">
          {user.memberships.map((m) => (
            <button
              key={m.org_id}
              role="menuitem"
              disabled={busy}
              onClick={() => choose(m.org_id)}
              className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-slate-50"
            >
              <span>{m.org_name}</span>
              <span className="text-xs text-slate-400">{m.role}</span>
            </button>
          ))}
          <div className="border-t border-slate-100">
            <button
              role="menuitem"
              onClick={() => {
                setOpen(false);
                navigate("/workspaces");
              }}
              className="w-full px-3 py-2 text-left text-sm text-brand-600 hover:bg-slate-50"
            >
              Manage workspaces…
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
