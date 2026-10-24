import { z } from "zod";
import { errorSchema } from "./schemas";
export type ApiResult<T> = {
  response: T;
  httpHeaders: Record<string, string | null>;
};
export class ApiError extends Error {
  code: string;
  requestId: string;
  retryable: boolean;
  retryAfter: number;
  details: z.infer<typeof errorSchema>["error"]["details"];
  constructor(error: z.infer<typeof errorSchema>["error"], retryAfter = 0) {
    super(error.message);
    this.code = error.code;
    this.requestId = error.requestId;
    this.retryable = error.retryable;
    this.retryAfter = retryAfter;
    this.details = error.details;
  }
}
export function retryAfterMs(value: string | null) {
  if (!value) return 0;
  return /^\d+$/.test(value)
    ? Number(value) * 1000
    : Math.max(0, Date.parse(value) - Date.now()) || 0;
}
export async function request<T>(
  path: string,
  schema: z.ZodType<T>,
  signal?: AbortSignal,
  params?: URLSearchParams,
  guard?: (data: T) => boolean,
  acceptedStatuses: number[] = [],
): Promise<ApiResult<T>> {
  const base = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(
    /\/$/,
    "",
  );
  const response = await fetch(
    `${base}/${path}${params?.size ? `?${params}` : ""}`,
    {
      signal,
      headers: {
        Accept: "application/json",
        "X-Request-ID": crypto.randomUUID(),
      },
    },
  );
  const httpHeaders = Object.fromEntries(
    ["X-Request-ID", "Server-Timing", "Cache-Control", "Retry-After"].map(
      (key) => [key, response.headers.get(key)],
    ),
  );
  if (!response.headers.get("content-type")?.includes("application/json"))
    throw new Error(
      "The analysis service returned data this page doesn’t recognise.",
    );
  const body: unknown = await response.json();
  if (!response.ok && !acceptedStatuses.includes(response.status)) {
    const parsed = errorSchema.safeParse(body);
    if (!parsed.success)
      throw new Error(
        "The analysis service returned an unrecognised error response.",
      );
    throw new ApiError(
      parsed.data.error,
      retryAfterMs(httpHeaders["Retry-After"]),
    );
  }
  const parsed = schema.safeParse(body);
  if (!parsed.success)
    throw new Error(
      "The analysis service returned data this page doesn’t recognise.",
    );
  if (guard && !guard(parsed.data))
    throw new Error(
      "The returned analysis does not match the selected inputs. It has not been displayed.",
    );
  return { response: parsed.data, httpHeaders };
}
export const retry = (count: number, error: Error) =>
  count < 2 &&
  (error instanceof ApiError ? error.retryable : error instanceof TypeError);
export const retryDelay = (attempt: number, error: Error) =>
  error instanceof ApiError && error.retryAfter
    ? error.retryAfter
    : Math.min(1000 * 2 ** attempt, 10000);
