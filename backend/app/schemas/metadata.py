"""Response model for GET /metadata: static configuration, presets, units and definitions."""

from pydantic import Field

from app.analysis.cutoffs import PRESETS
from app.core.config import Settings
from app.models.analysis import CutoffRule
from app.schemas.common import (
    ALGORITHM_VERSION,
    CONTRACT_VERSION,
    POLICY_IDS,
    ApiModel,
    CutoffRuleOut,
    UnitInfoOut,
    rule_out,
    units,
)


class DateWindowOut(ApiModel):
    from_: str = Field(alias="from")
    to: str


class SummaryDefaultsOut(DateWindowOut):
    rule: CutoffRuleOut


class CutoffRangeOut(ApiModel):
    min_day_offset: int
    max_day_offset: int
    max_local_time_at_max_offset: str = "00:00"


class PresetOut(ApiModel):
    id: str
    rule: CutoffRuleOut
    is_default: bool


class CutoffSettingsOut(ApiModel):
    default_rule: CutoffRuleOut
    range: CutoffRangeOut
    presets: list[PresetOut]


class DatasetOut(ApiModel):
    id: str
    role: str
    filter: dict[str, str] | None
    resolution_minutes: int
    unit: UnitInfoOut


class PolicyOut(ApiModel):
    id: str
    text: str


class PoliciesOut(ApiModel):
    selection: PolicyOut
    mapping: PolicyOut
    duplicates: PolicyOut
    percentiles: PolicyOut


class MetricDefinitionOut(ApiModel):
    id: str
    formula: str
    description: str


class MetadataResponse(ApiModel):
    contract_version: str
    algorithm_version: str
    business_timezone: str = "Europe/London"
    supported_delivery_window: DateWindowOut
    summary_defaults: SummaryDefaultsOut
    cutoff: CutoffSettingsOut
    datasets: list[DatasetOut]
    policies: PoliciesOut
    metric_definitions: list[MetricDefinitionOut]


def default_rule(settings: Settings) -> CutoffRule:
    return CutoffRule(settings.default_cutoff_day_offset, settings.default_cutoff_local_time)


def metadata_response(settings: Settings) -> MetadataResponse:
    default = default_rule(settings)
    actual_unit, forecast_unit = units(settings)
    return MetadataResponse(
        contract_version=CONTRACT_VERSION,
        algorithm_version=ALGORITHM_VERSION,
        supported_delivery_window=DateWindowOut(
            from_=settings.supported_date_from.isoformat(),
            to=settings.supported_date_to.isoformat(),
        ),
        summary_defaults=SummaryDefaultsOut(
            from_=settings.summary_default_from.isoformat(),
            to=settings.summary_default_to.isoformat(),
            rule=rule_out(default),
        ),
        cutoff=CutoffSettingsOut(
            default_rule=rule_out(default),
            range=CutoffRangeOut(
                min_day_offset=settings.cutoff_min_day_offset,
                max_day_offset=settings.cutoff_max_day_offset,
            ),
            presets=[
                PresetOut(id=name, rule=rule_out(rule), is_default=rule == default)
                for name, rule in PRESETS.items()
            ],
        ),
        datasets=[
            DatasetOut(
                id="FUELHH",
                role="ACTUAL",
                filter={"fuelType": "WIND"},
                resolution_minutes=30,
                unit=actual_unit,
            ),
            DatasetOut(
                id="WINDFOR",
                role="FORECAST",
                filter=None,
                resolution_minutes=60,
                unit=forecast_unit,
            ),
        ],
        policies=PoliciesOut(
            selection=PolicyOut(
                id=POLICY_IDS["selection"],
                text="For each hour, only forecasts published at or before the decision time are "
                "eligible; the one with the latest publish time is used.",
            ),
            mapping=PolicyOut(
                id=POLICY_IDS["mapping"],
                text="Each hourly forecast applies to both settlement periods of its hour.",
            ),
            duplicates=PolicyOut(
                id=POLICY_IDS["duplicates"],
                text="Records sharing the latest publish time count once if their values agree and "
                "are excluded if they differ. An older forecast is never used as a fallback.",
            ),
            percentiles=PolicyOut(
                id="NEAREST_RANK",
                text="The p-th percentile is the value at rank ceil(p * n) of the sorted values.",
            ),
        ),
        metric_definitions=[
            MetricDefinitionOut(
                id="MAE",
                formula="(1/n) * sum(|F - A|)",
                description="Average size of the error, ignoring direction.",
            ),
            MetricDefinitionOut(
                id="RMSE",
                formula="sqrt((1/n) * sum((F - A)^2))",
                description="Like MAE, but gives large misses more weight.",
            ),
            MetricDefinitionOut(
                id="BIAS",
                formula="(1/n) * sum(F - A)",
                description="Average signed error. Positive means over-forecasting. Errors of "
                "opposite sign cancel, so read it alongside MAE.",
            ),
        ],
    )
