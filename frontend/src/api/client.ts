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
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });
  } catch (networkError) {
    console.error(`[API Network Error] ${options?.method || 'GET'} ${path}:`, networkError);
    throw networkError;
  }

  if (!res.ok) {
    let body: unknown;
    try { body = await res.json(); } catch { /* ignore */ }
    const detail = (body as { detail?: unknown })?.detail;
    const responseMessage = (body as { message?: unknown })?.message;
    const rawMessage =
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
            : undefined;

    // Log the error with request and response context
    console.error(`[API Error] ${options?.method || 'GET'} ${path} returned status ${res.status}:`, {
      status: res.status,
      statusText: res.statusText,
      detail: rawMessage,
      body,
    });

    const isGenericServerError = rawMessage === 'Internal Server Error' || !rawMessage;
    const message = (!isGenericServerError ? rawMessage : undefined) || (
      res.status >= 500
        ? 'A server error occurred. Please try again later.'
        : res.status === 404
          ? 'The requested resource was not found.'
          : res.status === 403 || res.status === 401
            ? 'You do not have permission to perform this action.'
            : `Request failed with status ${res.status}`
    );

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
