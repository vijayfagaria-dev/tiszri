import math

import pytest

from app.analysis.metrics import compute_metrics, histogram, nearest_rank

pytestmark = pytest.mark.req("FR-016", "FR-017", "FR-026", "AC-007", "AC-008")


@pytest.mark.parametrize(
    ("errors", "mae", "rmse", "bias"),
    [
        ([100, 300], 200.0, math.sqrt(50_000), 200.0),
        ([-100, -300], 200.0, math.sqrt(50_000), -200.0),
        ([100, -100], 100.0, 100.0, 0.0),
        ([0, 0, 0], 0.0, 0.0, 0.0),
        ([7], 7.0, 7.0, 7.0),
    ],
    ids=["over", "under", "mixed", "zero", "single"],
)
def test_metrics(errors: list[int], mae: float, rmse: float, bias: float) -> None:
    metrics = compute_metrics(errors)
    assert metrics.n == len(errors)
    assert (metrics.mae, metrics.rmse, metrics.bias) == pytest.approx((mae, rmse, bias))


def test_no_pairs_means_no_metrics_rather_than_zero() -> None:
    metrics = compute_metrics([])
    assert (metrics.n, metrics.mae, metrics.rmse, metrics.bias) == (0, None, None, None)


def test_direction_counts() -> None:
    metrics = compute_metrics([5, -3, 0, 2])
    assert (metrics.over, metrics.under, metrics.exact) == (2, 1, 1)


@pytest.mark.req("NFR-002")
def test_metrics_are_not_rounded() -> None:
    assert compute_metrics([1, 2]).mae == 1.5
    assert compute_metrics([1, 1, 2]).bias == 4 / 3


def test_nearest_rank() -> None:
    values = list(range(1, 11))
    assert [nearest_rank(values, p) for p in (10, 50, 90, 100)] == [1, 5, 9, 10]
    # 0.95 * 20 is 19.000000000000004 in floating point; the rank must still be 19.
    assert nearest_rank(list(range(1, 21)), 95) == 19


def test_histogram_bins_are_contiguous_and_floor_negatives() -> None:
    assert histogram([-1, 0, 499, 1600], width=500) == [
        (-500, 1),
        (0, 2),
        (500, 0),
        (1000, 0),
        (1500, 1),
    ]
    assert histogram([], width=500) == []
