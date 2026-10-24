import type { Metadata } from "../../api/schemas";

// The delivery days the overview covers, within the supported window.
export function DateRange({
  metadata,
  from,
  to,
  onChange,
}: {
  metadata: Metadata;
  from: string;
  to: string;
  onChange: (from: string, to: string) => void;
}) {
  const { from: first, to: last } = metadata.supportedDeliveryWindow;
  return (
    <div className="date-range" role="group" aria-label="Delivery days">
      <span>Delivery days</span>
      <label>
        <span className="sr-only">From</span>
        <input
          type="date"
          aria-label="From"
          min={first}
          max={to}
          value={from}
          onChange={(e) => e.target.value && onChange(e.target.value, to)}
        />
      </label>
      <span aria-hidden="true">–</span>
      <label>
        <span className="sr-only">To</span>
        <input
          type="date"
          aria-label="To"
          min={from}
          max={last}
          value={to}
          onChange={(e) => e.target.value && onChange(from, e.target.value)}
        />
      </label>
    </div>
  );
}
