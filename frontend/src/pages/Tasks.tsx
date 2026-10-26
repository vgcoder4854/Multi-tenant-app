import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { TaskFilters } from "@/api/tasks";
import { useCreateTask, useTask, useTasks, useUpdateTask, useChangeTaskStatusById } from "@/hooks/useTasks";
import { useProjects } from "@/hooks/useProjects";
import { useMembers } from "@/hooks/useAdmin";
import { useAuth } from "@/lib/auth";
import { RoleGate } from "@/components/RoleGate";
import { FilterBar } from "@/components/FilterBar";
import { FormField } from "@/components/FormField";
import {
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Input,
  Modal,
  Pagination,
  Select,
  Spinner,
  StatusBadge,
  Table,
  Textarea,
  useToast,
} from "@/components/ui";
import type { Task, TaskStatus } from "@/types";

const schema = z.object({
  project_id: z.string().min(1, "Project is required"),
  title: z.string().min(1, "Title is required"),
  description: z.string().optional(),
  priority: z.enum(["low", "medium", "high", "critical"]),
  assignee_id: z.string().optional(),
  due_date: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

const STATUSES: TaskStatus[] = ["todo", "in_progress", "blocked", "completed"];

export function Tasks() {
  const [filters, setFilters] = useState<TaskFilters>({ page: 1, page_size: 20 });
  const [params, setParams] = useSearchParams();
  const [openId, setOpenId] = useState<string | null>(params.get("open"));
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Task | null>(null);
  const [serverError, setServerError] = useState<unknown>(null);

  const { user, role } = useAuth();
  const { data, isLoading, error } = useTasks(filters);
  const { data: projects } = useProjects();
  const { data: members } = useMembers();
  const detail = useTask(openId ?? undefined);
  const create = useCreateTask();
  const update = useUpdateTask(editing?.id ?? "");
  const changeStatus = useChangeTaskStatusById();
  const toast = useToast();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  useEffect(() => {
    if (openId) setParams({ open: openId });
    else setParams({});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [openId]);

  const openCreate = () => {
    setEditing(null);
    reset({ project_id: "", title: "", description: "", priority: "medium", assignee_id: "", due_date: "" });
    setServerError(null);
    setFormOpen(true);
  };

  const openEdit = (task: Task) => {
    setEditing(task);
    reset({
      project_id: task.project_id,
      title: task.title,
      description: task.description ?? "",
      priority: task.priority,
      assignee_id: task.assignee_id ?? "",
      due_date: task.due_date ?? "",
    });
    setServerError(null);
    setFormOpen(true);
  };

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    const body = {
      project_id: values.project_id,
      title: values.title,
      description: values.description || undefined,
      priority: values.priority,
      assignee_id: values.assignee_id || null,
      due_date: values.due_date || null,
    };
    try {
      if (editing) await update.mutateAsync(body);
      else await create.mutateAsync(body);
      toast(editing ? "Task updated" : "Task created");
      setFormOpen(false);
    } catch (err) {
      setServerError(err);
    }
  };

  const canEdit = role === "org_admin" || role === "manager";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Tasks</h1>
        <RoleGate roles={["org_admin", "manager"]}>
          <Button onClick={openCreate}>New task</Button>
        </RoleGate>
      </div>

      <FilterBar value={filters} onChange={setFilters} projects={projects} members={members} />

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner className="h-6 w-6 text-brand-600" />
        </div>
      ) : error ? (
        <ErrorBanner error={error} />
      ) : data && data.items.length > 0 ? (
        <Card>
          <Table headers={["Title", "Project", "Status", "Priority", "Assignee", "Due", ""]}>
            {data.items.map((t) => {
              const isAssignee = user?.id === t.assignee_id;
              const canChange = isAssignee || canEdit;
              return (
                <tr key={t.id} className="hover:bg-slate-50">
                  <td className="px-3 py-2">
                    <button className="text-left font-medium text-brand-700 hover:underline" onClick={() => setOpenId(t.id)}>
                      {t.title}
                    </button>
                  </td>
                  <td className="px-3 py-2 text-slate-500">{projects?.find((p) => p.id === t.project_id)?.name ?? "—"}</td>
                  <td className="px-3 py-2">
                    {canChange ? (
                      <select
                        aria-label={`Status for ${t.title}`}
                        className="rounded border border-slate-300 px-2 py-1 text-xs"
                        value={t.status}
                        onChange={async (e) => {
                          try {
                            await changeStatus.mutateAsync({ id: t.id, status: e.target.value as TaskStatus });
                          } catch (err) {
                            toast(err instanceof Error ? err.message : "Status change failed", "error");
                          }
                        }}
                      >
                        {STATUSES.map((s) => (
                          <option key={s} value={s}>
                            {s.replace(/_/g, " ")}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <StatusBadge value={t.status} />
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <StatusBadge value={t.priority} />
                  </td>
                  <td className="px-3 py-2 text-slate-500">
                    {members?.find((m) => m.user_id === t.assignee_id)?.full_name ?? "Unassigned"}
                  </td>
                  <td className="px-3 py-2 text-slate-500">{t.due_date ?? "—"}</td>
                  <td className="px-3 py-2 text-right">
                    <RoleGate roles={["org_admin", "manager"]}>
                      <button className="text-xs text-brand-600 hover:underline" onClick={() => openEdit(t)}>
                        Edit
                      </button>
                    </RoleGate>
                  </td>
                </tr>
              );
            })}
          </Table>
          <Pagination
            page={data.page}
            pageSize={data.page_size}
            total={data.total}
            onChange={(page) => setFilters((f) => ({ ...f, page }))}
          />
        </Card>
      ) : (
        <Card>
          <EmptyState title="No tasks found" description="Try changing the filters." />
        </Card>
      )}

      {/* Create / edit modal */}
      <Modal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        title={editing ? "Edit task" : "New task"}
        footer={
          <>
            <Button variant="secondary" onClick={() => setFormOpen(false)}>
              Cancel
            </Button>
            <Button form="task-form" type="submit" loading={isSubmitting}>
              {editing ? "Save" : "Create"}
            </Button>
          </>
        }
      >
        <ErrorBanner error={serverError} />
        <form id="task-form" onSubmit={handleSubmit(onSubmit)} noValidate>
          <FormField label="Project" htmlFor="project_id" error={errors.project_id?.message}>
            <Select id="project_id" disabled={Boolean(editing)} {...register("project_id")}>
              <option value="">Select a project…</option>
              {projects
                ?.filter((p) => p.status === "active")
                .map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
            </Select>
          </FormField>
          <FormField label="Title" htmlFor="title" error={errors.title?.message}>
            <Input id="title" {...register("title")} />
          </FormField>
          <FormField label="Description" htmlFor="description">
            <Textarea id="description" rows={3} {...register("description")} />
          </FormField>
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Priority" htmlFor="priority">
              <Select id="priority" {...register("priority")}>
                {(["low", "medium", "high", "critical"] as const).map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </Select>
            </FormField>
            <FormField label="Due date" htmlFor="due_date">
              <Input id="due_date" type="date" {...register("due_date")} />
            </FormField>
          </div>
          <FormField label="Assignee" htmlFor="assignee_id" hint="Only active members of this organization">
            <Select id="assignee_id" {...register("assignee_id")}>
              <option value="">Unassigned</option>
              {members
                ?.filter((m) => m.status === "active")
                .map((m) => (
                  <option key={m.user_id} value={m.user_id}>
                    {m.full_name}
                  </option>
                ))}
            </Select>
          </FormField>
        </form>
      </Modal>

      {/* Detail drawer */}
      <Modal open={Boolean(openId)} onClose={() => setOpenId(null)} title={detail.data?.title ?? "Task"}>
        {detail.isLoading ? (
          <Spinner />
        ) : detail.data ? (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <StatusBadge value={detail.data.status} />
              <StatusBadge value={detail.data.priority} />
              <span className="text-xs text-slate-500">Due {detail.data.due_date ?? "—"}</span>
            </div>
            {detail.data.description && <p className="text-sm text-slate-600">{detail.data.description}</p>}
            <div>
              <h3 className="mb-2 text-sm font-medium">Status history</h3>
              <ol className="space-y-1 border-l border-slate-200 pl-4 text-sm">
                {detail.data.history.map((h) => (
                  <li key={h.id}>
                    <span className="text-slate-500">{new Date(h.changed_at).toLocaleString()}</span> —{" "}
                    {h.from_status ? `${h.from_status} → ` : ""}
                    <strong>{h.to_status}</strong>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        ) : (
          <ErrorBanner error={detail.error} />
        )}
      </Modal>
    </div>
  );
}
