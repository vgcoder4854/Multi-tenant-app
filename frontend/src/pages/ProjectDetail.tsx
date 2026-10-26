import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  useAddProjectMember,
  useProject,
  useProjectMembers,
  useRemoveProjectMember,
} from "@/hooks/useProjects";
import { useMembers } from "@/hooks/useAdmin";
import { useTasks } from "@/hooks/useTasks";
import { RoleGate } from "@/components/RoleGate";
import {
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Select,
  Spinner,
  StatusBadge,
  Table,
  useToast,
} from "@/components/ui";

export function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: project, isLoading, error } = useProject(id);
  const { data: members } = useProjectMembers(id);
  const { data: orgMembers } = useMembers();
  const tasks = useTasks({ project_id: id, page_size: 100 });
  const addMember = useAddProjectMember(id ?? "");
  const removeMember = useRemoveProjectMember(id ?? "");
  const toast = useToast();
  const [toAdd, setToAdd] = useState("");

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner className="h-6 w-6 text-brand-600" />
      </div>
    );
  }
  if (error || !project) return <ErrorBanner error={error ?? "Project not found"} />;

  const memberIds = new Set((members ?? []).map((m) => m.user_id));
  const candidates = (orgMembers ?? []).filter((m) => !memberIds.has(m.user_id) && m.status === "active");

  return (
    <div className="space-y-5">
      <div>
        <Link to="/projects" className="text-sm text-brand-600 hover:underline">
          ← Projects
        </Link>
        <div className="mt-1 flex items-center gap-3">
          <h1 className="text-xl font-semibold">{project.name}</h1>
          <StatusBadge value={project.status} />
        </div>
        {project.description && <p className="mt-1 text-sm text-slate-600">{project.description}</p>}
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <h2 className="mb-3 font-medium">Tasks</h2>
          {tasks.isLoading ? (
            <Spinner />
          ) : tasks.data && tasks.data.items.length > 0 ? (
            <Table headers={["Title", "Status", "Priority", "Due"]}>
              {tasks.data.items.map((t) => (
                <tr key={t.id}>
                  <td className="px-3 py-2">
                    <Link to={`/tasks?open=${t.id}`} className="text-brand-700 hover:underline">
                      {t.title}
                    </Link>
                  </td>
                  <td className="px-3 py-2">
                    <StatusBadge value={t.status} />
                  </td>
                  <td className="px-3 py-2">
                    <StatusBadge value={t.priority} />
                  </td>
                  <td className="px-3 py-2 text-slate-500">{t.due_date ?? "—"}</td>
                </tr>
              ))}
            </Table>
          ) : (
            <EmptyState title="No tasks in this project yet" />
          )}
        </Card>

        <Card>
          <h2 className="mb-3 font-medium">Members</h2>
          <ul className="mb-4 divide-y divide-slate-100">
            {(members ?? []).map((m) => (
              <li key={m.user_id} className="flex items-center justify-between py-2 text-sm">
                <span>
                  {m.full_name}
                  <span className="block text-xs text-slate-500">{m.email}</span>
                </span>
                <RoleGate roles={["org_admin"]}>
                  <button
                    className="text-xs text-red-600 hover:underline"
                    onClick={async () => {
                      await removeMember.mutateAsync(m.user_id);
                      toast("Member removed");
                    }}
                  >
                    Remove
                  </button>
                </RoleGate>
              </li>
            ))}
            {(members ?? []).length === 0 && <li className="py-2 text-sm text-slate-500">No members.</li>}
          </ul>

          <RoleGate roles={["org_admin"]}>
            <div className="flex gap-2">
              <Select aria-label="Add member" value={toAdd} onChange={(e) => setToAdd(e.target.value)}>
                <option value="">Add a member…</option>
                {candidates.map((m) => (
                  <option key={m.user_id} value={m.user_id}>
                    {m.full_name}
                  </option>
                ))}
              </Select>
              <Button
                disabled={!toAdd}
                onClick={async () => {
                  await addMember.mutateAsync(toAdd);
                  toast("Member added");
                  setToAdd("");
                }}
              >
                Add
              </Button>
            </div>
          </RoleGate>
        </Card>
      </div>
    </div>
  );
}
