"""The frontend's mock data must match the contract and what the backend actually returns."""

import json

import pytest

from scripts.generate_api_fixtures import OUTPUT_DIR, build_fixtures
from tests.support import contract_errors

SCHEMAS = {
    "/api/v1/metadata": "AppMetadata",
    "/api/v1/wind-analysis": "DayAnalysis",
    "/api/v1/accuracy-summary": "AccuracySummary",
}
INDEX = json.loads((OUTPUT_DIR / "index.json").read_text())


@pytest.mark.parametrize("entry", INDEX, ids=[e["file"] for e in INDEX])
def test_fixture_matches_the_contract(entry: dict[str, object]) -> None:
    body = json.loads((OUTPUT_DIR / str(entry["file"])).read_text())
    schema = SCHEMAS[str(entry["request"]["path"])] if entry["status"] == 200 else "ErrorEnvelope"  # type: ignore[index]
    assert contract_errors(body, schema) == []


async def test_fixtures_are_up_to_date() -> None:
    """Fails if the backend changed without running `python -m scripts.generate_api_fixtures`."""
    for name, (_, status, body) in (await build_fixtures()).items():
        committed = json.loads((OUTPUT_DIR / f"{name}.json").read_text())
        assert body == committed, f"{name}.json is stale"
        assert any(e["file"] == f"{name}.json" and e["status"] == status for e in INDEX)
