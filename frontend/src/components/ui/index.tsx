import {
  createContext,
  forwardRef,
  useCallback,
  useContext,
  useState,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";
import { ApiError } from "@/api/client";

export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

/* ----------------------------- Spinner ----------------------------- */
export function Spinner({ className = "" }: { className?: string }) {
  return (
    <span
      role="status"
      aria-label="loading"
      className={cn(
        "inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent",
        className,
      )}
    />
  );
}

/* ----------------------------- Button ------------------------------ */
type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  loading?: boolean;
};

export function Button({ variant = "primary", loading, className, children, disabled, ...rest }: ButtonProps) {
  const styles = {
    primary: "btn-primary",
    secondary: "btn-secondary",
    danger: "btn-danger",
    ghost: "btn text-slate-600 hover:bg-slate-100",
  }[variant];
  return (
    <button className={cn(styles, className)} disabled={disabled || loading} {...rest}>
      {loading && <Spinner className="h-3 w-3" />}
      {children}
    </button>
  );
}

/* --------------------------- Inputs -------------------------------- */
export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...rest }, ref) {
    return <input ref={ref} className={cn("input", className)} {...rest} />;
  },
);

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function Textarea({ className, ...rest }, ref) {
    return <textarea ref={ref} className={cn("input", className)} {...rest} />;
  },
);

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className, children, ...rest }, ref) {
    return (
      <select ref={ref} className={cn("input", className)} {...rest}>
        {children}
      </select>
    );
  },
);

/* ----------------------------- Card -------------------------------- */
export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("card p-5", className)}>{children}</div>;
}

/* ----------------------------- Badge ------------------------------- */
export function Badge({ children, tone = "slate" }: { children: ReactNode; tone?: string }) {
  const tones: Record<string, string> = {
    slate: "bg-slate-100 text-slate-700",
    green: "bg-emerald-100 text-emerald-700",
    amber: "bg-amber-100 text-amber-800",
    red: "bg-red-100 text-red-700",
    blue: "bg-blue-100 text-blue-700",
    purple: "bg-purple-100 text-purple-700",
  };
  return (
    <span className={cn("inline-flex rounded-full px-2 py-0.5 text-xs font-medium", tones[tone] ?? tones.slate)}>
      {children}
    </span>
  );
}

const STATUS_TONE: Record<string, string> = {
  todo: "slate",
  in_progress: "blue",
  blocked: "red",
  completed: "green",
  active: "green",
  archived: "slate",
  pending: "amber",
  approved: "green",
  rejected: "red",
  cancelled: "slate",
  suspended: "red",
  accepted: "green",
  revoked: "slate",
  expired: "slate",
  removed: "slate",
};
const PRIORITY_TONE: Record<string, string> = {
  low: "slate",
  medium: "blue",
  high: "amber",
  critical: "red",
};

export function StatusBadge({ value }: { value: string }) {
  return <Badge tone={STATUS_TONE[value] ?? "slate"}>{value.replace(/_/g, " ")}</Badge>;
}

export function PriorityBadge({ value }: { value: string }) {
  return <Badge tone={PRIORITY_TONE[value] ?? "slate"}>{value}</Badge>;
}

/* ----------------------------- Table ------------------------------- */
export function Table({ headers, children }: { headers: string[]; children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
          <tr>
            {headers.map((h) => (
              <th key={h} className="px-3 py-2 font-medium">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">{children}</tbody>
      </table>
    </div>
  );
}

/* --------------------------- Pagination ---------------------------- */
export function Pagination({
  page,
  pageSize,
  total,
  onChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  onChange: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="flex items-center justify-between pt-3 text-sm text-slate-600">
      <span>
        Page {page} of {pages} · {total} items
      </span>
      <div className="flex gap-2">
        <Button variant="secondary" disabled={page <= 1} onClick={() => onChange(page - 1)}>
          Previous
        </Button>
        <Button variant="secondary" disabled={page >= pages} onClick={() => onChange(page + 1)}>
          Next
        </Button>
      </div>
    </div>
  );
}

/* -------------------------- Empty / Error -------------------------- */
export function EmptyState({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 py-10 text-center">
      <p className="font-medium text-slate-700">{title}</p>
      {description && <p className="text-sm text-slate-500">{description}</p>}
      {action}
    </div>
  );
}

export function ErrorBanner({ error }: { error: unknown }) {
  if (!error) return null;
  const message =
    error instanceof ApiError ? error.message : error instanceof Error ? error.message : String(error);
  const code = error instanceof ApiError ? error.code : undefined;
  return (
    <div role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
      {message}
      {code && <span className="ml-2 text-xs text-red-500">({code})</span>}
    </div>
  );
}

/* ----------------------------- Modal ------------------------------- */
export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div role="dialog" aria-modal="true" aria-label={title} className="w-full max-w-lg rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          <h2 className="font-semibold">{title}</h2>
          <button aria-label="Close" onClick={onClose} className="text-slate-400 hover:text-slate-700">
            ✕
          </button>
        </div>
        <div className="max-h-[70vh] overflow-y-auto px-5 py-4">{children}</div>
        {footer && <div className="flex justify-end gap-2 border-t border-slate-200 px-5 py-3">{footer}</div>}
      </div>
    </div>
  );
}

/* ----------------------------- Toast ------------------------------- */
interface ToastItem {
  id: number;
  message: string;
  tone: "success" | "error";
}
const ToastContext = createContext<(message: string, tone?: "success" | "error") => void>(() => {});

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const push = useCallback((message: string, tone: "success" | "error" = "success") => {
    const id = Date.now() + Math.random();
    setItems((prev) => [...prev, { id, message, tone }]);
    setTimeout(() => setItems((prev) => prev.filter((i) => i.id !== id)), 4000);
  }, []);
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="fixed bottom-4 right-4 z-[60] flex flex-col gap-2">
        {items.map((i) => (
          <div
            key={i.id}
            role="status"
            className={cn(
              "rounded-md px-4 py-2 text-sm text-white shadow-lg",
              i.tone === "success" ? "bg-slate-800" : "bg-red-600",
            )}
          >
            {i.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
