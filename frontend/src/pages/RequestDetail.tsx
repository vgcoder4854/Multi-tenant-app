import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useApprovalRequest, useCancelRequest, useDecideRequest } from "@/hooks/useWorkflows";
import { useAuth } from "@/lib/auth";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Button, Card, ErrorBanner, Spinner, StatusBadge, Textarea, useToast } from "@/components/ui";

export function RequestDetail() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, error } = useApprovalRequest(id);
  const { user } = useAuth();
  const decide = useDecideRequest(id ?? "");
  const cancel = useCancelRequest();
  const toast = useToast();
  const [comment, setComment] = useState("");
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [actionError, setActionError] = useState<unknown>(null);

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner className="h-6 w-6 text-brand-600" />
      </div>
    );
  }
  if (error || !data) return <ErrorBanner error={error ?? "Request not found"} />;

  const isRequester = user?.id === data.requester_id;

  const act = async (decision: "approved" | "rejected") => {
    setActionError(null);
    try {
      await decide.mutateAsync({ decision, comment: comment || undefined });
      toast(`Request ${decision}`);
      setComment("");
    } catch (err) {
      setActionError(err);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div>
        <Link to="/requests/mine" className="text-sm text-brand-600 hover:underline">
          ← Requests
        </Link>
        <div className="mt-1 flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-semibold">{data.title}</h1>
          <StatusBadge value={data.status} />
        </div>
        <p className="mt-1 text-sm text-slate-500">
          {data.template_name} · requested by {data.requester_name} · {new Date(data.submitted_at).toLocaleString()}
        </p>
      </div>

      {/* Step progress */}
      <Card>
        <h2 className="mb-3 font-medium">Steps</h2>
        <ol className="space-y-2">
          {data.steps.map((s) => {
            const done = data.decisions.some((d) => d.step_order === s.step_order);
            const current = data.status === "pending" && s.step_order === data.current_step_order;
            return (
              <li key={s.id} className="flex items-center gap-3 text-sm">
                <span
                  className={
                    "flex h-6 w-6 items-center justify-center rounded-full text-xs " +
                    (done ? "bg-emerald-100 text-emerald-700" : current ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-500")
                  }
                >
                  {s.step_order}
                </span>
                <span className="font-medium">{s.name}</span>
                <span className="text-slate-500">
                  {s.approver_type === "role" ? `role: ${s.approver_role}` : "specific user"}
                </span>
                {current && <StatusBadge value="pending" />}
              </li>
            );
          })}
        </ol>
      </Card>

      {Object.keys(data.details ?? {}).length > 0 && (
        <Card>
          <h2 className="mb-2 font-medium">Details</h2>
          <dl className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
            {Object.entries(data.details).map(([k, v]) => (
              <div key={k}>
                <dt className="text-slate-500">{k}</dt>
                <dd>{String(v)}</dd>
              </div>
            ))}
          </dl>
        </Card>
      )}

      {/* Decision history */}
      <Card>
        <h2 className="mb-3 font-medium">Approval history</h2>
        {data.decisions.length === 0 ? (
          <p className="text-sm text-slate-500">No decisions yet.</p>
        ) : (
          <ol className="space-y-3 border-l border-slate-200 pl-4">
            {data.decisions.map((d) => (
              <li key={d.id} className="text-sm">
                <div className="flex items-center gap-2">
                  <StatusBadge value={d.decision} />
                  <span className="text-slate-500">step {d.step_order}</span>
                  <span className="text-slate-400">{new Date(d.decided_at).toLocaleString()}</span>
                </div>
                {d.comment && <p className="mt-1 text-slate-600">“{d.comment}”</p>}
              </li>
            ))}
          </ol>
        )}
      </Card>

      {/* Actions */}
      <ErrorBanner error={actionError} />
      {data.can_decide && (
        <Card>
          <h2 className="mb-2 font-medium">Your decision</h2>
          <Textarea rows={2} placeholder="Comment (required to reject)" value={comment} onChange={(e) => setComment(e.target.value)} />
          <div className="mt-3 flex gap-2">
            <Button onClick={() => act("approved")} loading={decide.isPending}>
              Approve
            </Button>
            <Button variant="danger" onClick={() => act("rejected")} loading={decide.isPending}>
              Reject
            </Button>
          </div>
        </Card>
      )}
      {isRequester && data.status === "pending" && (
        <Button variant="secondary" onClick={() => setConfirmCancel(true)}>
          Cancel request
        </Button>
      )}

      <ConfirmDialog
        open={confirmCancel}
        title="Cancel request"
        message="Cancel this pending request? This cannot be undone."
        confirmLabel="Cancel request"
        danger
        loading={cancel.isPending}
        onCancel={() => setConfirmCancel(false)}
        onConfirm={async () => {
          await cancel.mutateAsync(data.id);
          toast("Request cancelled");
          setConfirmCancel(false);
        }}
      />
    </div>
  );
}
