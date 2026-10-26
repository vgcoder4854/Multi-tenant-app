import { useState } from "react";
import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useArchiveProject, useCreateProject, useProjects } from "@/hooks/useProjects";
import { RoleGate } from "@/components/RoleGate";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { FormField } from "@/components/FormField";
import {
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Input,
  Modal,
  Spinner,
  StatusBadge,
  Table,
  Textarea,
  useToast,
} from "@/components/ui";
import type { Project } from "@/types";

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export function Projects() {
  const { data, isLoading, error } = useProjects();
  const create = useCreateProject();
  const archive = useArchiveProject();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [toArchive, setToArchive] = useState<Project | null>(null);
  const [serverError, setServerError] = useState<unknown>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      await create.mutateAsync(values);
      toast("Project created");
      reset();
      setOpen(false);
    } catch (err) {
      setServerError(err);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Projects</h1>
        <RoleGate roles={["org_admin"]}>
          <Button onClick={() => setOpen(true)}>New project</Button>
        </RoleGate>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner className="h-6 w-6 text-brand-600" />
        </div>
      ) : error ? (
        <ErrorBanner error={error} />
      ) : data && data.length > 0 ? (
        <Card>
          <Table headers={["Name", "Status", "Created", ""]}>
            {data.map((p) => (
              <tr key={p.id} className="hover:bg-slate-50">
                <td className="px-3 py-2">
                  <Link to={`/projects/${p.id}`} className="font-medium text-brand-700 hover:underline">
                    {p.name}
                  </Link>
                  {p.description && <p className="text-xs text-slate-500">{p.description}</p>}
                </td>
                <td className="px-3 py-2">
                  <StatusBadge value={p.status} />
                </td>
                <td className="px-3 py-2 text-slate-500">{new Date(p.created_at).toLocaleDateString()}</td>
                <td className="px-3 py-2 text-right">
                  <RoleGate roles={["org_admin"]}>
                    {p.status === "active" && (
                      <Button variant="secondary" onClick={() => setToArchive(p)}>
                        Archive
                      </Button>
                    )}
                  </RoleGate>
                </td>
              </tr>
            ))}
          </Table>
        </Card>
      ) : (
        <Card>
          <EmptyState title="No projects yet" description="Create a project to start managing tasks." />
        </Card>
      )}

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="New project"
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button form="project-form" type="submit" loading={isSubmitting}>
              Create
            </Button>
          </>
        }
      >
        <ErrorBanner error={serverError} />
        <form id="project-form" onSubmit={handleSubmit(onSubmit)} noValidate>
          <FormField label="Name" htmlFor="name" error={errors.name?.message}>
            <Input id="name" {...register("name")} />
          </FormField>
          <FormField label="Description" htmlFor="description" error={errors.description?.message}>
            <Textarea id="description" rows={3} {...register("description")} />
          </FormField>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(toArchive)}
        title="Archive project"
        message={`Archive "${toArchive?.name}"? Its tasks become read-only.`}
        confirmLabel="Archive"
        danger
        loading={archive.isPending}
        onCancel={() => setToArchive(null)}
        onConfirm={async () => {
          if (!toArchive) return;
          await archive.mutateAsync(toArchive.id);
          toast("Project archived");
          setToArchive(null);
        }}
      />
    </div>
  );
}
