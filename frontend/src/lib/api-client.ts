import { supabase } from '@/lib/supabase/client';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? '';

/**
 * Core fetch wrapper that attaches the Supabase JWT bearer token
 * to every outgoing API request.
 */
async function apiCall(
  endpoint: string,
  options: RequestInit = {},
): Promise<Response> {
  const { data: { session } } = await supabase.auth.getSession();

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  };

  if (session?.access_token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${session.access_token}`;
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const body = await response.text().catch(() => '');
    throw new ApiError(response.status, response.statusText, body);
  }

  return response;
}

/**
 * Typed API error with status code for downstream handling.
 */
export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public body: string,
  ) {
    super(`API ${status}: ${statusText}`);
    this.name = 'ApiError';
  }
}

// ── Convenience helpers ───────────────────────────────────────

export async function apiGet<T = unknown>(endpoint: string): Promise<T> {
  const res = await apiCall(endpoint, { method: 'GET' });
  return res.json() as Promise<T>;
}

export async function apiPost<T = unknown>(
  endpoint: string,
  data?: unknown,
): Promise<T> {
  const res = await apiCall(endpoint, {
    method: 'POST',
    body: data !== undefined ? JSON.stringify(data) : undefined,
  });
  return res.json() as Promise<T>;
}

export async function apiPut<T = unknown>(
  endpoint: string,
  data?: unknown,
): Promise<T> {
  const res = await apiCall(endpoint, {
    method: 'PUT',
    body: data !== undefined ? JSON.stringify(data) : undefined,
  });
  return res.json() as Promise<T>;
}

export async function apiDelete<T = unknown>(endpoint: string): Promise<T> {
  const res = await apiCall(endpoint, { method: 'DELETE' });
  return res.json() as Promise<T>;
}

export { apiCall };
