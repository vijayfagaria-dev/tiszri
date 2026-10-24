import { ArrowUp, Check, Info, TriangleAlert, Waves } from "lucide-react";
import type { Metrics } from "../../api/schemas";
import { number, percent } from "../../lib/format";

export function MetricsGrid({
  metrics,
  coverage,
  expected,
  compact = false,
}: {
  metrics: Metrics;
  coverage: number;
  expected: number;
  compact?: boolean;
}) {
  const items = [
    {
      title: "Typical miss",
      subtitle: "Mean absolute error",
      value: number(metrics.mae),
      unit: "MW",
      className: "cyan",
      Icon: Waves,
      help: "MAE: average absolute forecast-minus-actual error over matched half-hours. Direction is ignored.",
    },
    {
      title: "Large-error impact",
      subtitle: "Root mean squared error",
      value: number(metrics.rmse),
      unit: "MW",
      className: "purple",
      Icon: TriangleAlert,
      help: "RMSE: square root of the mean squared error. Large misses have more influence.",
    },
    {
      title: "Signed bias",
      subtitle:
        metrics.bias == null
          ? "No matched intervals"
          : metrics.bias >= 0
            ? "Mostly too high"
            : "Mostly too low",
      value: number(metrics.bias, true),
      unit: "MW",
      className: "amber",
      Icon: ArrowUp,
      help: "Bias = mean(forecast − actual). Positive means too high. Opposite errors can cancel; read alongside MAE.",
    },
    {
      title: "Coverage",
      subtitle: `${number(metrics.n)} / ${number(expected)} matched`,
      value: percent(coverage),
      unit: "",
      className: "teal",
      Icon: Check,
      help: "Matched half-hours divided by expected half-hours. Display percentage is rounded down.",
    },
  ];
  return (
    <div className={`metrics-grid ${compact ? "compact" : ""}`}>
      {items.map(({ Icon, ...item }) => (
        <article className={`metric ${item.className}`} key={item.title}>
          <div className="metric-top">
            <span className="icon-orb">
              <Icon size={21} />
            </span>
            <details className="help">
              <summary aria-label={`About ${item.title}`}>
                <Info size={15} />
              </summary>
              <p>{item.help}</p>
            </details>
          </div>
          <div className="metric-value">
            {item.value}
            <small>{item.value !== "Unavailable" && item.unit}</small>
          </div>
          <h3>{item.title}</h3>
          <p>{item.subtitle}</p>
          <div className="metric-rule" />
        </article>
      ))}
    </div>
  );
}
