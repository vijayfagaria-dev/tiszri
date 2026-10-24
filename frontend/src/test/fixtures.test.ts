import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import { daySchema, metadataSchema, summarySchema } from "../api/schemas";
const directory = new URL("../../public/_fixtures/", import.meta.url);
describe("synthetic contract catalogue", () => {
  for (const name of readdirSync(directory).filter((n) =>
    n.endsWith(".json"),
  )) {
    it(name, () => {
      const raw = JSON.parse(readFileSync(new URL(name, directory), "utf8"));
      if (name === "metadata.json") {
        expect(metadataSchema.safeParse(raw).success).toBe(true);
        return;
      }
      const data = name.startsWith("day_")
        ? daySchema.parse(raw)
        : summarySchema.parse(raw);
      const { counts, coverage } = data.metadata;
      expect(data.metadata.requestId).toMatch(/^synthetic-/);
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
          if (i.forecast) {
            expect(Date.parse(i.forecast.publishTime)).toBeLessThanOrEqual(
              Date.parse(data.query.decisionCutoff.utc),
            );
            const pair = data.intervals[index % 2 ? index - 1 : index + 1];
            if (pair?.forecast)
              expect(i.forecast.generation).toBe(pair.forecast.generation);
          }
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
