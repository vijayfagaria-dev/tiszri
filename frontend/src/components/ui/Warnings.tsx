import { Info } from "lucide-react";
import type { DayAnalysis } from "../../api/schemas";
import { warningLabels } from "../../lib/status";

export function Warnings({
  warnings,
  select,
}: {
  warnings: DayAnalysis["warnings"];
  select?: (instant: string) => void;
}) {
  return (
    <div className="warnings">
      {warnings.map((w) => (
        <details
          className={`notice ${w.severity === "INFO" ? "info" : ""}`}
          key={w.code}
          open={w.severity === "WARNING"}
        >
          <summary>
            <Info size={15} />
            {warningLabels[w.code] ?? "Other"}
            {w.affectedCount > 0 && ` · ${w.affectedCount}`}
          </summary>
          <p>{w.message}</p>
          {select && w.affectedIntervals.length > 0 && (
            <button onClick={() => select(w.affectedIntervals[0])}>
              Inspect affected interval
            </button>
          )}
        </details>
      ))}
    </div>
  );
}
