// @vitest-environment jsdom
import { afterEach, describe, expect, it } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { readFileSync } from "node:fs";
import { daySchema } from "../api/schemas";
import { Inspector } from "../features/replay/Inspector";
import { Warnings } from "../components/ui";
import { statusLabels, warningLabels } from "../lib/status";
const data = daySchema.parse(
  JSON.parse(
    readFileSync("public/_fixtures/day_2026-01-16_-1_0900_edge.json", "utf8"),
  ),
);
afterEach(cleanup);
describe("evidence presentation", () => {
  for (const interval of data.intervals.slice(0, 8))
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
            severity: "INFO",
            scope: "ANALYSIS",
            message: "New server detail",
            affectedCount: 0,
            affectedIntervals: [],
            data: null,
          },
        ]}
      />,
    );
    fireEvent.click(screen.getByText("Other"));
    expect(screen.getByText("New server detail")).toBeVisible();
  });
});
