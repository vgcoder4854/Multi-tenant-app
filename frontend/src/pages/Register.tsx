import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { FormField } from "@/components/FormField";
import { Button, ErrorBanner, Input } from "@/components/ui";

const schema = z.object({
  full_name: z.string().min(1, "Your name is required"),
  email: z.string().email("Enter a valid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});
type FormValues = z.infer<typeof schema>;

export function Register() {
  const { register: registerUser } = useAuth();
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<unknown>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      await registerUser(values.email, values.password, values.full_name);
      navigate("/workspaces");
    } catch (err) {
      setServerError(err);
    }
  };

  return (
    <div className="mx-auto mt-16 max-w-sm">
      <div className="card p-6">
        <h1 className="mb-5 text-xl font-semibold">Create your account</h1>
        <ErrorBanner error={serverError} />
        <form className="mt-4" onSubmit={handleSubmit(onSubmit)} noValidate>
          <FormField label="Full name" htmlFor="full_name" error={errors.full_name?.message}>
            <Input id="full_name" {...register("full_name")} />
          </FormField>
          <FormField label="Email" htmlFor="email" error={errors.email?.message}>
            <Input id="email" type="email" autoComplete="email" {...register("email")} />
          </FormField>
          <FormField
            label="Password"
            htmlFor="password"
            error={errors.password?.message}
            hint="At least 8 characters"
          >
            <Input id="password" type="password" autoComplete="new-password" {...register("password")} />
          </FormField>
          <Button type="submit" loading={isSubmitting} className="w-full">
            Register
          </Button>
        </form>
        <p className="mt-4 text-center text-sm text-slate-500">
          Already have an account?{" "}
          <Link to="/login" className="text-brand-600 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
