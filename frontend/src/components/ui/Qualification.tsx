import type { DayAnalysis, Summary } from "../../api/schemas";

export function Qualification({ data }: { data: DayAnalysis | Summary }) {
  return data.metrics.qualified ? (
    <p className="qualification">
      {data.resultState === "EMPTY"
        ? "Unavailable — no matched half-hours."
        : "Partial evidence — metrics describe matched half-hours only."}{" "}
      {data.metadata.counts.matched} of {data.metadata.counts.expected} matched.
    </p>
  ) : null;
}
