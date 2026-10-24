"""Builders and recorded-data loaders shared by the tests."""

import gzip
import json
from datetime import date, datetime, time
from functools import cache
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from app.analysis.cutoffs import cutoff_at, cutoff_from_rule
from app.models.analysis import Cutoff, CutoffRule
from app.models.source import Actual, Forecast

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_FIXTURES = REPO_ROOT / "contracts" / "fixtures" / "source"
CONTRACT = REPO_ROOT / "contracts" / "openapi.yaml"


@cache
def recorded(name: str) -> list[dict[str, Any]]:
    return json.loads(gzip.decompress((SOURCE_FIXTURES / name).read_bytes()))


def ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


def forecast(hour: str, published: str, generation: int | None) -> Forecast:
    return Forecast(ts(hour), ts(published), generation)


def actual(start: str, generation: int | None, **extra: Any) -> Actual:
    return Actual(ts(start), generation, **extra)


def rule_cutoff(delivery_date: date, day_offset: int, at: str) -> Cutoff:
    return cutoff_from_rule(delivery_date, CutoffRule(day_offset, time.fromisoformat(at)))


def explicit_cutoff(delivery_date: date, instant: str) -> Cutoff:
    return cutoff_at(delivery_date, ts(instant))


@cache
def _contract_registry() -> Registry:
    spec = yaml.safe_load(CONTRACT.read_text())
    return Registry().with_resource("contract", Resource.from_contents(spec, DRAFT202012))


def contract_errors(body: Any, schema: str) -> list[str]:
    """Differences between a response body and a schema in contracts/openapi.yaml."""
    validator = Draft202012Validator(
        {"$ref": f"contract#/components/schemas/{schema}"}, registry=_contract_registry()
    )
    return [f"{list(e.absolute_path)}: {e.message}" for e in validator.iter_errors(body)]
