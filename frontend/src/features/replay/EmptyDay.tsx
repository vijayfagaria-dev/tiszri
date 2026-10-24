import { useSearchParams } from "react-router-dom";
import type { DayAnalysis } from "../../api/schemas";
import { dayLabel, time } from "../../lib/format";

// Shown instead of the charts and tables when nothing could be compared.
export function EmptyDay({ data }: { data: DayAnalysis }) {
  const [p, setP] = useSearchParams();
  const { counts } = data.metadata;
  const first = data.highlights.earliestCoveringPublishTime;
  const notPublished =
    counts.byStatus.FORECAST_NOT_YET_PUBLISHED === counts.expected;
  return (
    <section className="panel empty-panel">
      <h2>
        {notPublished
          ? "No forecast had been published yet"
          : "Nothing to compare on this day"}
      </h2>
      <p>
        {notPublished
          ? `When the decision was made, no forecast covered ${dayLabel(data.query.deliveryDate)}.` +
            (first
              ? ` The first one was published on ${dayLabel(first)} at ${time(first)}.`
              : "")
          : (data.warnings.find((w) => w.code === "NO_MATCHED_INTERVALS")
              ?.message ??
            "No half-hour has both a forecast and an actual value, so accuracy can't be measured.")}
      </p>
      {notPublished && first && (
        <button
          onClick={() => {
            const next = new URLSearchParams(p);
            next.set("cutoff", first);
            next.delete("rule");
            setP(next);
          }}
        >
          Use the first forecast
        </button>
      )}
    </section>
  );
}
