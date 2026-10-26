import { Link } from "react-router-dom";
import { useMyRequests } from "@/hooks/useWorkflows";
import { Button, Card, EmptyState, ErrorBanner, Spinner, StatusBadge, Table } from "@/components/ui";

export function MyRequests() {
  const { data, isLoading, error } = useMyRequests();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">My requests</h1>
        <Link to="/requests/new">
          <Button>New request</Button>
        </Link>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner className="h-6 w-6 text-brand-600" />
        </div>
      ) : error ? (
        <ErrorBanner error={error} />
      ) : data && data.length > 0 ? (
        <Card>
          <Table headers={["Title", "Template", "Step", "Status", "Submitted"]}>
            {data.map((r) => (
              <tr key={r.id} className="hover:bg-slate-50">
                <td className="px-3 py-2">
                  <Link to={`/requests/${r.id}`} className="font-medium text-brand-700 hover:underline">
                    {r.title}
                  </Link>
                </td>
                <td className="px-3 py-2 text-slate-500">{r.template_name}</td>
                <td className="px-3 py-2 text-slate-500">{r.current_step_order}</td>
                <td className="px-3 py-2">
                  <StatusBadge value={r.status} />
                </td>
                <td className="px-3 py-2 text-slate-500">{new Date(r.submitted_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </Table>
        </Card>
      ) : (
        <Card>
          <EmptyState title="You have not submitted any requests" />
        </Card>
      )}
    </div>
  );
}
