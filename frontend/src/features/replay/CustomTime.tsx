import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import type { Metadata } from "../../api/schemas";
import { ruleAlias, ruleFromAlias } from "../../app/url";
import { dayLabel, shiftDate } from "../../lib/format";

const times = Array.from(
  { length: 48 },
  (_, i) =>
    `${String(Math.floor(i / 2)).padStart(2, "0")}:${i % 2 ? "30" : "00"}`,
);
const relative = (offset: number) =>
  offset === 0
    ? "delivery day"
    : Math.abs(offset) === 1
      ? `day ${offset < 0 ? "before" : "after"}`
      : `${Math.abs(offset)} days ${offset < 0 ? "before" : "after"}`;

export function CustomTime({
  metadata,
  date,
}: {
  metadata: Metadata;
  date: string;
}) {
  const [p, setP] = useSearchParams();
  const { range, defaultRule } = metadata.cutoff;
  const current = ruleFromAlias(p.get("rule") ?? "", metadata) ?? defaultRule;
  const [dayOffset, setDayOffset] = useState(current.dayOffset);
  const [localTime, setLocalTime] = useState(current.localTime);
  const details = useRef<HTMLDetailsElement>(null);

  // Close like a menu: on a click anywhere else, or on Escape.
  useEffect(() => {
    const onPointerDown = (event: PointerEvent) => {
      const panel = details.current;
      if (panel?.open && !panel.contains(event.target as Node))
        panel.open = false;
    };
    const onKeyDown = (event: KeyboardEvent) => {
      const panel = details.current;
      if (event.key !== "Escape" || !panel?.open) return;
      panel.open = false;
      panel.querySelector("summary")?.focus();
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, []);

  const offsets = Array.from(
    { length: range.maxDayOffset - range.minDayOffset + 1 },
    (_, i) => range.minDayOffset + i,
  );
  const allowed =
    dayOffset === range.maxDayOffset
      ? times.filter((t) => t <= range.maxLocalTimeAtMaxOffset)
      : times;
  const timeOptions = allowed.includes(localTime)
    ? allowed
    : [...allowed, localTime].sort();

  return (
    <details
      className="custom-cutoff"
      ref={details}
      onToggle={(e) => {
        if (!e.currentTarget.open) return;
        setDayOffset(current.dayOffset);
        setLocalTime(current.localTime);
      }}
    >
      <summary>Custom time</summary>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const next = new URLSearchParams(p);
          next.set("rule", ruleAlias({ dayOffset, localTime }, metadata));
          next.delete("cutoff");
          setP(next);
          details.current!.open = false;
        }}
      >
        <label>
          Decision day
          <select
            value={dayOffset}
            onChange={(e) => {
              const offset = Number(e.target.value);
              setDayOffset(offset);
              if (
                offset === range.maxDayOffset &&
                localTime > range.maxLocalTimeAtMaxOffset
              )
                setLocalTime(range.maxLocalTimeAtMaxOffset);
            }}
          >
            {offsets.map((offset) => (
              <option key={offset} value={offset}>
                {dayLabel(shiftDate(date, offset))} · {relative(offset)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Time (UK)
          <select
            value={localTime}
            onChange={(e) => setLocalTime(e.target.value)}
          >
            {timeOptions.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </label>
        <p>Only forecasts published by this time are used.</p>
        <button type="submit">Apply</button>
      </form>
    </details>
  );
}
