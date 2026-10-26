import { useEffect, useState } from "react";
import type { TaskFilters } from "@/api/tasks";
import { Input, Select } from "@/components/ui";
import type { Member, Project, TaskPriority, TaskStatus } from "@/types";

export function useDebounced<T>(value: T, delay = 350): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

const STATUSES: TaskStatus[] = ["todo", "in_progress", "blocked", "completed"];
const PRIORITIES: TaskPriority[] = ["low", "medium", "high", "critical"];

export function FilterBar({
  value,
  onChange,
  projects = [],
  members = [],
}: {
  value: TaskFilters;
  onChange: (next: TaskFilters) => void;
  projects?: Project[];
  members?: Member[];
}) {
  const [search, setSearch] = useState(value.search ?? "");
  const debouncedSearch = useDebounced(search);

  useEffect(() => {
    if ((value.search ?? "") !== debouncedSearch) {
      onChange({ ...value, search: debouncedSearch || undefined, page: 1 });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch]);

  const set = (patch: Partial<TaskFilters>) => onChange({ ...value, ...patch, page: 1 });

  return (
    <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
      <Input
        aria-label="Search tasks"
        placeholder="Search title or description…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      <Select aria-label="Project" value={value.project_id ?? ""} onChange={(e) => set({ project_id: e.target.value || undefined })}>
        <option value="">All projects</option>
        {projects.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </Select>
      <Select aria-label="Status" value={value.status ?? ""} onChange={(e) => set({ status: (e.target.value || undefined) as TaskStatus })}>
        <option value="">All statuses</option>
        {STATUSES.map((s) => (
          <option key={s} value={s}>
            {s.replace(/_/g, " ")}
          </option>
        ))}
      </Select>
      <Select aria-label="Priority" value={value.priority ?? ""} onChange={(e) => set({ priority: (e.target.value || undefined) as TaskPriority })}>
        <option value="">All priorities</option>
        {PRIORITIES.map((p) => (
          <option key={p} value={p}>
            {p}
          </option>
        ))}
      </Select>
      <Select aria-label="Assignee" value={value.assignee_id ?? ""} onChange={(e) => set({ assignee_id: e.target.value || undefined })}>
        <option value="">All assignees</option>
        {members.map((m) => (
          <option key={m.user_id} value={m.user_id}>
            {m.full_name}
          </option>
        ))}
      </Select>
    </div>
  );
}
