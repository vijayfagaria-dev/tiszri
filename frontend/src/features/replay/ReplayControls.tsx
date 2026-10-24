import { useSearchParams } from "react-router-dom";
import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react";
import type { Metadata } from "../../api/schemas";
import { CopyButton, PresetSelect } from "../../components/ui";
import { shiftDate } from "../../lib/format";
import { CustomTime } from "./CustomTime";

export function ReplayControls({ metadata }: { metadata: Metadata }) {
  const [p, setP] = useSearchParams();
  const date = p.get("date") ?? "2026-01-16";
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
      <CustomTime metadata={metadata} date={date} />
      <CopyButton value={location.href} />
    </section>
  );
}
