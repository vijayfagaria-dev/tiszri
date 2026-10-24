import type { DayAnalysis } from "../../api/schemas";
import { useEffect, useRef } from "react";
import { minutes, number, stamp, time } from "../../lib/format";
import { buckets, directionLabel, statusLabels } from "../../lib/status";

interface Props {
  data: DayAnalysis;
  active: number;
  filter: string;
  sort: string;
  select: (period: number) => void;
  onSort: (sort: string) => void;
  onFilter: (filter: string) => void;
}
export function IntervalLedger({
  data,
  active,
  filter,
  sort,
  select,
  onSort,
  onFilter,
}: Props) {
  const scrollArea = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const container = scrollArea.current;
    const row = container?.querySelector<HTMLElement>(
      `[data-period="${active}"]`,
    );
    if (!container || !row) return;
    const rowBox = row.getBoundingClientRect();
    const containerBox = container.getBoundingClientRect();
    if (rowBox.bottom > containerBox.bottom)
      container.scrollTop += rowBox.bottom - containerBox.bottom;
    else if (rowBox.top < containerBox.top + 32)
      container.scrollTop += rowBox.top - containerBox.top - 32;
  }, [active, filter, sort]);
  const visible = data.intervals.filter(
    (i) => filter === "All" || buckets[filter]?.includes(i.status),
  );
  const rows =
    sort === "error"
      ? [...visible].sort(
          (a, b) => (b.error?.absolute ?? -1) - (a.error?.absolute ?? -1),
        )
      : visible;
  const selectedHidden = !visible.some((i) => i.settlementPeriod === active);
  return (
    <section className="ledger panel" id="interval-ledger">
      <div className="ledger-heading">
        <h2>Interval ledger</h2>
        <label>
          Sort{" "}
          <select
            aria-label="Sort intervals"
            value={sort}
            onChange={(e) => onSort(e.target.value)}
          >
            <option value="time">Chronological</option>
            <option value="error">Largest error</option>
          </select>
        </label>
      </div>
      <div className="filters" role="group" aria-label="Coverage filters">
        {["All", ...Object.keys(buckets)].map((bucket) => (
          <button
            key={bucket}
            aria-pressed={filter === bucket}
            onClick={() => onFilter(bucket)}
          >
            {bucket}
            <span>
              {bucket === "All"
                ? data.metadata.counts.expected
                : buckets[bucket].reduce(
                    (n, s) => n + data.metadata.counts.byStatus[s],
                    0,
                  )}
            </span>
          </button>
        ))}
      </div>
      {selectedHidden && (
        <p role="status" className="notice">
          Selected interval {active} is outside this filter.{" "}
          <button onClick={() => onFilter("All")}>Clear filter</button>
        </p>
      )}
      <div className="table-scroll ledger-scroll" ref={scrollArea}>
        <table>
          <caption className="sr-only">
            Half-hourly forecast evidence in Europe/London. Values in MW.
          </caption>
          <thead>
            <tr>
              <th>#</th>
              <th>Delivery time</th>
              <th>Status</th>
              <th>Forecast MW</th>
              <th>Actual MW</th>
              <th>Error MW</th>
              <th>Vintage</th>
              <th>Lead / age</th>
              <th>Forecast hour</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((i) => (
              <tr
                key={i.settlementPeriod}
                data-period={i.settlementPeriod}
                className={i.settlementPeriod === active ? "selected" : ""}
                aria-selected={i.settlementPeriod === active}
              >
                <td>
                  <button
                    aria-label={`Inspect interval ${i.settlementPeriod}`}
                    onClick={() => select(i.settlementPeriod)}
                  >
                    {i.settlementPeriod}
                  </button>
                </td>
                <td>{time(i.startTime)}</td>
                <td>
                  <span
                    className={`status-chip ${i.status === "MATCHED" ? i.error?.direction.toLowerCase() : "excluded"}`}
                  >
                    {statusLabels[i.status]}
                    {i.error && ` · ${directionLabel(i.error.direction)}`}
                  </span>
                </td>
                <td>{number(i.forecast?.generation)}</td>
                <td>{number(i.actual?.generation)}</td>
                <td
                  className={i.error?.direction === "UNDER" ? "teal" : "amber"}
                >
                  {number(i.error?.signed, true)}
                </td>
                <td>
                  {i.forecast ? stamp(i.forecast.publishTime) : "Unavailable"}
                </td>
                <td>
                  {i.forecast
                    ? `${minutes(i.forecast.leadMinutes)} / ${minutes(i.forecast.ageAtCutoffMinutes)}`
                    : "Unavailable"}
                </td>
                <td>
                  {i.forecast
                    ? `${time(i.forecast.periodStart)} – ${time(i.forecast.periodEnd)}`
                    : "Unavailable"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && (
          <p className="empty-filter">No intervals in this filter.</p>
        )}
      </div>
    </section>
  );
}
