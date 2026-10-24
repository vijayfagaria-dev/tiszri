import { delay, http, HttpResponse, type JsonBodyType } from "msw";

// Mock mode serves the responses the backend generates into contracts/fixtures/api
// (`make fixtures`), so the demo shows real January 2026 results in the current contract shape.
const directory = "../../../contracts/fixtures/api/";
const files = import.meta.glob<JsonBodyType>(
  "../../../contracts/fixtures/api/*.json",
  {
    import: "default",
  },
);
const load = (file: string) => files[directory + file]();

type Entry = {
  file: string;
  status: number;
  request: { path: string; params: Record<string, string> };
  source: string;
};
const headers = {
  "X-Request-ID": "demo-request",
  "Server-Timing": "fetch;dur=12, analyze;dur=4, total;dur=16",
  "Cache-Control":
    "public, max-age=300, s-maxage=86400, stale-while-revalidate=604800",
};

// The app always sends the decision rule and summary window; fill in the defaults the
// backend applies so both sides of the lookup are spelled the same way.
const defaults: Record<string, Record<string, string>> = {
  "/api/v1/wind-analysis": { cutoffDayOffset: "-1", cutoffLocalTime: "09:00" },
  "/api/v1/accuracy-summary": {
    from: "2026-01-02",
    to: "2026-02-01",
    cutoffDayOffset: "-1",
    cutoffLocalTime: "09:00",
  },
};
const requestKey = (path: string, params: Record<string, string>) => {
  const all = { ...defaults[path], ...params };
  if (all.decisionCutoff) {
    delete all.cutoffDayOffset;
    delete all.cutoffLocalTime;
  }
  return `${path}?${new URLSearchParams(Object.entries(all).sort())}`;
};

const catalogue = load("index.json").then((data) => {
  const index = data as Entry[];
  const recorded = new Map<string, string>();
  const synthetic = new Map<string, string>();
  const errors = new Map<string, Entry>();
  for (const entry of index) {
    const key = requestKey(entry.request.path, entry.request.params);
    if (entry.status !== 200) {
      if (!errors.has(String(entry.status)))
        errors.set(String(entry.status), entry);
    } else if (entry.source === "synthetic") synthetic.set(key, entry.file);
    else recorded.set(key, entry.file);
  }
  return { recorded, synthetic, errors };
});

const notFound = () =>
  HttpResponse.json(
    {
      error: {
        code: "NOT_FOUND",
        message:
          "Demo mode only has recorded examples for 5, 15, 16, 19 and 28 January. Connect the app to the API to explore any other day or decision time.",
        details: [],
        requestId: "demo-request",
        retryable: false,
      },
    },
    { status: 404, headers: { "Cache-Control": "no-store" } },
  );

export const handlers = [
  http.get("*/api/v1/:endpoint", async ({ request }) => {
    const ui = new URLSearchParams(location.search);
    await delay(
      Math.min(10000, Math.max(0, Number(ui.get("mockDelay") ?? 300))),
    );
    const { recorded, synthetic, errors } = await catalogue;
    const url = new URL(request.url);
    const forced = ui.get("mockError");
    if (forced && url.pathname !== "/api/v1/metadata") {
      if (forced === "malformed") return HttpResponse.json({ broken: true });
      const entry = errors.get(forced) ?? errors.get("500")!;
      return HttpResponse.json(await load(entry.file), {
        status: entry.status,
        headers: {
          ...headers,
          "Cache-Control": "no-store",
          ...(entry.status === 503 ? { "Retry-After": "2" } : {}),
        },
      });
    }
    const key = requestKey(url.pathname, Object.fromEntries(url.searchParams));
    const file =
      (ui.get("scenario") === "edge" && synthetic.get(key)) ||
      recorded.get(key);
    if (!file) return notFound();
    return HttpResponse.json(await load(file), { headers });
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
