import { useState } from "react";
import { Link } from "react-router-dom";
import { dashboardApi } from "@/api/misc";
import type { DashboardFilters } from "@/api/misc";
import { useDashboardSummary, useMembers } from "@/hooks/useAdmin";
import { useProjects } from "@/hooks/useProjects";
import { usePendingForMe } from "@/hooks/useWorkflows";
import { RoleGate } from "@/components/RoleGate";
import { Button, Card, EmptyState, ErrorBanner, Input, Select, Spinner, useToast } from "@/components/ui";
import type { TaskStatus } from "@/types";

const STATUS_ORDER: TaskStatus[] = ["todo", "in_progress", "blocked", "completed"];

function StatCard({ label, value, tone = "slate" }: { label: string; value: number; tone?: string }) {
  const tones: Record<string, string> = {
    slate: "text-slate-900",
    blue: "text-blue-600",
    amber: "text-amber-600",
    red: "text-red-600",
  };
  return (
    <Card>
      <p className="text-sm text-slate-500">{label}</p>
      <p className={`mt-1 text-3xl font-semibold ${tones[tone]}`}>{value}</p>
    </Card>
  );
}

export function Dashboard() {
  const [filters, setFilters] = useState<DashboardFilters>({});
  const { data, isLoading, error } = useDashboardSummary(filters);
  const { data: projects } = useProjects();
  const { data: members } = useMembers();
  const pending = usePendingForMe();
  const toast = useToast();

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner className="h-6 w-6 text-brand-600" />
      </div>
    );
  }
  if (error || !data) return <ErrorBanner error={error ?? "Failed to load dashboard"} />;

  const maxStatus = Math.max(1, ...Object.values(data.tasks_by_status));
  const set = (patch: Partial<DashboardFilters>) => setFilters((f) => ({ ...f, ...patch }));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold">Dashboard</h1>
        <RoleGate roles={["org_admin", "manager"]}>
          <Button
            variant="secondary"
            onClick={async () => {
              try {
                await dashboardApi.exportCsv(filters);
              } catch {
                toast("Export failed", "error");
              }
            }}
          >
            Export CSV
          </Button>
        </RoleGate>
      </div>

      {/* Filters */}
      <Card className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Select value={filters.project_id ?? ""} onChange={(e) => set({ project_id: e.target.value || undefined })}>
          <option value="">All projects</option>
          {projects?.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </Select>
        <Select value={filters.assignee_id ?? ""} onChange={(e) => set({ assignee_id: e.target.value || undefined })}>
          <option value="">All assignees</option>
          {members?.map((m) => (
            <option key={m.user_id} value={m.user_id}>
              {m.full_name}
            </option>
          ))}
        </Select>
        <Select value={filters.status ?? ""} onChange={(e) => set({ status: (e.target.value || undefined) as TaskStatus })}>
          <option value="">All statuses</option>
          {STATUS_ORDER.map((s) => (
            <option key={s} value={s}>
              {s.replace(/_/g, " ")}
            </option>
          ))}
        </Select>
        <Input
          type="date"
          aria-label="From date"
          value={filters.date_from?.slice(0, 10) ?? ""}
          onChange={(e) => set({ date_from: e.target.value ? `${e.target.value}T00:00:00Z` : undefined })}
        />
      </Card>

      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Total projects" value={data.projects.total} />
        <StatCard label="Active projects" value={data.projects.active} tone="blue" />
        <StatCard label="My tasks" value={data.my_tasks} />
        <StatCard label="Overdue tasks" value={data.overdue_tasks} tone="red" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="mb-3 font-medium">Tasks by status</h2>
          <div className="space-y-2">
            {STATUS_ORDER.map((s) => (
              <div key={s} className="flex items-center gap-3">
                <span className="w-24 text-sm text-slate-600">{s.replace(/_/g, " ")}</span>
                <div className="h-4 flex-1 rounded bg-slate-100">
                  <div
                    className="h-4 rounded bg-brand-500"
                    style={{ width: `${(data.tasks_by_status[s] / maxStatus) * 100}%` }}
                  />
                </div>
                <span className="w-8 text-right text-sm tabular-nums">{data.tasks_by_status[s]}</span>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <h2 className="mb-3 font-medium">Approvals</h2>
          <div className="grid grid-cols-3 gap-3 text-center">
            <div>
              <p className="text-2xl font-semibold">{data.approvals.pending_total}</p>
              <p className="text-xs text-slate-500">Pending total</p>
            </div>
            <div>
              <p className="text-2xl font-semibold text-amber-600">{data.approvals.awaiting_my_action}</p>
              <p className="text-xs text-slate-500">Awaiting me</p>
            </div>
            <div>
              <p className="text-2xl font-semibold">{data.approvals.my_submitted_pending}</p>
              <p className="text-xs text-slate-500">My submitted</p>
            </div>
          </div>
        </Card>
      </div>

      <Card>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-medium">Awaiting my action</h2>
          <Link to="/requests/pending" className="text-sm text-brand-600 hover:underline">
            View all
          </Link>
        </div>
        {pending.data && pending.data.length > 0 ? (
          <ul className="divide-y divide-slate-100">
            {pending.data.slice(0, 5).map((r) => (
              <li key={r.id} className="flex items-center justify-between py-2">
                <Link to={`/requests/${r.id}`} className="text-sm hover:underline">
                  {r.title}
                </Link>
                <span className="text-xs text-slate-500">
                  step {r.current_step_order} · {r.template_name}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState title="Nothing awaiting your approval" />
        )}
      </Card>
    </div>
  );
}
