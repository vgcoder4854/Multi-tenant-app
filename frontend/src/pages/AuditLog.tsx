import { useState } from "react";
import type { AuditFilters } from "@/api/misc";
import { useAuditLogs } from "@/hooks/useAdmin";
import { Card, EmptyState, ErrorBanner, Input, Pagination, Spinner, Table } from "@/components/ui";

export function AuditLog() {
  const [filters, setFilters] = useState<AuditFilters>({ page: 1, page_size: 20 });
  const { data, isLoading, error } = useAuditLogs(filters);

  const set = (patch: Partial<AuditFilters>) => setFilters((f) => ({ ...f, ...patch, page: 1 }));

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Audit log</h1>

      <Card className="grid grid-cols-1 gap-3 sm:grid-cols-4">
        <Input
          placeholder="Action (e.g. task.created)"
          aria-label="Action"
          value={filters.action ?? ""}
          onChange={(e) => set({ action: e.target.value || undefined })}
        />
        <Input
          placeholder="Resource type (e.g. project)"
          aria-label="Resource type"
          value={filters.resource_type ?? ""}
          onChange={(e) => set({ resource_type: e.target.value || undefined })}
        />
        <Input
          type="date"
          aria-label="From"
          value={filters.date_from?.slice(0, 10) ?? ""}
          onChange={(e) => set({ date_from: e.target.value ? `${e.target.value}T00:00:00Z` : undefined })}
        />
        <Input
          type="date"
          aria-label="To"
          value={filters.date_to?.slice(0, 10) ?? ""}
          onChange={(e) => set({ date_to: e.target.value ? `${e.target.value}T23:59:59Z` : undefined })}
        />
      </Card>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner className="h-6 w-6 text-brand-600" />
        </div>
      ) : error ? (
        <ErrorBanner error={error} />
      ) : data && data.items.length > 0 ? (
        <Card>
          <Table headers={["When", "Action", "Resource", "Actor", "Metadata"]}>
            {data.items.map((row) => (
              <tr key={row.id}>
                <td className="whitespace-nowrap px-3 py-2 text-slate-500">
                  {new Date(row.created_at).toLocaleString()}
                </td>
                <td className="px-3 py-2 font-medium">{row.action}</td>
                <td className="px-3 py-2 text-slate-500">{row.resource_type ?? "—"}</td>
                <td className="px-3 py-2 text-slate-500">{row.actor_id?.slice(0, 8) ?? "system"}</td>
                <td className="px-3 py-2 font-mono text-xs text-slate-500">
                  {Object.keys(row.metadata ?? {}).length ? JSON.stringify(row.metadata) : "—"}
                </td>
              </tr>
            ))}
          </Table>
          <Pagination
            page={data.page}
            pageSize={data.page_size}
            total={data.total}
            onChange={(page) => setFilters((f) => ({ ...f, page }))}
          />
        </Card>
      ) : (
        <Card>
          <EmptyState title="No audit entries" />
        </Card>
      )}
    </div>
  );
}
