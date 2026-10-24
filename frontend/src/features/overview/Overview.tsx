import { DailyPerformance } from "./DailyPerformance";
import { FeaturedReplays } from "./FeaturedReplays";
import { ErrorDistribution } from "./ErrorDistribution";
import { Link, useSearchParams } from "react-router-dom";
import {
  ArrowDown,
  ArrowRight,
  ArrowUp,
  Info,
  Sparkles,
  Wind,
} from "lucide-react";
import type { Metadata, Summary } from "../../api/schemas";
import type { ApiResult } from "../../api/client";
import { DecisionTimePicker, MetricsGrid, Warnings } from "../../components/ui";
import { WindArt } from "../../components/WindArt";
import { DateRange } from "./DateRange";
import { dateLabel, mw, percent } from "../../lib/format";
import { replayLink } from "../../app/url";
export function Overview({
  result,
  metadata,
}: {
  result: ApiResult<Summary>;
  metadata: Metadata;
}) {
  const data = result.response;
  const [search, setSearch] = useSearchParams();
  const over = (data.metrics.overShare ?? 0) >= (data.metrics.underShare ?? 0);
  const share = over ? data.metrics.overShare : data.metrics.underShare;
  // 90th percentile of forecast − actual: how far wind fell short of the forecast
  const shortfall = data.distribution.signedError?.p90 ?? null;
  const change = (values: Record<string, string>) => {
    const next = new URLSearchParams(search);
    for (const [key, value] of Object.entries(values)) next.set(key, value);
    setSearch(next);
  };
  const controls = (
    <div className="decision-control">
      <DecisionTimePicker
        metadata={metadata}
        alias={search.get("rule") ?? "d1-0900"}
        onChange={(alias) => change({ rule: alias })}
      />
      <DateRange
        metadata={metadata}
        from={data.query.from}
        to={data.query.to}
        onChange={(from, to) => change({ from, to })}
      />
    </div>
  );

  if (data.resultState === "EMPTY")
    return (
      <>
        <div className="hero-heading">
          <h1 className="empty-heading">
            How far could the forecast be trusted?
          </h1>
          {controls}
        </div>
        <section className="panel empty-panel">
          <h2>Nothing to compare at this decision time</h2>
          <p>
            None of the days from {dateLabel(data.query.from)} to{" "}
            {dateLabel(data.query.to, true)} had a forecast available by then,
            usually because forecasts only look about three days ahead. Choose a
            later decision time.
          </p>
          <button onClick={() => change({ rule: "d1-0900" })}>
            Switch to day before, 09:00
          </button>
        </section>
      </>
    );

  return (
    <>
      <section className="overview-hero">
        <WindArt />
        <div className="hero-heading">
          <p className="eyebrow">
            <Sparkles size={13} />
            JANUARY, DECODED.
          </p>
          {controls}
        </div>
        <div className="hero-content">
          <article className="trust-card">
            <h1>
              How far could the
              <br />
              forecast be <em>trusted?</em>
            </h1>
            <p className="hero-description">
              {over
                ? "The forecast expected more wind than actually arrived in most matched half-hours."
                : "The forecast expected less wind than actually arrived in most matched half-hours."}
            </p>
            <div className="trust-stat">
              <strong>
                {share == null ? "—" : `${Math.round(share * 100)}%`}
              </strong>
              <span>
                of matched half-hours
                <br />
                forecast <b>{over ? "too high" : "too low"}</b>
              </span>
            </div>
            <div
              className="direction-bar"
              role="img"
              aria-label={`Too high ${percent(data.metrics.overShare ?? 0)}, too low ${percent(data.metrics.underShare ?? 0)}, exact ${data.metrics.directionCounts.exact} intervals`}
            >
              <span
                style={{ width: `${(data.metrics.overShare ?? 0) * 100}%` }}
              />
              <span
                style={{ width: `${(data.metrics.underShare ?? 0) * 100}%` }}
              />
            </div>
            <div className="direction-labels">
              <span>
                <ArrowUp size={16} />
                Too high{" "}
                <b>
                  {data.metrics.overShare == null
                    ? "Unavailable"
                    : percent(data.metrics.overShare)}
                </b>
              </span>
              <span>
                <ArrowDown size={16} />
                Too low{" "}
                <b>
                  {data.metrics.underShare == null
                    ? "Unavailable"
                    : percent(data.metrics.underShare)}
                </b>
              </span>
            </div>
            {data.metrics.directionCounts.exact > 0 && (
              <small>
                {data.metrics.directionCounts.exact} exact half-hours
              </small>
            )}
            {shortfall != null && (
              <p className="planning">
                <strong>For planning:</strong>{" "}
                {shortfall > 0 ? (
                  <>
                    in 9 of 10 half-hours, actual wind was no more than{" "}
                    <b>{mw(shortfall)}</b> below the forecast.
                  </>
                ) : (
                  "in 9 of 10 half-hours, actual wind was at least as high as the forecast."
                )}
              </p>
            )}
          </article>
          <div className="hero-metrics">
            <MetricsGrid
              metrics={data.metrics}
              coverage={data.metadata.coverage}
              expected={data.metadata.counts.expected}
            />
          </div>
          <aside className="glance panel">
            <div className="glance-art">
              <WindArt small />
              <Wind size={44} strokeWidth={1} />
              <svg viewBox="0 0 90 90" className="turbine" aria-hidden="true">
                <path
                  d="M48 75 45 32M45 32 30 8M45 32 76 27M45 32 28 57"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                />
                <circle cx="45" cy="32" r="3" fill="currentColor" />
              </svg>
            </div>
            <p className="eyebrow">THE BIG PICTURE</p>
            <h2>
              Wind forecast
              <br />
              at a glance
            </h2>
            <p>
              {dateLabel(data.query.from)} – {dateLabel(data.query.to, true)}
            </p>
            <small>GB National Wind · Europe/London</small>
            <div className="glance-line" />
            <p className="scope">
              <Info size={17} />
              This shows wind forecast accuracy only. It does not estimate how
              much electricity to buy.
            </p>
          </aside>
        </div>
      </section>
      <Warnings warnings={data.warnings} />
      <DailyPerformance
        data={data}
        metadata={metadata}
        search={search}
        onViewChange={(view) => change({ view })}
      />
      <FeaturedReplays data={data} metadata={metadata} search={search} />
      <ErrorDistribution data={data} />
      <div className="overview-footnote">
        <span>
          Decisions made in January 2026 · Inclusive delivery window shown above
        </span>
        <Link to={replayLink("2026-01-16", data.query.rule, metadata, search)}>
          Open the replay workbench <ArrowRight size={15} />
        </Link>
      </div>
    </>
  );
}
