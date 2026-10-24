import { Lightbulb } from "lucide-react";
import type { DayAnalysis } from "../../api/schemas";
import { MetricsGrid } from "../../components/ui";
import { percent } from "../../lib/format";

export function QuickSummary({ data }: { data: DayAnalysis }) {
  return (
    <aside className="quick-summary panel">
      <div className="summary-heading">
        <Lightbulb size={26} className="amber" />
        <div>
          <h2>Quick summary</h2>
          <p className="teal">
            {data.resultState === "COMPLETE"
              ? "All intervals matched."
              : data.resultState === "PARTIAL"
                ? "A partial picture."
                : "No matched evidence."}
          </p>
        </div>
      </div>
      <p className="muted">
        {data.metrics.bias == null
          ? "Metrics are unavailable."
          : data.metrics.bias >= 0
            ? "On average, the forecast was too high."
            : "On average, the forecast was too low."}
      </p>
      <div className="direction-counts">
        {(["over", "under", "exact"] as const).map((k) => (
          <div key={k}>
            <span>
              <i className={`status-dot ${k}`} />
              {k === "over"
                ? "Forecast too high"
                : k === "under"
                  ? "Forecast too low"
                  : "Exact"}
            </span>
            <b>{data.metrics.directionCounts[k]}</b>
          </div>
        ))}
      </div>
      <div className="coverage-summary">
        <div
          className="coverage-ring"
          style={{
            background: `conic-gradient(var(--teal) ${data.metadata.coverage * 360}deg, #203652 0)`,
          }}
        >
          <span>{percent(data.metadata.coverage)}</span>
        </div>
        <p>
          <b>
            {data.metadata.counts.matched} / {data.metadata.counts.expected}
          </b>
          <br />
          matched half-hours
        </p>
      </div>
      <MetricsGrid
        compact
        metrics={data.metrics}
        coverage={data.metadata.coverage}
        expected={data.metadata.counts.expected}
      />
      <p className="scope">
        Forecast accuracy only. This does not estimate how much electricity to
        buy.
      </p>
    </aside>
  );
}
