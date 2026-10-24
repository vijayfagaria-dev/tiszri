"""Record the Elexon source data used by tests and by the offline (fixtures) source mode.

Captures FUELHH wind actuals and every WINDFOR forecast vintage needed to analyse delivery
dates 1 Jan - 1 Feb 2026, and writes them as deterministic gzipped JSON plus a manifest.

Usage (from backend/): uv run python -m scripts.record_fixtures
"""

from __future__ import annotations

import gzip
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "contracts" / "fixtures" / "source"

RECORDINGS: list[dict[str, Any]] = [
    {
        "file": "fuelhh_wind.json.gz",
        "dataset": "FUELHH",
        "path": "/datasets/FUELHH/stream",
        "params": {
            "settlementDateFrom": "2026-01-01",
            "settlementDateTo": "2026-02-01",
            "fuelType": "WIND",
        },
    },
    {
        # Four publish days before the first delivery date up to the day after the last one,
        # so every vintage that can cover the supported window is present.
        "file": "windfor.json.gz",
        "dataset": "WINDFOR",
        "path": "/datasets/WINDFOR/stream",
        "params": {
            "publishDateTimeFrom": "2025-12-28T00:00:00Z",
            "publishDateTimeTo": "2026-02-03T00:00:00Z",
        },
    },
]


def record(client: httpx.Client, spec: dict[str, Any]) -> dict[str, Any]:
    response = client.get(spec["path"], params=spec["params"])
    response.raise_for_status()
    rows = response.json()
    if not isinstance(rows, list):
        raise ValueError(f"{spec['dataset']}: expected a JSON array, got {type(rows).__name__}")

    payload = json.dumps(rows, separators=(",", ":")).encode()
    # mtime=0 keeps the compressed bytes identical across re-recordings of the same data.
    (OUTPUT_DIR / spec["file"]).write_bytes(gzip.compress(payload, mtime=0))
    return {
        "file": spec["file"],
        "dataset": spec["dataset"],
        "request": {"path": spec["path"], "params": spec["params"]},
        "rows": len(rows),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=BASE_URL, timeout=60.0) as client:
        entries = [record(client, spec) for spec in RECORDINGS]
    manifest = {
        "source": BASE_URL,
        "recordedAt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "recordings": entries,
    }
    (OUTPUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for entry in entries:
        print(f"{entry['dataset']}: {entry['rows']} rows -> {entry['file']}")


if __name__ == "__main__":
    main()
