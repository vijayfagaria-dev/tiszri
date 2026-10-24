"""Read and validate query parameters before any data is fetched.

Every problem in a request is reported together. The response `code` is that of the first
problem; `details` lists them all.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from starlette.datastructures import QueryParams

from app.analysis.cutoffs import cutoff_at, cutoff_from_rule
from app.api.errors import ApiError
from app.core.config import Settings
from app.models.analysis import Cutoff, CutoffRule
from app.schemas.errors import ErrorDetailOut
from app.schemas.metadata import default_rule
from app.utils.dates import london_time

MAX_VALUE_LENGTH = 64
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
TIME_PATTERN = re.compile(r"\d{2}:\d{2}")
INSTANT_PATTERN = re.compile(
    r"(?P<base>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?P<fraction>\.\d+)?(?P<zone>Z|[+-]\d{2}:\d{2})?"
)


@dataclass
class SummaryQuery:
    first: date
    last: date
    rule: CutoffRule
    rule_source: str  # RULE or DEFAULT


class _Problems:
    def __init__(self) -> None:
        self.codes: list[str] = []
        self.details: list[ErrorDetailOut] = []

    def add(self, code: str, field: str | None, reason: str, message: str) -> None:
        self.codes.append(code)
        self.details.append(ErrorDetailOut(field=field, reason=reason, message=message))

    def raise_if_any(self) -> None:
        if self.details:
            raise ApiError(422, self.codes[0], self.details[0].message, self.details)


def parse_analysis_query(params: QueryParams, settings: Settings) -> tuple[date, Cutoff]:
    problems = _Problems()
    _check_names(
        params, {"deliveryDate", "decisionCutoff", "cutoffDayOffset", "cutoffLocalTime"}, problems
    )
    delivery_date = _parse_delivery_date(params.get("deliveryDate"), settings, problems)

    exact = params.get("decisionCutoff")
    has_rule = "cutoffDayOffset" in params or "cutoffLocalTime" in params
    if exact is not None and has_rule:
        problems.add(
            "INVALID_PARAMETER",
            "decisionCutoff",
            "MUTUALLY_EXCLUSIVE",
            "Send either decisionCutoff or cutoffDayOffset with cutoffLocalTime, not both.",
        )
    instant = _parse_instant(exact, problems) if exact is not None else None
    rule = _parse_rule(params, settings, problems)
    problems.raise_if_any()
    assert delivery_date is not None

    if instant is not None:
        cutoff = cutoff_at(delivery_date, instant)
    elif rule is not None:
        cutoff = cutoff_from_rule(delivery_date, rule)
    else:
        cutoff = cutoff_from_rule(delivery_date, default_rule(settings), "DEFAULT")
    _check_cutoff_range(delivery_date, cutoff.utc, settings)
    return delivery_date, cutoff


def parse_summary_query(params: QueryParams, settings: Settings) -> SummaryQuery:
    problems = _Problems()
    _check_names(params, {"from", "to", "cutoffDayOffset", "cutoffLocalTime"}, problems)

    first, last = settings.summary_default_from, settings.summary_default_to
    if ("from" in params) != ("to" in params):
        problems.add(
            "INVALID_PARAMETER", "from", "INCOMPLETE_PAIR", "Send both from and to, or neither."
        )
    elif "from" in params:
        first = (
            _parse_date("from", params["from"], settings, "INVALID_DATE_RANGE", problems) or first
        )
        last = _parse_date("to", params["to"], settings, "INVALID_DATE_RANGE", problems) or last
        if first > last:
            problems.add(
                "INVALID_DATE_RANGE", "from", "FROM_AFTER_TO", "from must not be after to."
            )

    rule = _parse_rule(params, settings, problems)
    problems.raise_if_any()
    if rule is None:
        return SummaryQuery(first, last, default_rule(settings), "DEFAULT")
    _check_cutoff_range(first, cutoff_from_rule(first, rule).utc, settings)
    return SummaryQuery(first, last, rule, "RULE")


def _check_names(params: QueryParams, allowed: set[str], problems: _Problems) -> None:
    for name in params:
        if name not in allowed:
            problems.add(
                "INVALID_PARAMETER", name, "UNKNOWN_PARAMETER", f"Unknown parameter {name!r}."
            )
        elif len(params.getlist(name)) > 1:
            problems.add(
                "INVALID_PARAMETER", name, "DUPLICATE_PARAMETER", f"{name} was sent more than once."
            )
        elif len(params[name]) > MAX_VALUE_LENGTH:
            problems.add("INVALID_PARAMETER", name, "TOO_LONG", f"{name} is too long.")


def _parse_delivery_date(value: str | None, settings: Settings, problems: _Problems) -> date | None:
    if value is None:
        problems.add(
            "INVALID_DELIVERY_DATE", "deliveryDate", "MISSING", "deliveryDate is required."
        )
        return None
    return _parse_date("deliveryDate", value, settings, "INVALID_DELIVERY_DATE", problems)


def _parse_date(
    field: str, value: str, settings: Settings, code: str, problems: _Problems
) -> date | None:
    try:
        if not DATE_PATTERN.fullmatch(value):
            raise ValueError
        parsed = date.fromisoformat(value)
    except ValueError:
        problems.add(code, field, "UNPARSEABLE", f"{field} must be a date like 2026-01-16.")
        return None
    if not settings.supported_date_from <= parsed <= settings.supported_date_to:
        start, end = settings.supported_date_from, settings.supported_date_to
        window = f"{start.day} {start:%b %Y} and {end.day} {end:%b %Y}"
        problems.add(code, field, "OUT_OF_RANGE", f"Choose a date between {window}.")
        return None
    return parsed


def _parse_instant(value: str, problems: _Problems) -> datetime | None:
    match = INSTANT_PATTERN.fullmatch(value)
    if match and match["fraction"]:
        problems.add(
            "INVALID_CUTOFF",
            "decisionCutoff",
            "FRACTIONAL_SECONDS",
            "decisionCutoff must not include fractions of a second.",
        )
        return None
    if match and not match["zone"]:
        problems.add(
            "INVALID_CUTOFF",
            "decisionCutoff",
            "TIMEZONE_REQUIRED",
            "decisionCutoff must include a timezone, e.g. 2026-01-15T09:00:00Z.",
        )
        return None
    try:
        if not match:
            raise ValueError
        return datetime.fromisoformat(value)
    except ValueError:
        hint = " A '+' offset must be sent as %2B; prefer the Z form." if " " in value else ""
        problems.add(
            "INVALID_CUTOFF",
            "decisionCutoff",
            "UNPARSEABLE",
            f"decisionCutoff must look like 2026-01-15T09:00:00Z.{hint}",
        )
        return None


def _parse_rule(params: QueryParams, settings: Settings, problems: _Problems) -> CutoffRule | None:
    offset, local = params.get("cutoffDayOffset"), params.get("cutoffLocalTime")
    if offset is None and local is None:
        return None
    if offset is None or local is None:
        problems.add(
            "INVALID_PARAMETER",
            "cutoffDayOffset",
            "INCOMPLETE_PAIR",
            "Send cutoffDayOffset and cutoffLocalTime together.",
        )
        return None

    day_offset: int | None = None
    if re.fullmatch(r"-?\d{1,2}", offset) and (
        settings.cutoff_min_day_offset <= int(offset) <= settings.cutoff_max_day_offset
    ):
        day_offset = int(offset)
    else:
        problems.add(
            "INVALID_CUTOFF_RULE",
            "cutoffDayOffset",
            "DAY_OFFSET_OUT_OF_RANGE",
            f"cutoffDayOffset must be a whole number from {settings.cutoff_min_day_offset} "
            f"to {settings.cutoff_max_day_offset}.",
        )

    local_time: time | None = None
    try:
        if not TIME_PATTERN.fullmatch(local):
            raise ValueError
        local_time = time.fromisoformat(local)
    except ValueError:
        problems.add(
            "INVALID_CUTOFF_RULE",
            "cutoffLocalTime",
            "TIME_UNPARSEABLE",
            "cutoffLocalTime must be a time like 09:00.",
        )

    if day_offset is None or local_time is None:
        return None
    return CutoffRule(day_offset, local_time)


def _check_cutoff_range(delivery_date: date, cutoff: datetime, settings: Settings) -> None:
    earliest = london_time(delivery_date + timedelta(days=settings.cutoff_min_day_offset), time(0))
    latest = london_time(delivery_date + timedelta(days=settings.cutoff_max_day_offset), time(0))
    if earliest <= cutoff <= latest:
        return
    reason = "BEFORE_RANGE" if cutoff < earliest else "AFTER_RANGE"
    message = (
        f"The decision time must be between {settings.cutoff_min_day_offset * -1} days before "
        f"and {settings.cutoff_max_day_offset} days after the delivery date (UK midnight)."
    )
    detail = ErrorDetailOut(field="decisionCutoff", reason=reason, message=message)
    raise ApiError(422, "CUTOFF_OUT_OF_RANGE", message, [detail])
