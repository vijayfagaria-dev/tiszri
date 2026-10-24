"""Decision-time presets and construction of the applied cutoff."""

from datetime import date, datetime, time

from app.models.analysis import Cutoff, CutoffRule
from app.utils.dates import cutoff_position, resolve_rule

PRESETS = {
    "TWO_DAYS_BEFORE_0900": CutoffRule(-2, time(9, 0)),
    "MORNING_BEFORE_0900": CutoffRule(-1, time(9, 0)),
    "NOON_BEFORE_1200": CutoffRule(-1, time(12, 0)),
    "DELIVERY_START_0000": CutoffRule(0, time(0, 0)),
    "AFTER_DELIVERY_0000": CutoffRule(1, time(0, 0)),
}


def preset_for(rule: CutoffRule) -> str | None:
    return next((name for name, preset in PRESETS.items() if preset == rule), None)


def cutoff_from_rule(delivery_date: date, rule: CutoffRule, source: str = "RULE") -> Cutoff:
    utc = resolve_rule(delivery_date, rule.day_offset, rule.local_time)
    return Cutoff(utc, source, cutoff_position(utc, delivery_date), rule, preset_for(rule))


def cutoff_at(delivery_date: date, utc: datetime) -> Cutoff:
    return Cutoff(utc, "EXPLICIT", cutoff_position(utc, delivery_date))
