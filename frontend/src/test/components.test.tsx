// @vitest-environment jsdom
import { afterEach, describe, expect, it } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { daySchema } from "../api/schemas";
import { Inspector } from "../features/replay/Inspector";
import { Warnings } from "../components/ui";
import { statusLabels, warningLabels } from "../lib/status";
import { fixture } from "./contract";
const data = daySchema.parse(fixture("analysis_synthetic_edge-cases.json"));
const oneOfEachStatus = [
  ...new Map(data.intervals.map((i) => [i.status, i])).values(),
];
afterEach(cleanup);
describe("evidence presentation", () => {
  for (const interval of oneOfEachStatus)
    it(`explains ${interval.status}`, () => {
      render(<Inspector data={data} interval={interval} />);
      expect(
        screen.getByText(statusLabels[interval.status]),
      ).toBeInTheDocument();
      if (interval.exclusionReason)
        expect(
          screen.getAllByText(interval.exclusionReason, { exact: false })
            .length,
        ).toBeGreaterThan(0);
    });
  for (const code of Object.keys(warningLabels))
    it(`presents ${code}`, () => {
      render(
        <Warnings
          warnings={[
            {
              code,
              severity: "WARNING",
              scope: "ANALYSIS",
              message: "Evidence detail",
              affectedCount: 0,
              affectedIntervals: [],
              data: null,
            },
          ]}
        />,
      );
      expect(screen.getByText(warningLabels[code])).toBeInTheDocument();
      expect(screen.getByText("Evidence detail")).toBeInTheDocument();
    });
  it("uses a neutral fallback for future warning codes", () => {
    render(
      <Warnings
        warnings={[
          {
            code: "FUTURE_CODE",
            severity: "WARNING",
            scope: "ANALYSIS",
            message: "New server detail",
            affectedCount: 0,
            affectedIntervals: [],
            data: null,
          },
        ]}
      />,
    );
    expect(screen.getByText("Other")).toBeVisible();
    expect(screen.getByText("New server detail")).toBeVisible();
  });
  it("shows information as a single line without a title", () => {
    render(
      <Warnings
        warnings={[
          {
            code: "NEWER_VERSION_AFTER_CUTOFF",
            severity: "INFO",
            scope: "SOURCE",
            message: "A newer forecast was not used.",
            affectedCount: 0,
            affectedIntervals: [],
            data: null,
          },
        ]}
      />,
    );
    expect(screen.getByText("A newer forecast was not used.")).toBeVisible();
    expect(
      screen.queryByText(warningLabels.NEWER_VERSION_AFTER_CUTOFF),
    ).toBeNull();
  });
});
