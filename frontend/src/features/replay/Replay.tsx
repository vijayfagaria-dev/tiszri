import { QuickSummary } from "./QuickSummary";
import { IntervalLedger } from "./IntervalLedger";
import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import type { DayAnalysis, Metadata } from "../../api/schemas";
import type { ApiResult } from "../../api/client";
import { Qualification, Warnings } from "../../components/ui";
import { dateLabel, stamp } from "../../lib/format";
import { statusLabels } from "../../lib/status";
import { ForecastChart } from "./ForecastChart";
import { ResponsiveInspector } from "./ResponsiveInspector";
import { Receipts } from "../receipts/Receipts";
export function Replay({
  result,
  metadata,
}: {
  result: ApiResult<DayAnalysis>;
  metadata: Metadata;
}) {
  const data = result.response;
  const [p, setP] = useSearchParams();
  const active = Math.min(
    data.intervals.length,
    Math.max(1, Math.trunc(Number(p.get("interval"))) || 1),
  );
  const interval = data.intervals[active - 1];
  const filter = p.get("filter") ?? "All";
  const sort = p.get("sort") ?? "time";
  const update = (key: string, value: string) => {
    const next = new URLSearchParams(p);
    next.set(key, value);
    setP(next);
  };
  const select = (period: number) => update("interval", String(period));
  useEffect(() => {
    if (p.has("interval") && p.get("interval") !== String(active)) {
      const next = new URLSearchParams(p);
      next.set("interval", String(active));
      setP(next, { replace: true });
    }
  }, [active, p, setP]);
  return (
    <>
      <div className="replay-heading">
        <div>
          <p className="eyebrow">THE DAY, REPLAYED.</p>
          <h1>{dateLabel(data.query.deliveryDate, true)}</h1>
        </div>
        <p>
          Decided: <strong>{stamp(data.query.decisionCutoff.utc)}</strong>
          <span className="block muted">
            {data.query.decisionCutoff.position
              .replaceAll("_", " ")
              .toLowerCase()}{" "}
            · {data.query.decisionCutoff.source.toLowerCase()}
          </span>
        </p>
      </div>
      <Qualification data={data} />
      <Warnings
        warnings={data.warnings}
        select={(instant) => {
          const i = data.intervals.find((i) => i.startTime === instant);
          if (i) select(i.settlementPeriod);
        }}
      />
      {data.query.decisionCutoff.position !== "BEFORE_DELIVERY" && (
        <button
          className="hindsight-reset"
          onClick={() => {
            const next = new URLSearchParams(p);
            next.set("rule", "d1-0900");
            next.delete("cutoff");
            setP(next);
          }}
        >
          Switch to Morning before
        </button>
      )}
      {data.resultState === "EMPTY" && (
        <section className="panel empty-panel">
          <h2>No matched evidence at this decision time</h2>
          <p>
            Missing intervals remain visible below; they are excluded from all
            metrics.
          </p>
          {data.highlights.earliestCoveringPublishTime && (
            <button
              onClick={() => {
                const next = new URLSearchParams(p);
                next.set(
                  "cutoff",
                  data.highlights.earliestCoveringPublishTime!,
                );
                next.delete("rule");
                setP(next);
              }}
            >
              Use earliest covering forecast
            </button>
          )}
        </section>
      )}
      <div className="replay-layout">
        <QuickSummary data={data} />
        <div className="replay-center">
          <ForecastChart data={data} active={active} select={select} />
          <IntervalLedger
            data={data}
            active={active}
            filter={filter}
            sort={sort}
            select={select}
            onSort={(value) => update("sort", value)}
            onFilter={(value) => update("filter", value)}
          />
        </div>
        {interval && <ResponsiveInspector interval={interval} data={data} />}
      </div>
      <p role="status" className="sr-only">
        Selected interval {active},{" "}
        {interval ? statusLabels[interval.status] : ""}. Filter: {filter}.
      </p>
      <Receipts result={result} metadata={metadata} />
    </>
  );
}
