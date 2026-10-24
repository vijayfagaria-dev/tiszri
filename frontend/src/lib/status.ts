import type { Status } from "../api/schemas";
export const statusLabels: Record<Status, string> = {
  MATCHED: "Matched",
  FORECAST_NOT_YET_PUBLISHED: "Not yet published",
  FORECAST_MISSING: "Forecast missing",
  ACTUAL_MISSING: "Actual missing",
  FULLY_MISSING: "Fully missing",
  INVALID_VALUE: "Invalid value",
  AMBIGUOUS_FORECAST: "Ambiguous forecast",
  AMBIGUOUS_ACTUAL: "Ambiguous actual",
};
export const buckets: Record<string, Status[]> = {
  Matched: ["MATCHED"],
  "Not published": ["FORECAST_NOT_YET_PUBLISHED"],
  Missing: ["FORECAST_MISSING", "ACTUAL_MISSING", "FULLY_MISSING"],
  Invalid: ["INVALID_VALUE"],
  Ambiguous: ["AMBIGUOUS_FORECAST", "AMBIGUOUS_ACTUAL"],
};
export const directionLabel = (direction?: string) =>
  direction === "OVER"
    ? "Too high"
    : direction === "UNDER"
      ? "Too low"
      : direction === "EXACT"
        ? "Exact"
        : "Unavailable";
export const warningLabels: Record<string, string> = {
  PARTIAL_COVERAGE: "Partial coverage",
  NO_MATCHED_INTERVALS: "No matched intervals",
  NO_SOURCE_DATA: "Source data unavailable",
  SOURCE_ROWS_REJECTED: "Source rows rejected",
  NEWER_VERSION_AFTER_CUTOFF: "A newer forecast was not eligible",
  CUTOFF_INSIDE_DELIVERY_DAY: "Decision made during delivery",
  HINDSIGHT_CUTOFF: "Hindsight view",
  ISSUED_AFTER_DELIVERY_START: "Forecast issued after delivery started",
  DUPLICATE_EQUIVALENT: "Equivalent duplicates collapsed",
  DUPLICATE_CONFLICT: "Conflicting duplicates excluded",
  UNIT_PENDING_VERIFICATION: "Unit verification pending",
  FORECAST_RESOLUTION_IRREGULAR: "Off-grid forecasts rejected",
  ACTUAL_TIMESTAMP_INCONSISTENT: "Actual timestamp inconsistent",
  RETRIEVAL_WINDOW_MAY_BE_INSUFFICIENT: "Retrieval window may be insufficient",
};
