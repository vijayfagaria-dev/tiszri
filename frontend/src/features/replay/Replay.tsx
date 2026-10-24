import { QuickSummary } from "./QuickSummary";
import { IntervalLedger } from "./IntervalLedger";
import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { RefreshCw } from "lucide-react";
import type { DayAnalysis } from "../../api/schemas";
import type { ApiResult } from "../../api/client";
import { Warnings } from "../../components/ui";
import { dayLabel, time } from "../../lib/format";
import { statusLabels } from "../../lib/status";
import { ForecastChart } from "./ForecastChart";
import { ResponsiveInspector } from "./ResponsiveInspector";
import { EmptyDay } from "./EmptyDay";
export function Replay({
  result,
  refreshing,
  onRefresh,
}: {
  result: ApiResult<DayAnalysis>;
  refreshing: boolean;
  onRefresh: () => void;
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
  const backToDefault = {
    label: "Switch to Morning before · 09:00",
    run: () => {
      const next = new URLSearchParams(p);
      next.set("rule", "d1-0900");
      next.delete("cutoff");
      setP(next);
    },
  };
  useEffect(() => {
    if (p.has("interval") && p.get("interval") !== String(active)) {
      const next = new URLSearchParams(p);
      next.set("interval", String(active));
      setP(next, { replace: true });
    }
  }, [active, p, setP]);
  return (
    <>
      <section className="replay-heading panel">
        <div>
          <span>Delivery day</span>
          <h1>{dayLabel(data.query.deliveryDate, true)}</h1>
        </div>
        <div>
          <span>Decision made</span>
          <strong>
            {dayLabel(data.query.decisionCutoff.utc)} at{" "}
            {time(data.query.decisionCutoff.utc)}
            {data.query.decisionCutoff.source === "EXPLICIT" && " (exact time)"}
          </strong>
        </div>
        <span role="status" className="sr-only">
          {refreshing ? "Refreshing…" : ""}
        </span>
        <button
          className="ghost"
          onClick={onRefresh}
          disabled={refreshing}
          aria-label="Refresh"
          title="Refresh"
        >
          <RefreshCw size={14} />
        </button>
      </section>
      <Warnings
        warnings={visibleWarnings(data)}
        select={(instant) => {
          const i = data.intervals.find((i) => i.startTime === instant);
          if (i) select(i.settlementPeriod);
        }}
        actions={{
          HINDSIGHT_CUTOFF: backToDefault,
          CUTOFF_INSIDE_DELIVERY_DAY: backToDefault,
        }}
      />
      {data.resultState === "EMPTY" ? (
        <EmptyDay data={data} />
      ) : (
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
      )}
      <p role="status" className="sr-only">
        Selected interval {active},{" "}
        {interval ? statusLabels[interval.status] : ""}. Filter: {filter}.
      </p>
    </>
  );
}

// Leave out warnings that something else on the page already says.
function visibleWarnings(data: DayAnalysis) {
  const codes = data.warnings.map((w) => w.code);
  const hidden = [
    // the empty-day panel explains these
    ...(data.resultState === "EMPTY"
      ? ["NO_MATCHED_INTERVALS", "NEWER_VERSION_AFTER_CUTOFF"]
      : []),
    // implied by a decision made during or after delivery
    ...(codes.includes("HINDSIGHT_CUTOFF") ||
    codes.includes("CUTOFF_INSIDE_DELIVERY_DAY")
      ? ["ISSUED_AFTER_DELIVERY_START"]
      : []),
  ];
  return data.warnings.filter((w) => !hidden.includes(w.code));
}
