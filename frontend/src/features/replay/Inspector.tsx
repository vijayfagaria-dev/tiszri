import { Lightbulb, ScanLine } from "lucide-react";
import type { DayAnalysis, Interval } from "../../api/schemas";
import { directionLabel, statusLabels } from "../../lib/status";
import { minutes, number, stamp, time } from "../../lib/format";
export function Inspector({
  interval: i,
  data,
  id = "interval-inspector",
}: {
  interval: Interval;
  data: DayAnalysis;
  id?: string;
}) {
  const cutoff = data.query.decisionCutoff;
  return (
    <aside className="inspector panel" id={id} aria-label="Interval evidence">
      <h2>
        <span className="icon-orb purple">
          <ScanLine size={18} />
        </span>
        Why this forecast?
      </h2>
      <div className="inspector-story">
        <Lightbulb className="amber" size={25} />
        <p>
          {i.forecast ? (
            <>
              Interval {i.settlementPeriod} uses the hourly forecast published
              at <strong>{stamp(i.forecast.publishTime)}</strong>. This is the
              latest eligible publication at the applied decision time.
            </>
          ) : (
            <>{i.exclusionReason} No older vintage is used as a fallback.</>
          )}
        </p>
      </div>
      <div className="decision-timeline">
        <span>
          <i />
          {i.forecast ? time(i.forecast.publishTime) : "No selection"}
          <small>Forecast published</small>
        </span>
        <span>
          <i />
          {time(cutoff.utc)}
          <small>Decision time</small>
        </span>
      </div>
      <dl className="evidence-list">
        <dt>Settlement period</dt>
        <dd>{i.settlementPeriod}</dd>
        <dt>Delivery interval</dt>
        <dd>
          {time(i.startTime)} – {time(i.endTime)}
        </dd>
        <dt>Status</dt>
        <dd>{statusLabels[i.status]}</dd>
        <dt>Forecast period</dt>
        <dd>
          {i.forecast
            ? `${time(i.forecast.periodStart)} – ${time(i.forecast.periodEnd)}`
            : "Unavailable"}
        </dd>
        <dt>Eligible vintages</dt>
        <dd>{i.selection.eligibleCount}</dd>
        <dt>Later vintages</dt>
        <dd>{i.selection.laterCount}</dd>
        <dt>Selected vintage</dt>
        <dd>{i.forecast ? stamp(i.forecast.publishTime) : "Unavailable"}</dd>
        <dt>Lead time / age</dt>
        <dd>
          {i.forecast
            ? `${minutes(i.forecast.leadMinutes)} / ${minutes(i.forecast.ageAtCutoffMinutes)}`
            : "Unavailable"}
        </dd>
        <dt>Forecast value</dt>
        <dd>{number(i.forecast?.generation)} MW</dd>
        <dt>Actual value</dt>
        <dd>{number(i.actual?.generation)} MW</dd>
        <dt>Signed error</dt>
        <dd className={i.error?.direction === "UNDER" ? "teal" : "amber"}>
          {number(i.error?.signed, true)} MW (
          {directionLabel(i.error?.direction)})
        </dd>
        <dt>Absolute error</dt>
        <dd>{number(i.error?.absolute)} MW</dd>
      </dl>
      {i.exclusionReason && <p className="notice">{i.exclusionReason}</p>}
      {i.flags.map((flag) => (
        <p className="notice info" key={flag}>
          {flag.replaceAll("_", " ").toLowerCase()}
        </p>
      ))}
      <details>
        <summary>More evidence & UTC timestamps</summary>
        <div className="disclosure-body">
          <p>
            Delivery: {i.startTime} → {i.endTime}
          </p>
          <p>
            Decision: {cutoff.utc} ({cutoff.source})
          </p>
          <p>
            Forecast publication: {i.forecast?.publishTime ?? "Unavailable"}
          </p>
          <p>Actual publication: {i.actual?.publishTime ?? "Unavailable"}</p>
          <p>
            Next publication after cutoff:{" "}
            {i.selection.earliestLaterPublishTime
              ? stamp(i.selection.earliestLaterPublishTime)
              : "Unavailable"}
          </p>
          <p>
            Lead: {i.forecast?.leadMinutes ?? "Unavailable"} minutes from
            publication to delivery. Age:{" "}
            {i.forecast?.ageAtCutoffMinutes ?? "Unavailable"} minutes from
            publication to decision.
          </p>
          {i.selection.conflictingValues && (
            <p>
              Conflicting forecast values:{" "}
              {i.selection.conflictingValues.join(", ")} MW
            </p>
          )}
          {i.actual?.conflictingValues && (
            <p>
              Conflicting actual values: {i.actual.conflictingValues.join(", ")}{" "}
              MW
            </p>
          )}
        </div>
      </details>
    </aside>
  );
}
