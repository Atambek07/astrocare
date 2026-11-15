'use client';

/** Base URL of the unified AstroCare backend service. */
const BACKEND_HTTP_BASE_URL =
  process.env.NEXT_PUBLIC_BACKEND_HTTP_URL?.replace(/\/+$/, '') || 'http://localhost:8765';

/** Convert a backend route such as `/simulation/status` into an absolute backend URL. */
export function backendUrl(path: string): string {
  if (!path.startsWith('/')) throw new Error('backend route must start with /');
  return `${BACKEND_HTTP_BASE_URL}${path}`;
}

export interface BackendRequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: unknown;
  signal?: AbortSignal;
}

/** Fetch a backend JSON resource and return a descriptive error for failures. */
export async function fetchBackendJson<T>(path: string, options: BackendRequestOptions = {}): Promise<T> {
  const response = await fetch(backendUrl(path), {
    method: options.method ?? 'GET',
    cache: 'no-store',
    signal: options.signal,
    headers: options.body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload && typeof payload === 'object' && 'error' in payload
      ? String((payload as { error: unknown }).error)
      : `HTTP ${response.status}`;
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export { BACKEND_HTTP_BASE_URL };
