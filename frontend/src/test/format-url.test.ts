import { describe, it, expect } from "vitest";
import { metadataSchema, daySchema } from "../api/schemas";
import { number, percent, time } from "../lib/format";
import { apiParams, canonicalParams } from "../app/url";
import { seriesPath } from "../features/replay/chartGeometry";
import { fixture } from "./contract";
const metadata = metadataSchema.parse(fixture("metadata.json"));
describe("display formatting and URL state", () => {
  it("keeps missing distinct from zero and floors coverage", () => {
    expect(number(null)).toBe("Unavailable");
    expect(number(0)).toBe("0");
    expect(percent(44 / 48)).toBe("91.6%");
    expect(number(1748, true)).toBe("+1,748");
  });
  it("formats London DST gap and fold instants without host timezone assumptions", () => {
    expect(time("2026-03-29T00:30:00Z")).toBe("00:30 GMT");
    expect(time("2026-03-29T01:30:00Z")).toBe("02:30 BST");
    expect(time("2026-10-25T00:30:00Z")).toBe("01:30 BST");
    expect(time("2026-10-25T01:30:00Z")).toBe("01:30 GMT");
  });
  it("canonicalizes defaults, drops unknown UI keys and maps only API parameters", () => {
    const p = canonicalParams(new URLSearchParams("noise=1"), true, metadata);
    expect(p.toString()).toBe("date=2026-01-16&rule=d1-0900");
    expect(apiParams(p, true, metadata).toString()).toBe(
      "deliveryDate=2026-01-16&cutoffDayOffset=-1&cutoffLocalTime=09%3A00",
    );
    expect(canonicalParams(p, true, metadata).toString()).toBe(p.toString());
  });
  it("keeps cutoff mutually exclusive and rejects unknown rules", () => {
    const p = canonicalParams(
      new URLSearchParams("rule=d1-0900&cutoff=2026-01-15T12%3A00%3A00Z"),
      true,
      metadata,
    );
    expect(p.has("rule")).toBe(false);
    expect(apiParams(p, true, metadata).has("cutoffLocalTime")).toBe(false);
    expect(() =>
      apiParams(new URLSearchParams("rule=bad"), true, metadata),
    ).toThrow("Unknown");
  });
  it("breaks chart lines at missing values instead of joining across gaps", () => {
    const data = daySchema.parse(fixture("analysis_2026-01-16_default.json"));
    const intervals = data.intervals.slice(0, 5);
    intervals[2].forecast = null;
    const path = seriesPath(
      intervals,
      "forecast",
      (i) => i,
      (v) => v,
    );
    expect(path.match(/M/g)).toHaveLength(2);
    expect(path).not.toContain("H2");
  });
});
