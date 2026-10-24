"""Accuracy across a window of delivery days, pooled over every matched settlement period."""

from collections import Counter
from datetime import UTC, date, datetime, time, timedelta

from app.analysis.day_warnings import sort_warnings
from app.analysis.metrics import compute_metrics, histogram, nearest_rank
from app.models.analysis import AnalysisWarning, CutoffRule, DayAnalysis, FeaturedDay, Summary
from app.models.enums import Status, WarningCode
from app.utils.dates import LONDON, format_utc, resolve_rule

HISTOGRAM_BIN_MW = 500

SUMMARY_MESSAGES = {
    WarningCode.PARTIAL_COVERAGE: (
        "{days} of {total} days had partial coverage; pooled metrics use only matched periods."
    ),
    WarningCode.NO_MATCHED_INTERVALS: (
        "{days} of {total} days had no comparable settlement periods."
    ),
    WarningCode.NEWER_VERSION_AFTER_CUTOFF: (
        "On {days} of {total} days, forecasts published after the decision time were not used."
    ),
}


def summarize(days: list[DayAnalysis], rule: CutoffRule, publish_times: set[datetime]) -> Summary:
    matched = [i for day in days for i in day.intervals if i.error is not None]
    errors = [i.error for i in matched if i.error is not None]
    on_the_hour = [i.error for i in matched if i.error is not None and i.start.minute == 0]

    status_counts = dict.fromkeys(Status, 0)
    for day in days:
        for status, count in day.status_counts.items():
            status_counts[status] += count

    abs_percentiles = signed_percentiles = None
    if errors:
        absolute, signed = sorted(abs(e) for e in errors), sorted(errors)
        abs_percentiles = {f"p{p}": nearest_rank(absolute, p) for p in (50, 90, 95)}
        signed_percentiles = {f"p{p}": nearest_rank(signed, p) for p in (10, 90)}

    return Summary(
        days=days,
        status_counts=status_counts,
        metrics=compute_metrics(errors),
        on_the_hour=compute_metrics(on_the_hour),
        abs_percentiles=abs_percentiles,
        signed_percentiles=signed_percentiles,
        histogram=histogram(errors, HISTOGRAM_BIN_MW),
        featured=featured_days(days, rule, publish_times),
        warnings=_pooled_warnings(days),
    )


def featured_days(
    days: list[DayAnalysis], rule: CutoffRule, publish_times: set[datetime]
) -> list[FeaturedDay]:
    """Days worth a closer look. Ties go to the earliest day."""
    featured = []
    measured = [d for d in days if d.metrics.mae is not None]
    complete = [d for d in measured if d.result_state == "COMPLETE"]

    if measured:
        worst = max(measured, key=lambda d: (_mae(d), -d.delivery_date.toordinal()))
        featured.append(FeaturedDay("WORST_DAY", worst.delivery_date, rule, _mae_and_bias(worst)))
    if complete:
        best = min(complete, key=lambda d: (_mae(d), d.delivery_date.toordinal()))
        featured.append(FeaturedDay("BEST_DAY", best.delivery_date, rule, _mae_and_bias(best)))

        # Days where at least half of the average miss cancels out in the bias.
        hidden = [d for d in complete if _mae(d) - abs(_bias(d)) >= 0.5 * _mae(d)]
        if hidden:
            day = max(hidden, key=lambda d: (_mae(d) - abs(_bias(d)), -d.delivery_date.toordinal()))
            data = _mae_and_bias(day) | {"over": day.metrics.over, "under": day.metrics.under}
            featured.append(FeaturedDay("BIAS_HIDES_ERROR", day.delivery_date, rule, data))

    if days:
        late = off_schedule_vintage(publish_times, days[0].delivery_date, days[-1].delivery_date)
        if late:
            featured.append(late)
    return featured


def off_schedule_vintage(
    publish_times: set[datetime], first: date, last: date
) -> FeaturedDay | None:
    """A forecast published outside its usual slot, replacing a slot that was skipped that day.

    Usual slots are publish times of day seen on at least half of the publish days. The suggested
    decision time falls between the skipped slot and the late publication, so replaying it shows
    the fallback to the previous forecast.
    """
    slots_by_day: dict[date, set[time]] = {}
    for publish in publish_times:
        slots_by_day.setdefault(publish.date(), set()).add(publish.time())
    seen = Counter(slot for slots in slots_by_day.values() for slot in slots)
    usual = {slot for slot, count in seen.items() if count * 2 >= len(slots_by_day)}

    for publish_day in sorted(slots_by_day):
        slots = slots_by_day[publish_day]
        for late_slot in sorted(slots - usual):
            skipped = sorted(s for s in usual - slots if s < late_slot)
            if not skipped:
                continue
            skipped_at = datetime.combine(publish_day, skipped[-1], tzinfo=UTC)
            published_at = datetime.combine(publish_day, late_slot, tzinfo=UTC)
            skipped_local = skipped_at.astimezone(LONDON)
            rule = CutoffRule(-1, time((skipped_local.hour + 1) % 24))
            delivery_date = published_at.astimezone(LONDON).date() + timedelta(days=1)
            if not first <= delivery_date <= last:
                continue
            suggested_at = resolve_rule(delivery_date, rule.day_offset, rule.local_time)
            if skipped_at < suggested_at < published_at:
                data = {
                    "publishTime": format_utc(published_at),
                    "missingSlot": f"{skipped_local:%H:%M}",
                }
                return FeaturedDay("OFF_SCHEDULE_VINTAGE", delivery_date, rule, data)
    return None


def _pooled_warnings(days: list[DayAnalysis]) -> list[AnalysisWarning]:
    by_code: dict[WarningCode, list[AnalysisWarning]] = {}
    for day in days:
        for warning in day.warnings:
            by_code.setdefault(warning.code, []).append(warning)

    pooled = []
    for code, found in by_code.items():
        template = SUMMARY_MESSAGES.get(code, "{code} on {days} of {total} days.")
        pooled.append(
            AnalysisWarning(
                code=code,
                severity="WARNING" if any(w.severity == "WARNING" for w in found) else "INFO",
                scope=found[0].scope,
                message=template.format(code=code, days=len(found), total=len(days)),
                data={"days": len(found)},
                count=sum(w.affected_count for w in found),
            )
        )
    return sort_warnings(pooled)


def _mae(day: DayAnalysis) -> float:
    return day.metrics.mae or 0.0


def _bias(day: DayAnalysis) -> float:
    return day.metrics.bias or 0.0


def _mae_and_bias(day: DayAnalysis) -> dict[str, float]:
    return {"mae": _mae(day), "bias": _bias(day)}
