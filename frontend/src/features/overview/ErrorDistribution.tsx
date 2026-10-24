import { ChartNoAxesCombined } from "lucide-react";
import type { Summary } from "../../api/schemas";
import { number } from "../../lib/format";
export function ErrorDistribution({ data }: { data: Summary }) {
  return (
    <section className="distribution panel">
      <div className="distribution-heading">
        <div>
          <p className="eyebrow">BEYOND THE AVERAGE</p>
          <h2>Every miss has a direction.</h2>
          <p>
            Signed error across {number(data.metrics.n)} matched half-hours.
          </p>
        </div>
        <div className="percentiles">
          {Object.entries(data.distribution.absError).map(([key, value]) => (
            <div key={key}>
              <span>{key.toUpperCase()} absolute error</span>
              <strong>
                {number(value)} <small>MW</small>
              </strong>
            </div>
          ))}
        </div>
      </div>
      <figure aria-label="Signed forecast error distribution">
        <div className="histogram">
          {data.distribution.histogram.bins.map((bin) => (
            <div
              key={bin.lowerEdge}
              className={`histogram-bin ${bin.lowerEdge < 0 ? "negative" : ""}`}
              style={{
                height: `${Math.max(2, (bin.count / Math.max(1, ...data.distribution.histogram.bins.map((b) => b.count))) * 100)}%`,
              }}
              tabIndex={0}
              role="img"
              aria-label={`${bin.lowerEdge} to less than ${bin.upperEdge} MW: ${bin.count} intervals`}
            >
              <span className="bin-tip">
                {number(bin.lowerEdge)} to &lt; {number(bin.upperEdge)} MW
                <br />
                {bin.count} intervals
              </span>
            </div>
          ))}
        </div>
        <figcaption>
          <span>← Forecast too low</span>
          <span>Forecast − actual (MW)</span>
          <span>Forecast too high →</span>
        </figcaption>
      </figure>
      <details>
        <summary>
          <ChartNoAxesCombined size={15} />
          View distribution table
        </summary>
        <div className="table-scroll">
          <table>
            <caption>
              Signed error bins, lower inclusive / upper exclusive
            </caption>
            <thead>
              <tr>
                <th>From (MW)</th>
                <th>To (MW)</th>
                <th>Half-hours</th>
              </tr>
            </thead>
            <tbody>
              {data.distribution.histogram.bins.map((b) => (
                <tr key={b.lowerEdge}>
                  <td>{number(b.lowerEdge)}</td>
                  <td>{number(b.upperEdge)}</td>
                  <td>{b.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}
