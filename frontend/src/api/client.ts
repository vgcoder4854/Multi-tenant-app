// The single HTTP gateway to the backend.
// - adds the Authorization header
// - parses the standard error JSON into ApiError(status, code, message)
// - logs the user out on 401

const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  code: string;
  errors?: unknown[];

  constructor(status: number, code: string, message: string, errors?: unknown[]) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.errors = errors;
  }
}

// --- token + 401 handling, wired up by the AuthProvider ---
let accessToken: string | null = sessionStorage.getItem("mta_token");
let onUnauthorized: (() => void) | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
  if (token) sessionStorage.setItem("mta_token", token);
  else sessionStorage.removeItem("mta_token");
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler;
}

type Query = Record<string, string | number | boolean | undefined | null>;

function buildUrl(path: string, query?: Query): string {
  const url = new URL(BASE_URL + path);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

async function request<T>(
  method: string,
  path: string,
  options: { body?: unknown; query?: Query } = {},
): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;

  const response = await fetch(buildUrl(path, options.query), {
    method,
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  if (response.status === 401 && onUnauthorized) onUnauthorized();

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const code = data?.code ?? "ERROR";
    const message = data?.detail ?? response.statusText;
    throw new ApiError(response.status, code, message, data?.errors);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string, query?: Query) => request<T>("GET", path, { query }),
  post: <T>(path: string, body?: unknown, query?: Query) => request<T>("POST", path, { body, query }),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, { body }),
  del: <T>(path: string) => request<T>("DELETE", path),
};

// Raw CSV download (used by the dashboard export button).
export async function downloadCsv(path: string, filename: string, query?: Query): Promise<void> {
  const headers: Record<string, string> = {};
  if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;
  const response = await fetch(buildUrl(path, query), { headers });
  if (!response.ok) throw new ApiError(response.status, "EXPORT_FAILED", "Export failed");
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
