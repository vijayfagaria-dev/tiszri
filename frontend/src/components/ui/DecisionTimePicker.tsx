import type { Metadata } from "../../api/schemas";
import { aliases, customAlias, londonRule, ruleFromAlias } from "../../app/url";
import { dayLabel, shiftDate } from "../../lib/format";
import { InfoTip } from "./InfoTip";

// The usual choices. Anything else, including hindsight, is a custom time.
const choices: [string, string][] = [
  ["MORNING_BEFORE_0900", "Day before, 09:00 (default)"],
  ["NOON_BEFORE_1200", "Day before, 12:00"],
  ["TWO_DAYS_BEFORE_0900", "2 days before, 09:00"],
];
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

export function DecisionTimePicker({
  metadata,
  alias,
  exact,
  date,
  onChange,
}: {
  metadata: Metadata;
  alias: string; // the `rule` URL value, e.g. "d1-0900" or "custom:-3:09:00"
  exact?: string; // an exact UTC decision time from an older link
  date?: string; // the delivery date, to name the days (Day Replay only)
  onChange: (alias: string) => void;
}) {
  const { range, defaultRule } = metadata.cutoff;
  const rule =
    (exact && date
      ? londonRule(exact, date)
      : ruleFromAlias(alias, metadata)) ?? defaultRule;
  const presets = choices.filter(([id]) =>
    metadata.cutoff.presets.some((p) => p.id === id),
  );
  const selected =
    !exact && presets.some(([id]) => aliases[id] === alias) ? alias : "custom";

  const days = Array.from(
    { length: range.maxDayOffset - range.minDayOffset + 1 },
    (_, i) => range.minDayOffset + i,
  );
  if (!days.includes(rule.dayOffset)) days.push(rule.dayOffset);
  const allowed =
    rule.dayOffset === range.maxDayOffset
      ? times.filter((t) => t <= range.maxLocalTimeAtMaxOffset)
      : times;
  const timeOptions = allowed.includes(rule.localTime)
    ? allowed
    : [...allowed, rule.localTime].sort();
  const dayName = (offset: number) =>
    date
      ? `${dayLabel(shiftDate(date, offset))} · ${relative(offset)}`
      : relative(offset).replace(/^./, (c) => c.toUpperCase());

  return (
    <div className="decision-picker">
      <label>
        <span>Decision time</span>
        <select
          value={selected}
          onChange={(e) =>
            onChange(
              e.target.value === "custom" ? customAlias(rule) : e.target.value,
            )
          }
        >
          {presets.map(([id, label]) => (
            <option key={id} value={aliases[id]}>
              {label}
            </option>
          ))}
          <option value="custom">Custom…</option>
        </select>
      </label>
      {selected === "custom" && (
        <>
          <label>
            <span className="sr-only">Decision day</span>
            <select
              value={rule.dayOffset}
              onChange={(e) => {
                const dayOffset = Number(e.target.value);
                const localTime =
                  dayOffset === range.maxDayOffset &&
                  rule.localTime > range.maxLocalTimeAtMaxOffset
                    ? range.maxLocalTimeAtMaxOffset
                    : rule.localTime;
                onChange(customAlias({ dayOffset, localTime }));
              }}
            >
              {days.map((offset) => (
                <option key={offset} value={offset}>
                  {dayName(offset)}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="sr-only">Time (UK)</span>
            <select
              value={rule.localTime}
              onChange={(e) =>
                onChange(
                  customAlias({
                    dayOffset: rule.dayOffset,
                    localTime: e.target.value,
                  }),
                )
              }
            >
              {timeOptions.map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
          </label>
        </>
      )}
      <InfoTip label="About the decision time">
        When you would have placed the order. Only forecasts published by then
        are used.
      </InfoTip>
    </div>
  );
}
