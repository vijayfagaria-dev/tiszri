import { z } from "zod";

// Provisional contract 1.0.0 models. Replace with generated types when OpenAPI is supplied.
const count = z.number().int().nonnegative();
const instant = z.string().regex(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/);
const date = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);
const nullableNumber = z.number().finite().nullable();
export const statuses = [
  "MATCHED",
  "FORECAST_NOT_YET_PUBLISHED",
  "FORECAST_MISSING",
  "ACTUAL_MISSING",
  "FULLY_MISSING",
  "INVALID_VALUE",
  "AMBIGUOUS_FORECAST",
  "AMBIGUOUS_ACTUAL",
] as const;
export const presetIds = [
  "TWO_DAYS_BEFORE_0900",
  "MORNING_BEFORE_0900",
  "NOON_BEFORE_1200",
  "DELIVERY_START_0000",
  "AFTER_DELIVERY_0000",
] as const;
export const ruleSchema = z.object({
  dayOffset: z.number().int().min(-7).max(2),
  localTime: z.string().regex(/^([01]\d|2[0-3]):[0-5]\d$/),
});
const state = z.enum(["COMPLETE", "PARTIAL", "EMPTY"]);
const directions = z.object({ over: count, under: count, exact: count });
const cutoff = z.object({
  utc: instant,
  london: z.string(),
  source: z.enum(["EXPLICIT", "RULE", "DEFAULT"]),
  rule: ruleSchema.nullable(),
  presetId: z.enum(presetIds).nullable(),
  position: z.enum(["BEFORE_DELIVERY", "INSIDE_DELIVERY", "AFTER_DELIVERY"]),
});
const unit = z.object({
  unit: z.string(),
  meaning: z.string(),
  status: z.enum(["VERIFIED", "PENDING_VERIFICATION"]),
  evidence: z.string(),
});
const policy = z.object({ id: z.string(), text: z.string() });
export const metadataSchema = z.object({
  contractVersion: z.string(),
  algorithmVersion: z.string(),
  businessTimezone: z.literal("Europe/London"),
  supportedDeliveryWindow: z.object({ from: date, to: date }),
  summaryDefaults: z.object({ from: date, to: date, rule: ruleSchema }),
  cutoff: z.object({
    defaultRule: ruleSchema,
    range: z.object({
      minDayOffset: z.number(),
      maxDayOffset: z.number(),
      maxLocalTimeAtMaxOffset: z.string(),
    }),
    presets: z.array(
      z.object({
        id: z.enum(presetIds),
        rule: ruleSchema,
        isDefault: z.boolean(),
      }),
    ),
  }),
  datasets: z.array(
    z.object({
      id: z.enum(["FUELHH", "WINDFOR"]),
      role: z.enum(["ACTUAL", "FORECAST"]),
      filter: z.record(z.string(), z.unknown()).nullable(),
      resolutionMinutes: count,
      unit,
    }),
  ),
  policies: z.object({
    selection: policy,
    mapping: policy,
    duplicates: policy,
    percentiles: policy,
  }),
  metricDefinitions: z.array(
    z.object({ id: z.string(), formula: z.string(), description: z.string() }),
  ),
});
const provenance = z.object({
  dataset: z.enum(["FUELHH", "WINDFOR"]),
  role: z.enum(["ACTUAL", "FORECAST"]),
  filter: z.record(z.string(), z.unknown()).nullable(),
  requestedRange: z.object({
    from: z.string(),
    to: z.string(),
    basis: z.enum(["SETTLEMENT_DATE", "PUBLISH_TIME"]),
  }),
  rowsReceived: count,
  rowsRejected: count,
  rowsFiltered: count,
  fetchedAt: instant,
  cache: z.enum(["HIT", "MISS", "STALE", "BYPASS"]),
  versions: z
    .object({ coveringDay: count, eligible: count, afterCutoff: count })
    .nullable(),
});
const resultMetadata = z.object({
  contractVersion: z.string(),
  algorithmVersion: z.string(),
  requestId: z.string(),
  generatedAt: instant,
  sources: z.array(provenance),
  unit: z.object({ label: z.literal("MW"), actual: unit, forecast: unit }),
  resolution: z.object({
    deliveryMinutes: z.literal(30),
    forecastMinutes: z.literal(60),
  }),
  policyIds: z.object({
    selection: z.string(),
    mapping: z.string(),
    duplicates: z.string(),
  }),
  counts: z.object({
    expected: count,
    matched: count,
    excluded: count,
    byStatus: z.record(z.enum(statuses), count),
  }),
  coverage: z.number().min(0).max(1),
});
export const metricsSchema = z.object({
  n: count,
  mae: nullableNumber,
  rmse: nullableNumber,
  bias: nullableNumber,
  directionCounts: directions,
  signConvention: z.literal("FORECAST_MINUS_ACTUAL"),
  qualified: z.boolean(),
  unavailableReason: z.literal("NO_MATCHED_INTERVALS").nullable(),
});
const warning = z.object({
  code: z.string(),
  severity: z.enum(["INFO", "WARNING"]),
  scope: z.enum(["ANALYSIS", "INTERVAL", "SOURCE"]),
  message: z.string(),
  affectedCount: count,
  affectedIntervals: z.array(instant),
  data: z.record(z.string(), z.unknown()).nullable(),
});
export const intervalSchema = z.object({
  settlementPeriod: count,
  startTime: instant,
  endTime: instant,
  status: z.enum(statuses),
  exclusionReason: z.string().nullable(),
  forecast: z
    .object({
      generation: z.number().int().nullable(),
      publishTime: instant,
      periodStart: instant,
      periodEnd: instant,
      leadMinutes: z.number().int(),
      ageAtCutoffMinutes: count,
    })
    .nullable(),
  selection: z.object({
    eligibleCount: count,
    laterCount: count,
    earliestLaterPublishTime: instant.nullable(),
    conflictingValues: z.array(z.number().int()).nullable(),
  }),
  actual: z
    .object({
      generation: z.number().int().nullable(),
      publishTime: instant,
      conflictingValues: z.array(z.number().int()).nullable(),
    })
    .nullable(),
  error: z
    .object({
      signed: z.number().int(),
      absolute: count,
      direction: z.enum(["OVER", "UNDER", "EXACT"]),
    })
    .nullable(),
  flags: z.array(
    z.enum([
      "ISSUED_AFTER_DELIVERY_START",
      "DUPLICATE_EQUIVALENT_FORECAST",
      "DUPLICATE_EQUIVALENT_ACTUAL",
      "ACTUAL_TIMESTAMP_INCONSISTENT",
    ]),
  ),
});
export const daySchema = z.object({
  resultState: state,
  query: z.object({
    deliveryDate: date,
    decisionCutoff: cutoff,
    businessTimezone: z.literal("Europe/London"),
  }),
  metadata: resultMetadata,
  metrics: metricsSchema,
  highlights: z.object({
    largestOver: instant.nullable(),
    largestUnder: instant.nullable(),
    versionsUsed: z.array(instant),
    earliestCoveringPublishTime: instant.nullable(),
    newerVersionAfterCutoff: instant.nullable(),
  }),
  intervals: z.array(intervalSchema),
  warnings: z.array(warning),
});
export const summarySchema = z.object({
  resultState: state,
  query: z.object({
    from: date,
    to: date,
    rule: ruleSchema,
    ruleSource: z.enum(["RULE", "DEFAULT"]),
    presetId: z.enum(presetIds).nullable(),
    businessTimezone: z.literal("Europe/London"),
  }),
  metadata: resultMetadata.extend({ dayCount: count }),
  metrics: metricsSchema.extend({
    overShare: nullableNumber,
    underShare: nullableNumber,
  }),
  distribution: z.object({
    absError: z.object({
      p50: nullableNumber,
      p90: nullableNumber,
      p95: nullableNumber,
    }),
    signedError: z.object({ p10: nullableNumber, p90: nullableNumber }),
    histogram: z.object({
      binWidth: z.literal(500),
      bins: z.array(
        z.object({ lowerEdge: z.number(), upperEdge: z.number(), count }),
      ),
    }),
  }),
  days: z.array(
    z.object({
      deliveryDate: date,
      cutoff,
      resultState: state,
      expected: count,
      matched: count,
      mae: nullableNumber,
      rmse: nullableNumber,
      bias: nullableNumber,
      directionCounts: directions,
    }),
  ),
  featured: z.array(
    z.object({
      kind: z.string(),
      deliveryDate: date,
      suggestedRule: ruleSchema,
      data: z.record(z.string(), z.unknown()),
    }),
  ),
  sensitivity: z.object({
    onTheHourOnly: z.object({
      n: count,
      mae: nullableNumber,
      rmse: nullableNumber,
      bias: nullableNumber,
    }),
  }),
  warnings: z.array(warning),
});
export const readySchema = z.object({
  status: z.enum(["READY", "NOT_READY"]),
  checks: z.object({
    config: z.enum(["OK", "INVALID"]),
    upstream: z.enum(["OK", "UNKNOWN", "DEGRADED"]),
  }),
  lastUpstreamSuccessAt: instant.nullable(),
});
export const errorSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.array(
      z.object({ field: z.string(), reason: z.string(), message: z.string() }),
    ),
    requestId: z.string(),
    retryable: z.boolean(),
  }),
});
export type Metadata = z.infer<typeof metadataSchema>;
export type DayAnalysis = z.infer<typeof daySchema>;
export type Summary = z.infer<typeof summarySchema>;
export type Interval = z.infer<typeof intervalSchema>;
export type Rule = z.infer<typeof ruleSchema>;
export type Metrics = z.infer<typeof metricsSchema>;
export type Status = (typeof statuses)[number];
