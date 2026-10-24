# Wind Forecast Intelligence: web app

React 19, TypeScript and Vite. Two pages: **Overview** (`/`) shows January's accuracy at a chosen
decision time, and **Day Replay** (`/replay`) shows one delivery day half-hour by half-hour, with
the forecast that was available, the actual, and the error. All figures come from the API
described in [`../contracts/openapi.yaml`](../contracts/openapi.yaml); the browser only validates,
formats and displays them.

## Run locally

Needs Node 22 and Yarn 1.

```sh
yarn install
yarn dev        # demo data, no backend needed (http://localhost:5173)
yarn dev:api    # the real API from `make dev`, proxied at /api
```

`yarn dev` uses mock mode (`VITE_API_MODE=mock` in `.env.development`): [MSW](https://mswjs.io)
answers API calls in the browser with the responses the backend generates into
`../contracts/fixtures/api` (`make fixtures`). They are real January 2026 results for 5, 15, 16,
19 and 28 January, which cover every situation the UI handles (complete, partial and empty days,
a late forecast, hindsight). The **Demo scenario** menu adds a synthetic day with every interval
status and the error responses. Mock code and data are left out of production builds.

| Command | Purpose |
| --- | --- |
| `yarn typecheck` | TypeScript |
| `yarn lint` / `yarn format:check` | ESLint / Prettier |
| `yarn test` | Unit and component tests; every backend fixture checked against the runtime schemas |
| `yarn test:e2e` | Browser workflows, request races, offline state, responsive layout and axe checks (run `yarn playwright install chromium` once) |
| `yarn build` | Production build in `dist/`, calling the API at `VITE_API_BASE_URL` (default `/api/v1`) |

## Structure

```text
src/
  app/          routing, shell, error boundary, URL state
  api/          HTTP client, runtime response schemas (Zod), queries
  components/   small shared UI pieces
  features/     overview, replay and receipts screens
  hooks/        browser online status
  lib/          number and time formatting, display labels
  mocks/        MSW handlers serving ../contracts/fixtures/api
  styles/       design tokens and page layouts
  test/         unit, component and fixture tests
e2e/            Playwright workflows
```

The URL holds every input (date, decision-time rule or exact cutoff, selected interval), so any
view can be shared or reloaded. Each response is checked against its schema and against the
inputs it echoes back before it is shown, and an aborted or slower earlier request can never
replace the current one. Retries follow the API's `retryable` flag and `Retry-After` header.

## Deployment

The production build is static. It expects the API on the same origin under `/api/v1`:

- **Vercel**: `../vercel.json` serves this app and routes `/api/*` to the backend.
- **Docker**: `docker compose up` (from the repository root) serves it with nginx on port 8080
  and proxies `/api` to the API container.

## Accessibility

Everything works with a keyboard: native links, selects, disclosures and buttons, plus a range
control for stepping through intervals. The chart has an equivalent table, colour always comes
with text, missing values read "Unavailable", and every time shows GMT or BST. Reduced-motion and
print styles are included.
