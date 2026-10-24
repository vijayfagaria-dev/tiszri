# Wind Forecast Intelligence

[![Live demo](https://img.shields.io/badge/live%20demo-tiszri.vercel.app-5b6cff?logo=vercel)](https://tiszri.vercel.app)
[![CI](https://github.com/vijayfagaria-dev/tiszri/actions/workflows/ci.yml/badge.svg)](https://github.com/vijayfagaria-dev/tiszri/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)

See GB wind forecasts the way a day-ahead buyer saw them, and how far off they were.
Built on Elexon data for decisions made in January 2026.

**[Open the live app →](https://tiszri.vercel.app)** · **[Watch the walkthrough (4:30) →](https://youtu.be/BeIDjXWJPBY)**

| Overview | Day Replay |
|---|---|
| ![Overview](docs/images/overview.jpg) | ![Day Replay](docs/images/replay.jpg) |

## What it does

- **Day Replay:** pick a day and a decision time to see which forecast was available then,
  against what actually happened.
- **Accuracy overview:** MAE, RMSE, bias and coverage for any part of January, day by day.
- **Planning figure:** in 9 of 10 half-hours, actual wind was at most 4,145 MW below the forecast.
- **CSV export** of any day, and a shareable link for every view.

It measures forecast accuracy; it does not say how much power to buy.

## Run it

```bash
docker compose up --build      # web app on :8080, API on :8000
```

Or without Docker (needs Python 3.12 with uv, and Node 22 with Yarn):

```bash
make setup && make dev         # API on :8000
make web                       # web app on :5173 (second terminal)
```

## How it works

- **Data:** actual wind from Elexon FUELHH, forecasts from Elexon WINDFOR (MW).
- **Forecast used:** the latest one published at or before the decision time. Later forecasts are
  never used, and gaps are shown, not filled from older ones.
- **Matching:** each hourly forecast covers both half-hours of its hour.
- **Error:** forecast − actual, so positive means the forecast was too high.

The default decision time is 09:00 UK time the day before delivery. Full rules and formulas are in
the app under *How it's calculated*, and in [`contracts/openapi.yaml`](contracts/openapi.yaml).

## API

| Endpoint | Returns |
|---|---|
| `/api/v1/wind-analysis` | One day at a decision time |
| `/api/v1/wind-analysis/export` | The same day as CSV |
| `/api/v1/accuracy-summary` | Accuracy over a date range |
| `/api/v1/metadata` | Dates, presets and rules |
| `/api/v1/health/live`, `/ready` | Health checks |

Example: [`/api/v1/accuracy-summary`](https://tiszri.vercel.app/api/v1/accuracy-summary)

## Project

| | |
|---|---|
| `backend/` | Python FastAPI service and its tests |
| `frontend/` | React web app ([details](frontend/README.md)) |
| `contracts/` | API contract and recorded Elexon data |

Tests: `make ci` (backend) and `yarn test && yarn test:e2e` (in `frontend/`); CI runs both on every
push. Deployed on Vercel from [`vercel.json`](vercel.json).

## AI Assistance

Claude Code was used occasionally for Elexon API research and to assist with parts of the
implementation and testing. The final code and analysis were reviewed and checked against recorded
Elexon data and expected results.
