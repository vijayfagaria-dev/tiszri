import type { Interval } from "../../api/schemas";
export function seriesPath(
  intervals: Interval[],
  side: "forecast" | "actual",
  x: (i: number) => number,
  y: (v: number) => number,
) {
  let path = "";
  let previous = false;
  intervals.forEach((interval, i) => {
    const value = interval[side]?.generation;
    if (
      value == null ||
      (side === "actual" && interval.status === "AMBIGUOUS_ACTUAL")
    ) {
      previous = false;
      return;
    }
    path += `${previous ? (side === "forecast" ? `H${x(i)}V` : "L") : "M"}${previous && side === "forecast" ? y(value) : `${x(i)},${y(value)}`} `;
    previous = true;
  });
  return path;
}
