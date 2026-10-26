import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useSubmitRequest, useWorkflowTemplates } from "@/hooks/useWorkflows";
import { FormField } from "@/components/FormField";
import { Button, Card, ErrorBanner, Input, Select, Textarea, useToast } from "@/components/ui";

const schema = z.object({
  template_id: z.string().min(1, "Choose a template"),
  title: z.string().min(1, "Title is required"),
  notes: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export function NewRequest() {
  const { data: templates } = useWorkflowTemplates();
  const submit = useSubmitRequest();
  const navigate = useNavigate();
  const toast = useToast();
  const [serverError, setServerError] = useState<unknown>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      await submit.mutateAsync({
        template_id: values.template_id,
        title: values.title,
        details: values.notes ? { notes: values.notes } : {},
      });
      toast("Request submitted");
      navigate("/requests/mine");
    } catch (err) {
      setServerError(err);
    }
  };

  const activeTemplates = (templates ?? []).filter((t) => t.is_active);

  return (
    <div className="mx-auto max-w-lg">
      <h1 className="mb-4 text-xl font-semibold">New approval request</h1>
      <Card>
        <ErrorBanner error={serverError} />
        <form className="mt-3" onSubmit={handleSubmit(onSubmit)} noValidate>
          <FormField label="Template" htmlFor="template_id" error={errors.template_id?.message}>
            <Select id="template_id" {...register("template_id")}>
              <option value="">Select a template…</option>
              {activeTemplates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} ({t.steps.length} step{t.steps.length > 1 ? "s" : ""})
                </option>
              ))}
            </Select>
          </FormField>
          <FormField label="Title" htmlFor="title" error={errors.title?.message}>
            <Input id="title" {...register("title")} />
          </FormField>
          <FormField label="Details / notes" htmlFor="notes">
            <Textarea id="notes" rows={4} {...register("notes")} />
          </FormField>
          <Button type="submit" loading={isSubmitting}>
            Submit request
          </Button>
        </form>
      </Card>
    </div>
  );
}
