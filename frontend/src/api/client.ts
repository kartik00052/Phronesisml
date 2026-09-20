/**
 * API transport: single fetch entry point + error normalization.
 *
 * All domain API modules go through `apiRequest`. In demo mode the matching
 * module calls the in-memory handlers instead (see `src/mocks/handlers.ts`),
 * so the UI never bypasses this layer.
 */
import { ApiError, type ApiErrorPayload } from "@/types/api";
import { isDemoMode } from "@/mocks";

export const DEFAULT_BASE_URL = "http://localhost:8000/api/v1";

export function getBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL as string | undefined;
  return (configured ?? DEFAULT_BASE_URL).replace(/\/+$/, "");
}

export function buildUrl(path: string): string {
  return `${getBaseUrl()}${path.startsWith("/") ? path : `/${path}`}`;
}

/** Normalize any thrown value into an ApiError. */
export function toApiError(err: unknown, fallback = "Request failed."): ApiError {
  if (err instanceof ApiError) return err;
  if (err instanceof Error) return new ApiError(err.message);
  return new ApiError(fallback);
}

/** Extract the error envelope from a response body (nested or flat). */
function parsePayload(raw: unknown): ApiErrorPayload {
  if (!raw || typeof raw !== "object") return { error: "" };
  const obj = raw as Record<string, unknown>;
  const nested = obj["error"];
  if (nested && typeof nested === "object") {
    const inner = nested as Record<string, unknown>;
    return {
      error: typeof inner["message"] === "string" ? (inner["message"] as string) : "",
      error_type: typeof inner["code"] === "string" ? (inner["code"] as string) : undefined,
      message: typeof inner["message"] === "string" ? (inner["message"] as string) : undefined,
      context: inner["details"] as Record<string, string> | undefined,
    };
  }
  return {
    error: typeof obj["error"] === "string" ? (obj["error"] as string) : "",
    error_type: typeof obj["error_type"] === "string" ? (obj["error_type"] as string) : undefined,
    message: typeof obj["message"] === "string" ? (obj["message"] as string) : undefined,
    context: obj["context"] as Record<string, string> | undefined,
  };
}

/** Low-level request helper (real API mode only). */
export async function apiRequest<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  if (isDemoMode()) {
    throw new ApiError("apiRequest() must not be called in demo mode.", "DemoMode");
  }
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60_000);
  try {
    const res = await fetch(buildUrl(path), {
      ...init,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });
    const raw: unknown = await res.json().catch(() => null);
    if (!res.ok) {
      const payload = parsePayload(raw);
      throw new ApiError(
        payload.message ?? payload.error ?? `HTTP ${res.status}`,
        payload.error_type ?? "HttpError",
        res.status,
        payload.context ?? null,
      );
    }
    return raw as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError("Request timed out.", "Timeout");
    }
    throw new ApiError(
      `Cannot reach the PhronesisML backend at ${getBaseUrl()}.`,
      "NetworkError",
      null,
      { url: getBaseUrl() },
    );
  } finally {
    clearTimeout(timeout);
  }
}

/** Streaming upload with progress callback (real API mode only). */
export function uploadFile<T>(
  path: string,
  file: File,
  onProgress?: (percent: number) => void,
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", buildUrl(path));
    xhr.upload.onprogress = (evt) => {
      if (evt.lengthComputable && onProgress) {
        onProgress(Math.round((evt.loaded / evt.total) * 100));
      }
    };
    xhr.onload = () => {
      let raw: unknown = null;
      try {
        raw = JSON.parse(xhr.responseText);
      } catch {
        raw = null;
      }
      if (xhr.status < 200 || xhr.status >= 300) {
        const payload = parsePayload(raw);
        reject(
          new ApiError(
            payload.message ?? payload.error ?? `HTTP ${xhr.status}`,
            payload.error_type ?? "HttpError",
            xhr.status,
            payload.context ?? null,
          ),
        );
        return;
      }
      resolve(raw as T);
    };
    xhr.onerror = () =>
      reject(new ApiError(`Cannot reach the PhronesisML backend at ${getBaseUrl()}.`, "NetworkError", null, { url: getBaseUrl() }));
    xhr.onabort = () => reject(new ApiError("Upload aborted.", "AbortError"));
    const form = new FormData();
    form.append("file", file);
    xhr.send(form);
  });
}

export type { ApiErrorPayload };
export { ApiError };