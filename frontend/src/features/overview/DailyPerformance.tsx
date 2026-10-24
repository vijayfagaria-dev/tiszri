import { Link } from "react-router-dom";
import { CalendarDays } from "lucide-react";
import type { Metadata, Summary } from "../../api/schemas";
import { dateLabel, number } from "../../lib/format";
import { replayLink } from "../../app/url";
interface Props {
  data: Summary;
  metadata: Metadata;
  search: URLSearchParams;
  onViewChange: (view: string) => void;
}
export function DailyPerformance({
  data,
  metadata,
  search,
  onViewChange,
}: Props) {
  const ranked = search.get("view") === "ranked";
  const days = ranked
    ? [...data.days].sort((a, b) => (b.mae ?? -1) - (a.mae ?? -1))
    : data.days;
  return (
    <section
      className={`daily panel ${ranked ? "ranked" : ""}`}
      aria-label="Daily performance"
    >
      <div className="section-title">
        <CalendarDays size={23} />
        <div>
          <h2>Daily performance</h2>
          <p>
            {ranked
              ? "Highest MAE first"
              : "Select a day to explore the evidence"}
          </p>
        </div>
      </div>
      <div className="days">
        {days.map((d) => (
          <Link
            className={`day ${d.resultState.toLowerCase()}`}
            key={d.deliveryDate}
            to={replayLink(d.deliveryDate, data.query.rule, metadata, search)}
            aria-label={`${dateLabel(d.deliveryDate)}, ${d.resultState}, MAE ${number(d.mae)} MW`}
          >
            <span
              className={`day-dot ${d.mae != null && d.mae > 3000 ? "high" : d.bias != null && d.bias < 0 ? "low" : ""}`}
            >
              {d.resultState !== "COMPLETE"
                ? "!"
                : d.bias != null && d.bias < 0
                  ? "↓"
                  : "↑"}
            </span>
            <span>
              {d.deliveryDate.endsWith("02-01")
                ? "1 Feb"
                : Number(d.deliveryDate.slice(-2))}
            </span>
            <span className="day-tip">
              {dateLabel(d.deliveryDate)} · {number(d.mae)} MW MAE
              <br />
              {d.matched}/{d.expected} matched
            </span>
            {ranked && <small>{number(d.mae)} MW</small>}
          </Link>
        ))}
      </div>
      <div className="segmented">
        <button aria-pressed={!ranked} onClick={() => onViewChange("calendar")}>
          Calendar
        </button>
        <button aria-pressed={ranked} onClick={() => onViewChange("ranked")}>
          Ranked
        </button>
      </div>
    </section>
  );
}
