import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  useChangeMemberRole,
  useInvitations,
  useInviteMember,
  useMembers,
  useRemoveMember,
  useRevokeInvitation,
} from "@/hooks/useAdmin";
import { FormField } from "@/components/FormField";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import {
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Input,
  Select,
  Spinner,
  StatusBadge,
  Table,
  useToast,
} from "@/components/ui";
import type { Member, MemberRole } from "@/types";

const ROLES: MemberRole[] = ["org_admin", "manager", "employee"];

const schema = z.object({ email: z.string().email("Enter a valid email"), role: z.enum(["org_admin", "manager", "employee"]) });
type FormValues = z.infer<typeof schema>;

export function Members() {
  const members = useMembers();
  const invitations = useInvitations();
  const invite = useInviteMember();
  const revoke = useRevokeInvitation();
  const changeRole = useChangeMemberRole();
  const removeMember = useRemoveMember();
  const toast = useToast();
  const [serverError, setServerError] = useState<unknown>(null);
  const [toRemove, setToRemove] = useState<Member | null>(null);
  const [createdToken, setCreatedToken] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { role: "employee" } });

  const onInvite = async (values: FormValues) => {
    setServerError(null);
    try {
      const created = await invite.mutateAsync(values);
      setCreatedToken(created.token);
      toast("Invitation created");
      reset({ email: "", role: "employee" });
    } catch (err) {
      setServerError(err);
    }
  };

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold">Members & invitations</h1>

      <Card>
        <h2 className="mb-3 font-medium">Invite a member</h2>
        <ErrorBanner error={serverError} />
        {createdToken && (
          <div className="mb-3 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm">
            Invitation token (shown once):
            <code className="ml-1 break-all font-mono text-xs">{createdToken}</code>
          </div>
        )}
        <form className="flex flex-wrap items-end gap-3" onSubmit={handleSubmit(onInvite)} noValidate>
          <div className="min-w-56 flex-1">
            <FormField label="Email" htmlFor="email" error={errors.email?.message}>
              <Input id="email" type="email" {...register("email")} />
            </FormField>
          </div>
          <div className="w-40">
            <FormField label="Role" htmlFor="role">
              <Select id="role" {...register("role")}>
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </Select>
            </FormField>
          </div>
          <Button type="submit" loading={isSubmitting} className="mb-4">
            Send invite
          </Button>
        </form>
      </Card>

      <Card>
        <h2 className="mb-3 font-medium">Pending invitations</h2>
        {invitations.isLoading ? (
          <Spinner />
        ) : invitations.data && invitations.data.length > 0 ? (
          <Table headers={["Email", "Role", "Status", "Expires", ""]}>
            {invitations.data.map((inv) => (
              <tr key={inv.id}>
                <td className="px-3 py-2">{inv.email}</td>
                <td className="px-3 py-2">{inv.role}</td>
                <td className="px-3 py-2">
                  <StatusBadge value={inv.status} />
                </td>
                <td className="px-3 py-2 text-slate-500">{new Date(inv.expires_at).toLocaleDateString()}</td>
                <td className="px-3 py-2 text-right">
                  {inv.status === "pending" && (
                    <button
                      className="text-xs text-red-600 hover:underline"
                      onClick={async () => {
                        await revoke.mutateAsync(inv.id);
                        toast("Invitation revoked");
                      }}
                    >
                      Revoke
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </Table>
        ) : (
          <EmptyState title="No invitations" />
        )}
      </Card>

      <Card>
        <h2 className="mb-3 font-medium">Members</h2>
        {members.isLoading ? (
          <Spinner />
        ) : members.data && members.data.length > 0 ? (
          <Table headers={["Name", "Email", "Role", "Status", ""]}>
            {members.data.map((m) => (
              <tr key={m.user_id}>
                <td className="px-3 py-2">{m.full_name}</td>
                <td className="px-3 py-2 text-slate-500">{m.email}</td>
                <td className="px-3 py-2">
                  <Select
                    aria-label={`Role for ${m.full_name}`}
                    value={m.role}
                    disabled={m.status !== "active"}
                    onChange={async (e) => {
                      try {
                        await changeRole.mutateAsync({ userId: m.user_id, role: e.target.value as MemberRole });
                        toast("Role updated");
                      } catch (err) {
                        toast(err instanceof Error ? err.message : "Failed", "error");
                      }
                    }}
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </Select>
                </td>
                <td className="px-3 py-2">
                  <StatusBadge value={m.status} />
                </td>
                <td className="px-3 py-2 text-right">
                  {m.status === "active" && (
                    <button className="text-xs text-red-600 hover:underline" onClick={() => setToRemove(m)}>
                      Remove
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </Table>
        ) : (
          <EmptyState title="No members" />
        )}
      </Card>

      <ConfirmDialog
        open={Boolean(toRemove)}
        title="Remove member"
        message={`Remove ${toRemove?.full_name} from this organization?`}
        confirmLabel="Remove"
        danger
        loading={removeMember.isPending}
        onCancel={() => setToRemove(null)}
        onConfirm={async () => {
          if (!toRemove) return;
          try {
            await removeMember.mutateAsync(toRemove.user_id);
            toast("Member removed");
          } catch (err) {
            toast(err instanceof Error ? err.message : "Failed", "error");
          }
          setToRemove(null);
        }}
      />
    </div>
  );
}
