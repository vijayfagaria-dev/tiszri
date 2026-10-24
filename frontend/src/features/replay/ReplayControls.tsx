import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react";
import type { Metadata } from "../../api/schemas";
import { CopyButton, PresetSelect } from "../../components/ui";
import { shiftDate } from "../../lib/format";

export function ReplayControls({ metadata }: { metadata: Metadata }) {
  const [p, setP] = useSearchParams();
  const date = p.get("date") ?? "2026-01-16";
  const [custom, setCustom] = useState("");
  const [error, setError] = useState("");
  const changeDate = (nextDate: string) => {
    const next = new URLSearchParams(p);
    next.set("date", nextDate);
    next.delete("interval");
    if (next.has("cutoff")) {
      const cutoff = new Date(next.get("cutoff")!);
      if (
        Number.isFinite(cutoff.getTime()) &&
        Number.isFinite(Date.parse(date)) &&
        Number.isFinite(Date.parse(nextDate))
      )
        next.set(
          "cutoff",
          new Date(cutoff.getTime() + Date.parse(nextDate) - Date.parse(date))
            .toISOString()
            .replace(".000Z", "Z"),
        );
    }
    setP(next);
  };
  return (
    <section className="replay-controls panel">
      <div className="date-control">
        <button
          aria-label="Previous day"
          disabled={date <= metadata.supportedDeliveryWindow.from}
          onClick={() => changeDate(shiftDate(date, -1))}
        >
          <ChevronLeft size={18} />
        </button>
        <label>
          <CalendarDays size={20} />
          <span className="sr-only">Delivery date</span>
          <input
            aria-label="Delivery date"
            type="date"
            min={metadata.supportedDeliveryWindow.from}
            max={metadata.supportedDeliveryWindow.to}
            value={date}
            onChange={(e) => changeDate(e.target.value)}
          />
        </label>
        <button
          aria-label="Next day"
          disabled={date >= metadata.supportedDeliveryWindow.to}
          onClick={() => changeDate(shiftDate(date, 1))}
        >
          <ChevronRight size={18} />
        </button>
      </div>
      <PresetSelect
        metadata={metadata}
        value={p.has("cutoff") ? "exact" : (p.get("rule") ?? "d1-0900")}
        onChange={(value) => {
          const next = new URLSearchParams(p);
          next.set("rule", value);
          next.delete("cutoff");
          setP(next);
        }}
      />
      <details className="custom-cutoff">
        <summary>Custom cutoff</summary>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (
              !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(custom) ||
              !Number.isFinite(Date.parse(custom))
            ) {
              setError(
                "Enter a valid UTC instant with seconds, for example 2026-01-15T09:00:00Z.",
              );
              return;
            }
            const min = Date.parse(`${shiftDate(date, -7)}T00:00:00Z`);
            const max = Date.parse(`${shiftDate(date, 2)}T00:00:00Z`);
            if (Date.parse(custom) < min || Date.parse(custom) > max) {
              setError(
                "Cutoff must lie between 7 days before and 2 days after delivery at 00:00 London.",
              );
              return;
            }
            const next = new URLSearchParams(p);
            next.set("cutoff", custom);
            next.delete("rule");
            setError("");
            setP(next);
          }}
        >
          <label>
            Exact decision time (UTC)
            <input
              placeholder="2026-01-15T09:00:00Z"
              value={custom}
              onChange={(e) => setCustom(e.target.value)}
              aria-invalid={!!error}
            />
          </label>
          <p>
            UTC input is unambiguous. Applied London time appears with the
            result. Day navigation shifts this instant by the same number of
            days within the January window.
          </p>
          {error && <p role="alert">{error}</p>}
          <button type="submit">Apply cutoff</button>
        </form>
      </details>
      <CopyButton value={location.href} />
    </section>
  );
}
