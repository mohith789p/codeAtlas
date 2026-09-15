/**
 * CodeAtlas API Client
 * Thin fetch wrapper — no fake data, no mocking.
 * All API errors are surfaced honestly to callers.
 */

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api';

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public body?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    let body: unknown;
    try { body = await res.json(); } catch { /* ignore */ }
    const detail = (body as { detail?: unknown })?.detail;
    const responseMessage = (body as { message?: unknown })?.message;
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((item) => {
            if (typeof item === 'string') return item;
            if (item && typeof item === 'object' && 'msg' in item) {
              return String((item as { msg: unknown }).msg);
            }
            return String(item);
          }).join(', ')
          : typeof responseMessage === 'string'
            ? responseMessage
            : `HTTP ${res.status}`;
    throw new ApiError(res.status, message, body);
  }

  if (res.status === 204) return undefined as unknown as T;
  return res.json() as Promise<T>;
}

export const get = <T>(path: string, opts?: RequestInit) =>
  request<T>(path, { method: 'GET', ...opts });

export const post = <T>(path: string, body?: unknown, opts?: RequestInit) =>
  request<T>(path, {
    method: 'POST',
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    ...opts,
  });

export const del = <T>(path: string, opts?: RequestInit) =>
  request<T>(path, { method: 'DELETE', ...opts });
