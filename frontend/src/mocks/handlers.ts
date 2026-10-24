import { delay, http, HttpResponse, bypass } from "msw";
const headers = {
  "X-Request-ID": "synthetic-demo-request",
  "Server-Timing": "fetch;dur=12, analyze;dur=4, total;dur=16",
  "Cache-Control":
    "public, max-age=300, s-maxage=86400, stale-while-revalidate=604800",
};
const error = (
  code: string,
  message: string,
  status: number,
  retryable = false,
  details: { field: string; reason: string; message: string }[] = [],
) =>
  HttpResponse.json(
    {
      error: {
        code,
        message,
        details,
        requestId: "synthetic-error",
        retryable,
      },
    },
    {
      status,
      headers: {
        ...headers,
        "Cache-Control": "no-store",
        ...(status === 429 || status === 503 ? { "Retry-After": "2" } : {}),
      },
    },
  );
export const handlers = [
  http.get("*/api/v1/:endpoint", async ({ request, params }) => {
    const ui = new URLSearchParams(location.search);
    await delay(
      Math.min(10000, Math.max(0, Number(ui.get("mockDelay") ?? 300))),
    );
    if (params.endpoint === "metadata")
      return HttpResponse.json(
        await (await fetch(bypass("/_fixtures/metadata.json"))).json(),
        { headers },
      );
    const forced = ui.get("mockError");
    if (forced) {
      const errors: Record<string, [string, number, boolean]> = {
        "502": ["UPSTREAM_UNAVAILABLE", 502, true],
        "503": ["UPSTREAM_RATE_LIMITED", 503, true],
        "504": ["UPSTREAM_TIMEOUT", 504, true],
        "500": ["INTERNAL_ERROR", 500, false],
        "422": ["INVALID_DELIVERY_DATE", 422, false],
        "429": ["RATE_LIMITED", 429, true],
      };
      if (forced === "malformed") return HttpResponse.json({ broken: true });
      const [code, status, retryable] = errors[forced] ?? [
        "INTERNAL_ERROR",
        500,
        false,
      ];
      return error(
        code,
        `Demo scenario: ${code.toLowerCase().replaceAll("_", " ")}.`,
        status,
        retryable,
      );
    }
    const p = new URL(request.url).searchParams;
    const date = p.get("deliveryDate") ?? "";
    if (
      params.endpoint === "wind-analysis" &&
      (!/^2026-(01-\d{2}|02-01)$/.test(date) ||
        date < "2026-01-01" ||
        date > "2026-02-01")
    )
      return error(
        "INVALID_DELIVERY_DATE",
        "Delivery date must be between 1 January and 1 February 2026.",
        422,
        false,
        [
          {
            field: "deliveryDate",
            reason: "OUT_OF_RANGE",
            message: "Select a date within the supported window.",
          },
        ],
      );
    let offset = p.get("cutoffDayOffset") ?? "-1";
    let local = p.get("cutoffLocalTime") ?? "09:00";
    const explicit = p.get("decisionCutoff");
    if (explicit) {
      offset = String(
        Math.round(
          (Date.parse(explicit.slice(0, 10)) - Date.parse(date)) / 86400000,
        ),
      );
      local = explicit.slice(11, 16);
    }
    const key = `${offset}_${local.replace(":", "")}`;
    const scenario = ui.get("scenario") ?? "complete";
    if (
      params.endpoint === "accuracy-summary" &&
      (p.get("from") !== "2026-01-02" || p.get("to") !== "2026-02-01")
    )
      return error(
        "NOT_FOUND",
        "Demo fixtures cover the inclusive 2 January–1 February window. Real API mode supports all contract date ranges.",
        404,
      );
    const file =
      params.endpoint === "wind-analysis"
        ? `day_${date}_${key}_${scenario}`
        : params.endpoint === "accuracy-summary"
          ? `summary_${key}_${scenario}`
          : null;
    if (
      !file ||
      ![
        "-2_0900",
        "-1_0900",
        "-1_1200",
        "0_0000",
        "1_0000",
        "-3_0900",
      ].includes(key) ||
      !["complete", "partial", "empty", "edge"].includes(scenario)
    )
      return error(
        "NOT_FOUND",
        "No demo fixture for this input. Available: all five presets and the custom rule −3 days at 09:00, 1 January–1 February 2026.",
        404,
      );
    const data = await (await fetch(bypass(`/_fixtures/${file}.json`))).json();
    if (explicit && params.endpoint === "wind-analysis") {
      data.query.decisionCutoff.source = "EXPLICIT";
      data.query.decisionCutoff.rule = null;
      data.query.decisionCutoff.presetId = null;
    }
    return HttpResponse.json(data, { headers });
  }),
  http.get("*/api/v1/health/ready", () =>
    HttpResponse.json(
      {
        status: "READY",
        checks: {
          config: "OK",
          upstream:
            new URLSearchParams(location.search).get("mockHealth") ?? "OK",
        },
        lastUpstreamSuccessAt: "2026-02-03T10:00:00Z",
      },
      { headers: { "Cache-Control": "no-store" } },
    ),
  ),
  http.get("*/api/v1/health/live", () =>
    HttpResponse.json(
      { status: "OK" },
      { headers: { "Cache-Control": "no-store" } },
    ),
  ),
];
