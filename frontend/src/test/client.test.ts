import { afterEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";
import { ApiError, request, retry, retryAfterMs } from "../api/client";
afterEach(() => vi.unstubAllGlobals());
const schema = z.object({ value: z.number() });
describe("API boundary", () => {
  it("sends documented parameters, cancellation and captures headers", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      Response.json(
        { value: 1, future: true },
        {
          headers: {
            "X-Request-ID": "test-request",
            "Server-Timing": "total;dur=12",
          },
        },
      ),
    );
    vi.stubGlobal("fetch", fetcher);
    const controller = new AbortController();
    const result = await request(
      "wind-analysis",
      schema,
      controller.signal,
      new URLSearchParams({
        deliveryDate: "2026-01-16",
        decisionCutoff: "2026-01-15T12:00:00Z",
      }),
    );
    expect(fetcher.mock.calls[0][0]).toBe(
      "/api/v1/wind-analysis?deliveryDate=2026-01-16&decisionCutoff=2026-01-15T12%3A00%3A00Z",
    );
    expect(fetcher.mock.calls[0][1].signal).toBe(controller.signal);
    expect(result.httpHeaders["X-Request-ID"]).toBe("test-request");
    expect(result.response).toEqual({ value: 1 });
  });
  it("rejects malformed and mismatched responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(Response.json({ value: "invalid" }))
        .mockResolvedValueOnce(Response.json({ value: 1 })),
    );
    await expect(request("metadata", schema)).rejects.toThrow(
      "doesn’t recognise",
    );
    await expect(
      request("metadata", schema, undefined, undefined, () => false),
    ).rejects.toThrow("does not match");
  });
  it("uses envelope retryability and Retry-After, not status guesses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        Response.json(
          {
            error: {
              code: "UPSTREAM_RATE_LIMITED",
              message: "Wait",
              details: [],
              requestId: "test",
              retryable: true,
            },
          },
          { status: 503, headers: { "Retry-After": "2" } },
        ),
      ),
    );
    try {
      await request("wind-analysis", schema);
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).retryAfter).toBe(2000);
      expect(retry(0, error as Error)).toBe(true);
      expect(retry(2, error as Error)).toBe(false);
    }
    expect(retryAfterMs("3")).toBe(3000);
    expect(retry(0, new Error("schema error"))).toBe(false);
  });
});
