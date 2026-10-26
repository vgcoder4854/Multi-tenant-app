import { Link } from "react-router-dom";

export function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3">
      <h1 className="text-3xl font-semibold">404</h1>
      <p className="text-slate-500">This page does not exist.</p>
      <Link to="/dashboard" className="text-brand-600 hover:underline">
        Back to dashboard
      </Link>
    </div>
  );
}
