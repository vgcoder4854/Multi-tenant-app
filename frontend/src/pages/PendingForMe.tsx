import { useState } from "react";
import { Link } from "react-router-dom";
import { useDecideRequest, usePendingForMe } from "@/hooks/useWorkflows";
import { ApiError } from "@/api/client";
import { Button, Card, EmptyState, ErrorBanner, Spinner, Textarea, useToast } from "@/components/ui";

function DecideRow({ id, title, templateName, step }: { id: string; title: string; templateName: string; step: number }) {
  const decide = useDecideRequest(id);
  const toast = useToast();
  const [comment, setComment] = useState("");
  const [error, setError] = useState<unknown>(null);

  const act = async (decision: "approved" | "rejected") => {
    setError(null);
    if (decision === "rejected" && !comment.trim()) {
      setError(new ApiError(422, "VALIDATION_ERROR", "A comment is required when rejecting"));
      return;
    }
    try {
      await decide.mutateAsync({ decision, comment: comment || undefined });
      toast(`Request ${decision}`);
    } catch (err) {
      setError(err);
      if (err instanceof ApiError && err.status === 409) toast("Already decided — refreshing", "error");
    }
  };

  return (
    <div className="border-b border-slate-100 py-4 last:border-0">
      <div className="flex items-center justify-between">
        <Link to={`/requests/${id}`} className="font-medium text-brand-700 hover:underline">
          {title}
        </Link>
        <span className="text-xs text-slate-500">
          {templateName} · step {step}
        </span>
      </div>
      <ErrorBanner error={error} />
      <Textarea
        className="my-2"
        rows={2}
        placeholder="Comment (required to reject)"
        value={comment}
        onChange={(e) => setComment(e.target.value)}
      />
      <div className="flex gap-2">
        <Button onClick={() => act("approved")} loading={decide.isPending}>
          Approve
        </Button>
        <Button variant="danger" onClick={() => act("rejected")} loading={decide.isPending}>
          Reject
        </Button>
      </div>
    </div>
  );
}

export function PendingForMe() {
  const { data, isLoading, error } = usePendingForMe();

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Pending for me</h1>
      {isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner className="h-6 w-6 text-brand-600" />
        </div>
      ) : error ? (
        <ErrorBanner error={error} />
      ) : data && data.length > 0 ? (
        <Card>
          {data.map((r) => (
            <DecideRow key={r.id} id={r.id} title={r.title} templateName={r.template_name} step={r.current_step_order} />
          ))}
        </Card>
      ) : (
        <Card>
          <EmptyState title="Nothing awaiting your approval" />
        </Card>
      )}
    </div>
  );
}
