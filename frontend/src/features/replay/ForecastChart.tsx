import { seriesPath } from "./chartGeometry";
import { useState } from "react";
import type { DayAnalysis } from "../../api/schemas";
import { number, time, mw } from "../../lib/format";
import { directionLabel, statusLabels } from "../../lib/status";
export function ForecastChart({
  data,
  active,
  select,
}: {
  data: DayAnalysis;
  active: number;
  select: (period: number) => void;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const { intervals } = data;
  const selected = intervals[(hover ?? active) - 1] ?? intervals[0];
  const ceiling = Math.max(
    3000,
    Math.ceil(
      Math.max(
        ...intervals.flatMap((i) => [
          i.forecast?.generation ?? 0,
          i.actual?.generation ?? 0,
        ]),
      ) / 3000,
    ) * 3000,
  );
  const x = (i: number) => 50 + (i / (intervals.length - 1)) * 910;
  const y = (v: number) => 235 - (v / ceiling) * 200;
  const selectedX = x(selected.settlementPeriod - 1);
  // The plot runs from 5% to 96% of the chart's width. Inset the strips below
  // so each cell is centred under its point (cells are 2px apart).
  const step = 91 / (intervals.length - 1);
  const underPlot = {
    paddingLeft: `calc(${5 - step / 2}% + 1px)`,
    paddingRight: `calc(${4 - step / 2}% + 1px)`,
  };
  return (
    <section className="chart-panel panel">
      <div className="chart-header">
        <h2>Forecast vs actual</h2>
        <div className="legend">
          <span>
            <i className="forecast-key" />
            Forecast (expected)
          </span>
          <span>
            <i className="actual-key" />
            Actual generation
          </span>
        </div>
        <span className="unit-tag">MW</span>
      </div>
      <figure
        className="forecast-figure"
        aria-label="Forecast versus actual generation by settlement period"
      >
        <svg
          viewBox="0 0 1000 280"
          role="img"
          aria-label="Interactive forecast and actual time series. Use the interval control or ledger to inspect evidence."
        >
          <defs>
            <linearGradient id="chart-fill" x1="0" y1="0" x2="0" y2="1">
              <stop stopColor="#8d73ec" stopOpacity=".19" />
              <stop offset="1" stopColor="#8d73ec" stopOpacity="0" />
            </linearGradient>
          </defs>
          {Array.from({ length: 5 }, (_, i) => (
            <g key={i}>
              <line
                x1="50"
                x2="960"
                y1={y((i * ceiling) / 4)}
                y2={y((i * ceiling) / 4)}
                className="chart-grid"
              />
              <text x="39" y={y((i * ceiling) / 4) + 4} textAnchor="end">
                {number((i * ceiling) / 4)}
              </text>
            </g>
          ))}
          {intervals
            .filter((_, i) => i % 6 === 0 || i === intervals.length - 1)
            .map((i) => (
              <g key={i.settlementPeriod}>
                <line
                  x1={x(i.settlementPeriod - 1)}
                  x2={x(i.settlementPeriod - 1)}
                  y1="35"
                  y2="235"
                  className="chart-grid"
                />
                <text x={x(i.settlementPeriod - 1)} y="260" textAnchor="middle">
                  {time(i.startTime).slice(0, 5)}
                </text>
              </g>
            ))}
          <path
            d={seriesPath(intervals, "forecast", x, y)}
            className="forecast-line"
          />
          <path
            d={seriesPath(intervals, "actual", x, y)}
            className="actual-line"
          />
          <line
            className="crosshair"
            x1={selectedX}
            x2={selectedX}
            y1="25"
            y2="235"
          />
          {(["forecast", "actual"] as const).map(
            (side) =>
              selected[side]?.generation != null && (
                <circle
                  key={side}
                  cx={selectedX}
                  cy={y(selected[side]!.generation!)}
                  r="4"
                  className={`${side}-point`}
                />
              ),
          )}
          {intervals.map((i, index) => (
            <rect
              key={i.settlementPeriod}
              x={x(index) - 10}
              y="25"
              width={Math.max(14, 910 / intervals.length)}
              height="210"
              fill="transparent"
              onMouseEnter={() => setHover(i.settlementPeriod)}
              onMouseLeave={() => setHover(null)}
              onClick={() => select(i.settlementPeriod)}
            >
              <title>
                {time(i.startTime)} · {statusLabels[i.status]}
              </title>
            </rect>
          ))}
        </svg>
        <figcaption>
          <span>
            Europe/London · {time(intervals[0].startTime).split(" ").at(-1)} ·
            Gaps indicate unavailable evidence
          </span>
          <a href="#interval-ledger">View equivalent table ↗</a>
        </figcaption>
      </figure>
      <div
        className="chart-readout"
        aria-live={hover == null ? "polite" : "off"}
      >
        <strong>
          {time(selected.startTime)} · SP {selected.settlementPeriod}
        </strong>
        <span className="purple">
          Forecast <b>{mw(selected.forecast?.generation)}</b>
        </span>
        <span>
          Actual <b>{mw(selected.actual?.generation)}</b>
        </span>
        <span
          className={selected.error?.direction === "UNDER" ? "teal" : "amber"}
        >
          {mw(selected.error?.signed, true)} ·{" "}
          {directionLabel(selected.error?.direction)}
        </span>
        <span>
          {statusLabels[selected.status]} · Vintage{" "}
          {selected.forecast
            ? time(selected.forecast.publishTime)
            : "unavailable"}
        </span>
      </div>
      <label className="interval-slider">
        Selected settlement period{" "}
        <strong>
          {active} / {intervals.length}
        </strong>
        <input
          type="range"
          min="1"
          max={intervals.length}
          value={active}
          onChange={(e) => select(Number(e.target.value))}
          aria-label="Selected settlement period"
          aria-valuetext={`${active}, ${time(intervals[active - 1]?.startTime ?? intervals[0].startTime)}`}
        />
      </label>
      <div className="ribbon-heading">
        <h3>Forecast vintage timeline</h3>
        <span>
          {data.highlights.versionsUsed.length} selected vintage
          {data.highlights.versionsUsed.length !== 1 ? "s" : ""} · publication
          evidence only
        </span>
      </div>
      <div className="vintage-ribbon" style={underPlot} aria-hidden="true">
        {intervals.map((i) => (
          <span
            key={i.settlementPeriod}
            onClick={() => select(i.settlementPeriod)}
            className={`${i.status !== "MATCHED" ? "excluded" : ""} ${i.settlementPeriod === active ? "active" : ""}`}
            title={`SP ${i.settlementPeriod} · ${i.forecast ? time(i.forecast.publishTime) : statusLabels[i.status]}`}
          />
        ))}
      </div>
      <div className="ribbon-heading">
        <h3>Error fingerprint</h3>
        <span>↑ too high · ↓ too low · hatched = excluded</span>
      </div>
      <div className="error-fingerprint" style={underPlot} aria-hidden="true">
        {intervals.map((i) => (
          <span
            key={i.settlementPeriod}
            className={`${i.settlementPeriod === active ? "active " : ""}${i.error ? i.error.direction.toLowerCase() : "excluded"}`}
            onClick={() => select(i.settlementPeriod)}
            title={`SP ${i.settlementPeriod} · ${mw(i.error?.signed, true)}`}
          >
            <i
              style={{
                height: `${i.error ? Math.max(3, Math.min(48, i.error.absolute / 150)) : 22}px`,
              }}
            />
          </span>
        ))}
      </div>
    </section>
  );
}
