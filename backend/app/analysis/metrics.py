"""Accuracy metrics over signed errors (forecast - actual).

Generation values are integers, so the sums are exact and each metric does a single division.
"""

import math

from app.models.analysis import Metrics


def compute_metrics(errors: list[int]) -> Metrics:
    n = len(errors)
    over = sum(1 for e in errors if e > 0)
    under = sum(1 for e in errors if e < 0)
    if n == 0:
        return Metrics(n=0, mae=None, rmse=None, bias=None, over=0, under=0, exact=0)
    return Metrics(
        n=n,
        mae=sum(abs(e) for e in errors) / n,
        rmse=math.sqrt(sum(e * e for e in errors) / n),
        bias=sum(errors) / n,
        over=over,
        under=under,
        exact=n - over - under,
    )


def nearest_rank(sorted_values: list[int], percent: int) -> int:
    """Value at rank ceil(percent/100 * n). Integer maths avoids float rounding at the edges."""
    rank = -(-percent * len(sorted_values) // 100)
    return sorted_values[rank - 1]


def histogram(errors: list[int], width: int) -> list[tuple[int, int]]:
    """(lower edge, count) for contiguous [lower, lower + width) bins, empty bins included."""
    if not errors:
        return []
    counts: dict[int, int] = {}
    for error in errors:
        lower = error // width * width
        counts[lower] = counts.get(lower, 0) + 1
    return [
        (lower, counts.get(lower, 0)) for lower in range(min(counts), max(counts) + width, width)
    ]
