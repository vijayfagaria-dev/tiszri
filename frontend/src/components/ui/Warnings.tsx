import { Info, TriangleAlert } from "lucide-react";
import type { DayAnalysis } from "../../api/schemas";
import { warningLabels } from "../../lib/status";

// Warnings change how the numbers should be read, so they stand out and stay
// open. Info is routine context (e.g. a newer forecast arrived after the
// decision), so it is a single quiet line.
export function Warnings({
  warnings,
  select,
  actions = {},
}: {
  warnings: DayAnalysis["warnings"];
  select?: (instant: string) => void;
  actions?: Record<string, { label: string; run: () => void }>;
}) {
  if (!warnings.length) return null;
  return (
    <div className="warnings">
      {warnings.map((w, index) =>
        w.severity === "WARNING" ? (
          <div className="callout" key={`${w.code}-${index}`}>
            <TriangleAlert size={17} />
            <div>
              <strong>{warningLabels[w.code] ?? "Other"}</strong>
              <p>{w.message}</p>
              {actions[w.code] ? (
                <button className="link" onClick={actions[w.code].run}>
                  {actions[w.code].label}
                </button>
              ) : (
                select &&
                w.affectedIntervals.length > 0 && (
                  <button
                    className="link"
                    onClick={() => select(w.affectedIntervals[0])}
                  >
                    Inspect affected interval
                  </button>
                )
              )}
            </div>
          </div>
        ) : (
          <p className="note" key={`${w.code}-${index}`}>
            <Info size={14} />
            {w.message}
          </p>
        ),
      )}
    </div>
  );
}
