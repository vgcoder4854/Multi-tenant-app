import { useState } from "react";
import { usePlatformOrganizations, usePlatformStats, useSetOrgStatus } from "@/hooks/useAdmin";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import {
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Input,
  Pagination,
  Spinner,
  StatusBadge,
  Table,
  useToast,
} from "@/components/ui";
import type { Organization } from "@/types";

export function PlatformAdmin() {
  const [name, setName] = useState("");
  const [page, setPage] = useState(1);
  const { data, isLoading, error } = usePlatformOrganizations({ name: name || undefined, page, page_size: 20 });
  const stats = usePlatformStats();
  const setStatus = useSetOrgStatus();
  const toast = useToast();
  const [target, setTarget] = useState<Organization | null>(null);

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold">Platform administration</h1>

      {stats.data && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
          {Object.entries(stats.data).map(([k, v]) => (
            <Card key={k}>
              <p className="text-xs text-slate-500">{k.replace(/_/g, " ")}</p>
              <p className="text-2xl font-semibold">{v}</p>
            </Card>
          ))}
        </div>
      )}

      <Input placeholder="Search organizations by name…" value={name} onChange={(e) => { setName(e.target.value); setPage(1); }} />

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner className="h-6 w-6 text-brand-600" />
        </div>
      ) : error ? (
        <ErrorBanner error={error} />
      ) : data && data.items.length > 0 ? (
        <Card>
          <Table headers={["Name", "Slug", "Status", "Created", ""]}>
            {data.items.map((o) => (
              <tr key={o.id}>
                <td className="px-3 py-2 font-medium">{o.name}</td>
                <td className="px-3 py-2 text-slate-500">{o.slug}</td>
                <td className="px-3 py-2">
                  <StatusBadge value={o.status} />
                </td>
                <td className="px-3 py-2 text-slate-500">{new Date(o.created_at).toLocaleDateString()}</td>
                <td className="px-3 py-2 text-right">
                  <Button variant={o.status === "active" ? "danger" : "secondary"} onClick={() => setTarget(o)}>
                    {o.status === "active" ? "Suspend" : "Activate"}
                  </Button>
                </td>
              </tr>
            ))}
          </Table>
          <Pagination page={data.page} pageSize={data.page_size} total={data.total} onChange={setPage} />
        </Card>
      ) : (
        <Card>
          <EmptyState title="No organizations" />
        </Card>
      )}

      <ConfirmDialog
        open={Boolean(target)}
        title={target?.status === "active" ? "Suspend organization" : "Activate organization"}
        message={
          target?.status === "active"
            ? `Suspend "${target?.name}"? All its tenant endpoints will be blocked.`
            : `Activate "${target?.name}"? Its members will regain access.`
        }
        confirmLabel={target?.status === "active" ? "Suspend" : "Activate"}
        danger={target?.status === "active"}
        loading={setStatus.isPending}
        onCancel={() => setTarget(null)}
        onConfirm={async () => {
          if (!target) return;
          await setStatus.mutateAsync({ id: target.id, status: target.status === "active" ? "suspended" : "active" });
          toast("Status updated");
          setTarget(null);
        }}
      />
    </div>
  );
}
