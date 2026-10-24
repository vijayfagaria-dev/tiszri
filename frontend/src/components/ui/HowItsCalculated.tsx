import type { Metadata } from "../../api/schemas";

// The method in brief, from the definitions the API publishes in /metadata.
export function HowItsCalculated({ metadata }: { metadata: Metadata }) {
  const { policies } = metadata;
  return (
    <details className="methodology panel">
      <summary>How it’s calculated</summary>
      <div className="methodology-body">
        <section>
          <h3>Data</h3>
          <ul>
            {metadata.datasets.map((d) => (
              <li key={d.id}>
                <strong>Elexon {d.id}</strong>:{" "}
                {d.role === "ACTUAL"
                  ? "actual wind generation"
                  : "wind generation forecast"}
                , in {d.unit.unit}. {d.unit.meaning}.
              </li>
            ))}
          </ul>
        </section>
        <section>
          <h3>Which forecast is used</h3>
          <ul>
            <li>{policies.selection.text}</li>
            <li>{policies.mapping.text}</li>
            <li>{policies.duplicates.text}</li>
          </ul>
        </section>
        <section>
          <h3>Metrics</h3>
          <ul>
            <li>
              Error = forecast − actual, so a positive error means the forecast
              was too high.
            </li>
            {metadata.metricDefinitions.map((m) => (
              <li key={m.id}>
                <strong>{m.id}</strong> = <code>{m.formula}</code>.{" "}
                {m.description}
              </li>
            ))}
            <li>
              <strong>Coverage</strong> = matched half-hours ÷ expected
              half-hours.
            </li>
            <li>
              Only half-hours with both a forecast and an actual value count;
              missing values are excluded, never treated as zero. Figures over
              several days pool every matched half-hour.
            </li>
            <li>Times are UK time (GMT or BST).</li>
          </ul>
        </section>
      </div>
    </details>
  );
}
