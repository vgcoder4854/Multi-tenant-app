import { useState } from "react";
import { useCreateTemplate, useDeactivateTemplate, useWorkflowTemplates } from "@/hooks/useWorkflows";
import { useMembers } from "@/hooks/useAdmin";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { FormField } from "@/components/FormField";
import {
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Input,
  Modal,
  Select,
  Spinner,
  StatusBadge,
  Table,
  useToast,
} from "@/components/ui";
import type { ApproverType, MemberRole, WorkflowTemplate } from "@/types";

interface StepDraft {
  name: string;
  approver_type: ApproverType;
  approver_role: MemberRole;
  approver_user_id: string;
}

const newStep = (): StepDraft => ({ name: "Approval step", approver_type: "role", approver_role: "manager", approver_user_id: "" });

export function Workflows() {
  const { data, isLoading, error } = useWorkflowTemplates();
  const { data: members } = useMembers();
  const create = useCreateTemplate();
  const deactivate = useDeactivateTemplate();
  const toast = useToast();

  const [open, setOpen] = useState(false);
  const [toDeactivate, setToDeactivate] = useState<WorkflowTemplate | null>(null);
  const [serverError, setServerError] = useState<unknown>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [steps, setSteps] = useState<StepDraft[]>([newStep()]);

  const reset = () => {
    setName("");
    setDescription("");
    setSteps([newStep()]);
    setServerError(null);
  };

  const submit = async () => {
    setServerError(null);
    try {
      await create.mutateAsync({
        name,
        description: description || undefined,
        steps: steps.map((s) => ({
          name: s.name,
          approver_type: s.approver_type,
          approver_role: s.approver_type === "role" ? s.approver_role : null,
          approver_user_id: s.approver_type === "user" ? s.approver_user_id : null,
        })),
      });
      toast("Template created");
      setOpen(false);
      reset();
    } catch (err) {
      setServerError(err);
    }
  };

  const move = (index: number, delta: number) => {
    setSteps((prev) => {
      const next = [...prev];
      const target = index + delta;
      if (target < 0 || target >= next.length) return prev;
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Workflow templates</h1>
        <Button onClick={() => setOpen(true)}>New template</Button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner className="h-6 w-6 text-brand-600" />
        </div>
      ) : error ? (
        <ErrorBanner error={error} />
      ) : data && data.length > 0 ? (
        <Card>
          <Table headers={["Name", "Steps", "Active", ""]}>
            {data.map((t) => (
              <tr key={t.id}>
                <td className="px-3 py-2">
                  <span className="font-medium">{t.name}</span>
                  {t.description && <p className="text-xs text-slate-500">{t.description}</p>}
                </td>
                <td className="px-3 py-2 text-slate-600">
                  <ol className="list-decimal pl-4 text-xs">
                    {t.steps.map((s) => (
                      <li key={s.id}>
                        {s.name} —{" "}
                        {s.approver_type === "role" ? s.approver_role : members?.find((m) => m.user_id === s.approver_user_id)?.full_name ?? "user"}
                      </li>
                    ))}
                  </ol>
                </td>
                <td className="px-3 py-2">
                  <StatusBadge value={t.is_active ? "active" : "archived"} />
                </td>
                <td className="px-3 py-2 text-right">
                  {t.is_active && (
                    <button className="text-xs text-red-600 hover:underline" onClick={() => setToDeactivate(t)}>
                      Deactivate
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </Table>
        </Card>
      ) : (
        <Card>
          <EmptyState title="No templates yet" description="Create a template to define an approval flow." />
        </Card>
      )}

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="New workflow template"
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button onClick={submit} loading={create.isPending}>
              Create
            </Button>
          </>
        }
      >
        <ErrorBanner error={serverError} />
        <FormField label="Name">
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </FormField>
        <FormField label="Description">
          <Input value={description} onChange={(e) => setDescription(e.target.value)} />
        </FormField>

        <div className="mb-2 flex items-center justify-between">
          <span className="label mb-0">Steps (in order)</span>
          <Button variant="secondary" onClick={() => setSteps((s) => [...s, newStep()])}>
            Add step
          </Button>
        </div>
        <div className="space-y-3">
          {steps.map((step, i) => (
            <div key={i} className="rounded-md border border-slate-200 p-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500">Step {i + 1}</span>
                <div className="flex gap-1">
                  <button className="text-xs text-slate-500" onClick={() => move(i, -1)} aria-label="Move up">
                    ↑
                  </button>
                  <button className="text-xs text-slate-500" onClick={() => move(i, 1)} aria-label="Move down">
                    ↓
                  </button>
                  <button
                    className="text-xs text-red-600"
                    onClick={() => setSteps((s) => s.filter((_, idx) => idx !== i))}
                    aria-label="Remove step"
                  >
                    ✕
                  </button>
                </div>
              </div>
              <Input
                className="mb-2"
                placeholder="Step name"
                value={step.name}
                onChange={(e) => setSteps((s) => s.map((x, idx) => (idx === i ? { ...x, name: e.target.value } : x)))}
              />
              <div className="grid grid-cols-2 gap-2">
                <Select
                  value={step.approver_type}
                  onChange={(e) =>
                    setSteps((s) => s.map((x, idx) => (idx === i ? { ...x, approver_type: e.target.value as ApproverType } : x)))
                  }
                >
                  <option value="role">By role</option>
                  <option value="user">Specific user</option>
                </Select>
                {step.approver_type === "role" ? (
                  <Select
                    value={step.approver_role}
                    onChange={(e) =>
                      setSteps((s) => s.map((x, idx) => (idx === i ? { ...x, approver_role: e.target.value as MemberRole } : x)))
                    }
                  >
                    <option value="manager">manager</option>
                    <option value="org_admin">org_admin</option>
                  </Select>
                ) : (
                  <Select
                    value={step.approver_user_id}
                    onChange={(e) =>
                      setSteps((s) => s.map((x, idx) => (idx === i ? { ...x, approver_user_id: e.target.value } : x)))
                    }
                  >
                    <option value="">Select a user…</option>
                    {members?.map((m) => (
                      <option key={m.user_id} value={m.user_id}>
                        {m.full_name}
                      </option>
                    ))}
                  </Select>
                )}
              </div>
            </div>
          ))}
        </div>
      </Modal>

      <ConfirmDialog
        open={Boolean(toDeactivate)}
        title="Deactivate template"
        message={`Deactivate "${toDeactivate?.name}"? It can no longer be used for new requests.`}
        confirmLabel="Deactivate"
        danger
        onCancel={() => setToDeactivate(null)}
        onConfirm={async () => {
          if (!toDeactivate) return;
          await deactivate.mutateAsync(toDeactivate.id);
          toast("Template deactivated");
          setToDeactivate(null);
        }}
      />
    </div>
  );
}
