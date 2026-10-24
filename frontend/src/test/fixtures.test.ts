import { describe, expect, it } from "vitest";
import {
  daySchema,
  errorSchema,
  metadataSchema,
  summarySchema,
} from "../api/schemas";
import { fixture } from "./contract";
const index = fixture("index.json") as { file: string }[];
describe("backend fixtures pass the frontend's runtime checks", () => {
  for (const { file } of index) {
    if (file.startsWith("versions_")) continue; // endpoint not used by the app yet
    it(file, () => {
      const raw = fixture(file);
      if (file === "metadata.json") {
        expect(metadataSchema.safeParse(raw).success).toBe(true);
        return;
      }
      if (file.startsWith("error_")) {
        expect(errorSchema.safeParse(raw).success).toBe(true);
        return;
      }
      const data = file.startsWith("analysis_")
        ? daySchema.parse(raw)
        : summarySchema.parse(raw);
      const { counts, coverage } = data.metadata;
      expect(counts.expected).toBe(counts.matched + counts.excluded);
      expect(Object.values(counts.byStatus).reduce((a, b) => a + b, 0)).toBe(
        counts.expected,
      );
      expect(coverage).toBe(counts.matched / counts.expected);
      expect(data.metrics.n).toBe(counts.matched);
      expect(
        Object.values(data.metrics.directionCounts).reduce((a, b) => a + b, 0),
      ).toBe(counts.matched);
      if ("intervals" in data) {
        expect(data.intervals).toHaveLength(counts.expected);
        const errors = data.intervals.flatMap((i) =>
          i.error ? [i.error.signed] : [],
        );
        if (errors.length) {
          expect(data.metrics.mae).toBeCloseTo(
            errors.reduce((a, b) => a + Math.abs(b), 0) / errors.length,
            8,
          );
          expect(data.metrics.bias).toBeCloseTo(
            errors.reduce((a, b) => a + b, 0) / errors.length,
            8,
          );
          expect(data.metrics.rmse).toBeCloseTo(
            Math.sqrt(errors.reduce((a, b) => a + b * b, 0) / errors.length),
            8,
          );
        } else
          expect([
            data.metrics.mae,
            data.metrics.rmse,
            data.metrics.bias,
          ]).toEqual([null, null, null]);
        data.intervals.forEach((i, index) => {
          expect(i.settlementPeriod).toBe(index + 1);
          expect(Date.parse(i.endTime) - Date.parse(i.startTime)).toBe(1800000);
          expect(i.error !== null).toBe(i.status === "MATCHED");
          if (i.forecast)
            expect(Date.parse(i.forecast.publishTime)).toBeLessThanOrEqual(
              Date.parse(data.query.decisionCutoff.utc),
            );
          if (i.error)
            expect(i.error.signed).toBe(
              i.forecast!.generation! - i.actual!.generation!,
            );
        });
      } else
        expect(
          data.distribution.histogram.bins.reduce((a, b) => a + b.count, 0),
        ).toBe(counts.matched);
    });
  }
});
