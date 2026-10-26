import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate, useSearchParams } from "react-router-dom";
import { orgsApi } from "@/api/orgs";
import { useAuth } from "@/lib/auth";
import { FormField } from "@/components/FormField";
import { Button, ErrorBanner, Input, useToast } from "@/components/ui";

const schema = z.object({ token: z.string().min(10, "Paste the invitation token") });
type FormValues = z.infer<typeof schema>;

export function AcceptInvite() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { refreshUser } = useAuth();
  const [serverError, setServerError] = useState<unknown>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { token: params.get("token") ?? "" } });

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      const org = await orgsApi.acceptInvitation(values.token);
      await refreshUser();
      toast(`Joined ${org.name}`);
      navigate("/workspaces");
    } catch (err) {
      setServerError(err);
    }
  };

  return (
    <div className="mx-auto mt-16 max-w-sm">
      <div className="card p-6">
        <h1 className="mb-1 text-xl font-semibold">Accept invitation</h1>
        <p className="mb-5 text-sm text-slate-500">Paste the token from your invitation email.</p>
        <ErrorBanner error={serverError} />
        <form className="mt-4" onSubmit={handleSubmit(onSubmit)} noValidate>
          <FormField label="Invitation token" htmlFor="token" error={errors.token?.message}>
            <Input id="token" {...register("token")} />
          </FormField>
          <Button type="submit" loading={isSubmitting} className="w-full">
            Accept invitation
          </Button>
        </form>
      </div>
    </div>
  );
}
