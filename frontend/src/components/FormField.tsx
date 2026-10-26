import type { ReactNode } from "react";

export function FormField({
  label,
  error,
  htmlFor,
  children,
  hint,
}: {
  label: string;
  error?: string;
  htmlFor?: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <div className="mb-4">
      <label className="label" htmlFor={htmlFor}>
        {label}
      </label>
      {children}
      {hint && !error && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
      {error && (
        <p role="alert" className="mt-1 text-xs text-red-600">
          {error}
        </p>
      )}
    </div>
  );
}
