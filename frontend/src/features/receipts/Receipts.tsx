import type { ApiResult } from "../../api/client";
import type { DayAnalysis, Metadata, Summary } from "../../api/schemas";
import { stamp, mw } from "../../lib/format";
import { CopyButton } from "../../components/ui";
import { FileText, Settings2 } from "lucide-react";
export function Receipts({
  result,
  metadata,
}: {
  result: ApiResult<DayAnalysis | Summary>;
  metadata: Metadata;
}) {
  const d = result.response;
  return (
    <section className="receipts">
      <details className="panel">
        <summary>
          <Settings2 size={17} />
          Methodology & definitions
        </summary>
        <div className="disclosure-body">
          <p>
            Forecast minus actual: positive errors mean too high; negative
            errors mean too low.
          </p>
          {metadata.metricDefinitions.map((m) => (
            <p key={m.id}>
              <strong>
                {m.id} · {m.formula}
              </strong>
              <br />
              {m.description}
            </p>
          ))}
          <p>
            <strong>Coverage</strong> = matched / expected half-hours. Metrics
            use matched evidence only.
          </p>
          {Object.values(metadata.policies).map((p) => (
            <p key={p.id}>
              {p.text}
              <small className="block mono muted">{p.id}</small>
            </p>
          ))}
          <p>
            09:00 the day before is an editable default, not a market rule.
            Relative rules use London calendar days. Spring gaps move forward an
            hour; autumn folds use the earlier instant.
          </p>
          {metadata.datasets.map((ds) => (
            <p key={ds.id}>
              <strong>
                {ds.id} · {ds.role} · {ds.unit.unit}
              </strong>
              <br />
              {ds.unit.meaning}
              <br />
              {ds.unit.status}: {ds.unit.evidence}
            </p>
          ))}
          {"sensitivity" in d && (
            <p>
              On-the-hour sensitivity: {d.sensitivity.onTheHourOnly.n} matched;
              MAE {mw(d.sensitivity.onTheHourOnly.mae)}, RMSE{" "}
              {mw(d.sensitivity.onTheHourOnly.rmse)}, bias{" "}
              {mw(d.sensitivity.onTheHourOnly.bias, true)}.
            </p>
          )}
        </div>
      </details>
      <details className="panel">
        <summary>
          <FileText size={17} />
          Result receipt & provenance
        </summary>
        <div className="disclosure-body">
          <p>
            Contract {d.metadata.contractVersion} · Algorithm{" "}
            {d.metadata.algorithmVersion}
          </p>
          <p>Computed at {stamp(d.metadata.generatedAt)}</p>
          <p className="mono">Request {d.metadata.requestId}</p>
          {d.metadata.sources.map((s) => (
            <div key={s.dataset} className="source-receipt">
              <h3>
                {s.dataset} · {s.role}
              </h3>
              <p>
                {s.requestedRange.from} → {s.requestedRange.to} (
                {s.requestedRange.basis})
              </p>
              <p>
                {s.rowsReceived} received · {s.rowsRejected} rejected ·{" "}
                {s.rowsFiltered} filtered · Cache {s.cache}
              </p>
              <p>Fetched {stamp(s.fetchedAt)}</p>
              {s.versions && (
                <p>
                  {s.versions.coveringDay} covering vintages ·{" "}
                  {s.versions.eligible} eligible · {s.versions.afterCutoff}{" "}
                  after cutoff
                </p>
              )}
            </div>
          ))}
          <CopyButton
            label="Copy diagnostic receipt"
            value={JSON.stringify(
              { response: d, httpHeaders: result.httpHeaders },
              null,
              2,
            )}
          />
          <details>
            <summary>Raw query, metadata & HTTP headers</summary>
            <pre>
              {JSON.stringify(
                {
                  query: d.query,
                  metadata: d.metadata,
                  httpHeaders: result.httpHeaders,
                },
                null,
                2,
              )}
            </pre>
          </details>
        </div>
      </details>
    </section>
  );
}
