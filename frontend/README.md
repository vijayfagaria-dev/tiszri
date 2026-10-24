# Wind Forecast Intelligence

React 19 + TypeScript + Vite dashboard for historical GB national wind forecast accuracy. Overview (`/`) and Day Replay (`/replay`) use the supplied contract 1.0.0. The dark visual direction follows the requested screenshot.

## Run locally

```sh
cd frontend
yarn install
yarn dev
```

Open the printed Vite URL (normally http://localhost:5173). Development defaults to `VITE_API_MODE=mock` via `.env.development`. The mock worker is checked in. Regenerate it after upgrading MSW with `yarn msw init public --save`.

## Commands

| Command | Purpose |
| --- | --- |
| `yarn dev` | Local application with MSW demo data |
| `yarn typecheck` | TypeScript validation |
| `yarn lint` | ESLint and React hook checks |
| `yarn test` | Contract fixtures, API client, formatting, URL and component tests |
| `yarn playwright install chromium` | Install browser for E2E checks |
| `yarn test:e2e` | Browser workflows, race, offline, responsive and axe checks |
| `yarn build` | Production build; real API mode by default |
| `yarn build:demo` | Production-style artifact with demo mode enabled |
| `yarn preview` | Serve the last build |
| `yarn fixtures:generate` | Reproduce all synthetic JSON fixtures offline |
| `yarn format` | Format application and test source |

The initial verification used `PLAYWRIGHT_BROWSERS_PATH=/private/tmp/wind-forecast-browsers` for browser installation and execution. Omit that variable to use Playwright's normal cache on your machine.

## Low-level design and directory responsibilities

```text
src/
  app/                    Routing, providers, shell, error boundary, URL mapping
  api/                    HTTP client, response schemas, query lifecycle
  components/
    ui/                   Small reusable presentation/feedback components
    WindArt.tsx           Decorative, code-native SVG artwork
  features/
    overview/             Daily performance, featured replays, distribution, hero
    replay/               Decision controls, chart, ledger, summary, inspector
    receipts/             Methodology and diagnostic receipt presentation
  hooks/                  Browser online status
  lib/                    Number/time formatting and display labels
  mocks/                  MSW request handlers; no analytical calculation
  styles/                 Semantic tokens, shell, overview and replay layouts
  test/                   Unit, component and complete fixture validation
e2e/                      Browser workflows and accessibility checks
scripts/                  Offline synthetic fixture generation
public/_fixtures/         Precomputed deterministic contract-shaped responses
```

Responsibilities follow single-responsibility and composition principles. Feature components receive typed data and callbacks. API schemas and fetching stay outside presentation; URL parsing stays outside formatting. The ledger, chart and inspector share one selected interval from the URL. No global state library, service locator, generic repository hierarchy or custom rendering framework is introduced.

The app uses familiar APIs: React function components, state/effect hooks, React Router routes/search params, TanStack `useQuery`, native `fetch`, Zod objects, MSW HTTP handlers and semantic HTML. The error boundary is a small class because React's built-in boundary API requires one. `keepPreviousData` is used specifically to retain correctly labelled prior evidence while a new selection loads. No browser-side metric/selection engine exists.

## Mock catalogue and limitations

**All displayed data in mock mode is synthetic, not verified January 2026 measurements.** Every fixture request ID begins with `synthetic-`. No absent source recording is represented as real data.

The offline Python script creates coherent hourly forecasts and half-hour actuals, then precomputes metrics, status counts, distributions and supported featured categories into JSON. The browser only requests, validates, formats and displays those responses. Tests independently check their arithmetic and contract invariants.

Available requests:

- Every day from 1 January through 1 February 2026, all five metadata presets.
- Custom rule `custom:-3:09:00` for the empty scenario.
- Exact UTC cutoffs that correspond to those fixture rules.
- Overview's inclusive 2 January–1 February window for each rule.
- Scenarios `complete`, `partial`, `empty`, `edge` (the last includes every interval status).
- `mockDelay=1400` for latency; `mockError=422|429|500|502|503|504|malformed` for failures; `mockHealth=DEGRADED|UNKNOWN` for source state.

The visible Demo scenario control selects common cases. These UI parameters never reach the real API. Unmapped demo requests produce an explanatory 404. No off-schedule featured card is fabricated when the synthetic data has no qualifying vintage.

Custom cutoff entry deliberately accepts a canonical UTC instant rather than an ambiguous wall-clock value. The result shows its London equivalent. January day navigation shifts an exact cutoff by the date difference, preserving its relative time. General DST formatting is tested; relative-rule DST resolution remains the server's responsibility. The initial contract only permits January delivery dates.

## Real API integration

1. Reconcile this frontend with the repository's `../contracts/openapi.yaml` and `../contracts/fixtures/api/`. Those artifacts are available in the destination repository; this imported frontend still uses its synthetic demo catalogue. `src/api/schemas.ts` contains provisional schemas transcribed from the original contract and inferred types, not generated OpenAPI output.
2. Generate authoritative TypeScript models from that artifact, reconcile the runtime schemas, and run recorded fixtures through the same tests. Preserve unknown-field tolerance and neutral fallbacks for future warning/featured codes.
3. Set `VITE_API_MODE=real` and `VITE_API_BASE_URL=/api/v1` (or a configured API origin). Build with `yarn build`. Use a same-origin reverse proxy for production.
4. Route unknown frontend paths to `index.html` and `/api/v1/*` to the backend. Never rewrite API failures to HTML.
5. Smoke-test metadata, summary, replay, readiness (including NOT_READY), retries, echoed query identity and response headers against the backend.

Abort signals and query keys prevent old requests from replacing current results. Runtime validation rejects malformed shapes, and echoed-query guards reject results for different inputs. Metric values and result identity always come from the API response. Receipts separate `response` and `httpHeaders`, including request ID, cache and Server-Timing. Retry policy uses envelope `retryable` and honors Retry-After.

## Accessibility and operations

Native links, selects, disclosures, buttons and the range control support keyboard use. The chart has a ledger equivalent; excluded intervals use gaps and hatch patterns. Color is accompanied by direction/status text. Coverage is rounded down, missing values say Unavailable, and every displayed business time includes GMT/BST. Reduced motion and print rules are included.

For a source outage, keep the selected URL, inspect the error code/request ID and retry only when appropriate. For a schema error, compare the response with the current contract; do not suppress validation. For stale assets, redeploy the last verified immutable build and reload. Do not log or transmit analysis payloads or copied diagnostic receipts. No external telemetry or tracking is enabled.

Production release still requires reconciliation with the repository's OpenAPI and recorded fixtures, deployment configuration, cross-browser/manual screen-reader review and live integration smoke tests. Local mock acceptance is not a claim that those integration and release gates have passed.
