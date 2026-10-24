# Run `make help` for the list of commands.
BACKEND := cd backend && env -u VIRTUAL_ENV uv run
URL ?= http://localhost:8000

.PHONY: help setup dev test traceability live lint format typecheck ci fixtures record up down latency

help:
	@echo "setup      install backend dependencies"
	@echo "dev        run the API locally with live Elexon data (http://localhost:8000)"
	@echo "test       run the backend test suite"
	@echo "traceability  run the tests and list which SRS requirements they cover"
	@echo "live       check the assumptions about the live Elexon API still hold"
	@echo "lint       check formatting and lint rules"
	@echo "format     apply formatting and safe lint fixes"
	@echo "typecheck  run mypy"
	@echo "ci         lint + typecheck + test (what CI runs)"
	@echo "fixtures   regenerate the frontend's API fixtures from the backend"
	@echo "record     re-record the Elexon source data used by tests"
	@echo "up / down  start / stop the stack with Docker Compose (SOURCE_MODE=fixtures for offline)"
	@echo "latency    print Server-Timing for a cold and two warm requests (URL=...)"

setup:
	cd backend && uv sync

dev:
	$(BACKEND) uvicorn app.main:app --reload --port 8000

test:
	$(BACKEND) pytest

traceability:
	$(BACKEND) pytest -q --traceability

live:
	cd backend && RUN_LIVE_TESTS=1 env -u VIRTUAL_ENV uv run pytest tests/live -v

lint:
	$(BACKEND) ruff check .
	$(BACKEND) ruff format --check .

format:
	$(BACKEND) ruff format .
	$(BACKEND) ruff check --fix .

typecheck:
	$(BACKEND) mypy

ci: lint typecheck test

fixtures:
	$(BACKEND) python -m scripts.generate_api_fixtures

record:
	$(BACKEND) python -m scripts.record_fixtures

up:
	docker compose up --build api

down:
	docker compose down

latency:
	@for run in cold warm warm; do \
		printf "%-5s " $$run; \
		curl -s -o /dev/null -D - "$(URL)/api/v1/wind-analysis?deliveryDate=2026-01-16" | grep -i server-timing; \
	done
