import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { RefreshCw } from "lucide-react";
import type { Metadata } from "../api/schemas";
import { useAnalysis } from "../api/queries";
import { apiParams, canonicalParams } from "./url";
import { Loading, ErrorPanel, PresetSelect } from "../components/ui";
import { Overview } from "../features/overview/Overview";
import { Replay } from "../features/replay/Replay";
import { ReplayControls } from "../features/replay/ReplayControls";
import { dateLabel, stamp } from "../lib/format";
export function AnalysisPage({
  metadata,
  replay,
}: {
  metadata: Metadata;
  replay: boolean;
}) {
  const [search, setSearch] = useSearchParams();
  const canonical = canonicalParams(search, replay, metadata);
  let params = new URLSearchParams();
  let inputError: Error | undefined;
  try {
    params = apiParams(canonical, replay, metadata);
  } catch (error) {
    inputError = error as Error;
  }
  const scenarioKey = ["scenario", "mockError", "mockDelay"]
    .map((key) => canonical.get(key))
    .join("|");
  const query = useAnalysis(params, replay, scenarioKey, inputError);
  useEffect(() => {
    if (canonical.toString() !== search.toString())
      setSearch(canonical, { replace: true });
  }, [canonical, search, setSearch]);
  useEffect(() => {
    document.title = `${replay ? "Day Replay" : "Overview"} · Wind Forecast Intelligence`;
  }, [replay]);
  const result = query.data;
  return (
    <>
      {replay && <ReplayControls metadata={metadata} />}
      {!replay && (!result || query.isError) && (
        <div className="recovery-controls">
          <PresetSelect
            metadata={metadata}
            value={canonical.get("rule")!}
            onChange={(value) => {
              const next = new URLSearchParams(search);
              next.set("rule", value);
              setSearch(next);
            }}
          />
        </div>
      )}
      {query.isPending && <Loading />}
      {query.isError && (
        <ErrorPanel
          key={query.error.message}
          error={query.error}
          retry={() => {
            void query.refetch();
          }}
        />
      )}
      {result && (
        <div
          aria-busy={query.isFetching}
          className={query.isFetching ? "updating" : ""}
        >
          {query.isPlaceholderData && (
            <p className="notice" role="status">
              Updating selection. Previous evidence:{" "}
              {"deliveryDate" in result.response.query
                ? `${dateLabel(result.response.query.deliveryDate, true)}; decided ${stamp(result.response.query.decisionCutoff.utc)}.`
                : `${dateLabel(result.response.query.from)}–${dateLabel(result.response.query.to, true)}; decision rule ${result.response.query.rule.dayOffset} calendar days relative to delivery at ${result.response.query.rule.localTime} Europe/London.`}
            </p>
          )}
          <div className="result-tools">
            <span role="status">
              {query.isFetching
                ? "Refreshing the current analysis…"
                : `${result.response.resultState.toLowerCase()} evidence · ${result.response.metadata.counts.matched} matched half-hours`}
            </span>
            <button
              className="ghost"
              onClick={() => {
                void query.refetch();
              }}
              disabled={query.isFetching}
            >
              <RefreshCw size={13} />
              Refresh
            </button>
          </div>
          {"intervals" in result.response ? (
            <Replay result={{ ...result, response: result.response }} />
          ) : (
            <Overview
              result={{ ...result, response: result.response }}
              metadata={metadata}
            />
          )}
        </div>
      )}
    </>
  );
}
