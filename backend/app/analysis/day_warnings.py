"""Warnings describing a day analysis. Clients key their wording on the code."""

from datetime import datetime

from app.models.analysis import AnalysisWarning, DayAnalysis
from app.models.enums import Flag, Status, WarningCode
from app.utils.dates import describe_london, format_utc


def day_warnings(day: DayAnalysis) -> list[AnalysisWarning]:
    warnings = []
    excluded = [i.start for i in day.intervals if i.status != Status.MATCHED]

    if day.matched == 0:
        warnings.append(
            AnalysisWarning(
                code=WarningCode.NO_MATCHED_INTERVALS,
                severity="WARNING",
                scope="ANALYSIS",
                message="No settlement period has both a forecast available at the decision "
                "time and an actual value, so accuracy metrics are unavailable.",
                intervals=excluded,
                data={"expected": day.expected},
            )
        )
    elif day.matched < day.expected:
        warnings.append(
            AnalysisWarning(
                code=WarningCode.PARTIAL_COVERAGE,
                severity="WARNING",
                scope="ANALYSIS",
                message=f"{day.matched} of {day.expected} settlement periods could be "
                "compared; metrics cover only those.",
                intervals=excluded,
                data={"matched": day.matched, "expected": day.expected},
            )
        )

    when = describe_london(day.cutoff.utc)
    if day.cutoff.position == "INSIDE_DELIVERY":
        warnings.append(
            AnalysisWarning(
                code=WarningCode.CUTOFF_INSIDE_DELIVERY_DAY,
                severity="WARNING",
                scope="ANALYSIS",
                message=f"The decision time ({when}) falls inside the delivery day; some "
                "forecasts may have been issued after their period began.",
                data={"cutoff": format_utc(day.cutoff.utc)},
            )
        )
    elif day.cutoff.position == "AFTER_DELIVERY":
        warnings.append(
            AnalysisWarning(
                code=WarningCode.HINDSIGHT_CUTOFF,
                severity="WARNING",
                scope="ANALYSIS",
                message=f"The decision time ({when}) is after the delivery day ended. This is "
                "a hindsight replay, not a decision-time view.",
                data={"cutoff": format_utc(day.cutoff.utc)},
            )
        )

    if day.newer_after_cutoff:
        published = describe_london(day.newer_after_cutoff)
        warnings.append(
            AnalysisWarning(
                code=WarningCode.NEWER_VERSION_AFTER_CUTOFF,
                severity="INFO",
                scope="SOURCE",
                message=f"A newer forecast was published at {published}, after the decision "
                "time, so it wasn't used.",
                data={"publishTime": format_utc(day.newer_after_cutoff)},
            )
        )

    late = _starts_with_flag(day, Flag.ISSUED_AFTER_DELIVERY_START)
    if late:
        warnings.append(
            AnalysisWarning(
                code=WarningCode.ISSUED_AFTER_DELIVERY_START,
                severity="WARNING",
                scope="INTERVAL",
                message=f"{len(late)} settlement periods use a forecast published after the "
                "period started.",
                intervals=late,
                data={"count": len(late)},
            )
        )

    duplicate_flags = {
        "WINDFOR": Flag.DUPLICATE_EQUIVALENT_FORECAST,
        "FUELHH": Flag.DUPLICATE_EQUIVALENT_ACTUAL,
    }
    for dataset, flag in duplicate_flags.items():
        duplicated = _starts_with_flag(day, flag)
        if duplicated:
            warnings.append(
                AnalysisWarning(
                    code=WarningCode.DUPLICATE_EQUIVALENT,
                    severity="INFO",
                    scope="INTERVAL",
                    message=f"{len(duplicated)} settlement periods had duplicate {dataset} "
                    "records with the same value; each was counted once.",
                    intervals=duplicated,
                    data={"dataset": dataset, "count": len(duplicated)},
                )
            )

    conflict_statuses = {"WINDFOR": Status.AMBIGUOUS_FORECAST, "FUELHH": Status.AMBIGUOUS_ACTUAL}
    for dataset, status in conflict_statuses.items():
        conflicting = [i.start for i in day.intervals if i.status == status]
        if conflicting:
            warnings.append(
                AnalysisWarning(
                    code=WarningCode.DUPLICATE_CONFLICT,
                    severity="WARNING",
                    scope="INTERVAL",
                    message=f"{len(conflicting)} settlement periods were excluded because "
                    f"{dataset} reported conflicting values for the same time.",
                    intervals=conflicting,
                    data={"dataset": dataset, "count": len(conflicting)},
                )
            )

    inconsistent = _starts_with_flag(day, Flag.ACTUAL_TIMESTAMP_INCONSISTENT)
    if inconsistent:
        warnings.append(
            AnalysisWarning(
                code=WarningCode.ACTUAL_TIMESTAMP_INCONSISTENT,
                severity="WARNING",
                scope="INTERVAL",
                message=f"{len(inconsistent)} FUELHH records have a settlement date or period "
                "that disagrees with their start time; they were matched by start time.",
                intervals=inconsistent,
                data={"count": len(inconsistent)},
            )
        )

    return sort_warnings(warnings)


def sort_warnings(warnings: list[AnalysisWarning]) -> list[AnalysisWarning]:
    """WARNING before INFO, then alphabetically by code."""
    return sorted(warnings, key=lambda w: (w.severity != "WARNING", w.code))


def _starts_with_flag(day: DayAnalysis, flag: Flag) -> list[datetime]:
    return [i.start for i in day.intervals if flag in i.flags]
