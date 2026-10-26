import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate, Link } from "react-router-dom";
import { orgsApi } from "@/api/orgs";
import { useAuth } from "@/lib/auth";
import { FormField } from "@/components/FormField";
import { Button, Card, ErrorBanner, Input } from "@/components/ui";

const schema = z.object({ name: z.string().min(2, "Organization name is required") });
type FormValues = z.infer<typeof schema>;

export function WorkspacePicker() {
  const { user, switchOrganization, refreshUser, logout } = useAuth();
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<unknown>(null);
  const [creating, setCreating] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const choose = async (orgId: string) => {
    await switchOrganization(orgId);
    navigate("/dashboard");
  };

  const createOrg = async (values: FormValues) => {
    setServerError(null);
    try {
      const org = await orgsApi.create({ name: values.name });
      await refreshUser();
      await choose(org.id);
    } catch (err) {
      setServerError(err);
    }
  };

  const memberships = user?.memberships ?? [];

  return (
    <div className="mx-auto mt-16 max-w-2xl px-4">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Choose a workspace</h1>
        <Button variant="ghost" onClick={logout}>
          Log out
        </Button>
      </div>

      {memberships.length === 0 ? (
        <p className="mb-4 text-sm text-slate-500">
          You are not a member of any organization yet. Create one to get started, or accept an invitation.
        </p>
      ) : (
        <div className="mb-6 grid gap-3 sm:grid-cols-2">
          {memberships.map((m) => (
            <button
              key={m.org_id}
              onClick={() => choose(m.org_id)}
              className="card p-4 text-left transition hover:border-brand-500 hover:shadow"
            >
              <p className="font-medium">{m.org_name}</p>
              <p className="text-xs text-slate-500">{m.role.replace(/_/g, " ")}</p>
            </button>
          ))}
        </div>
      )}

      <Card>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-medium">Create a new organization</h2>
          <Button variant="secondary" onClick={() => setCreating((v) => !v)}>
            {creating ? "Hide" : "Create"}
          </Button>
        </div>
        {creating && (
          <>
            <ErrorBanner error={serverError} />
            <form className="mt-3" onSubmit={handleSubmit(createOrg)} noValidate>
              <FormField label="Organization name" htmlFor="name" error={errors.name?.message}>
                <Input id="name" placeholder="Acme Corp" {...register("name")} />
              </FormField>
              <Button type="submit" loading={isSubmitting}>
                Create organization
              </Button>
            </form>
          </>
        )}
      </Card>

      <Card className="mt-4">
        <h2 className="mb-1 font-medium">Have an invitation?</h2>
        <p className="mb-3 text-sm text-slate-500">
          Been invited to an existing organization? Accept it with the token from your invitation email.
        </p>
        <Link to="/accept-invite">
          <Button variant="secondary">Accept an invitation</Button>
        </Link>
      </Card>

      {user?.is_platform_admin && (
        <Card className="mt-4">
          <h2 className="mb-1 font-medium">Platform administration</h2>
          <p className="mb-3 text-sm text-slate-500">
            You are a platform administrator. Manage organizations across the whole platform.
          </p>
          <Link to="/platform">
            <Button variant="secondary">Open Platform Admin</Button>
          </Link>
        </Card>
      )}
    </div>
  );
}
