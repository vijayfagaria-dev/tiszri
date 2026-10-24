import type { Metadata, Rule } from "../api/schemas";
import { dateLabel } from "../lib/format";
export const aliases: Record<string, string> = {
  TWO_DAYS_BEFORE_0900: "d2-0900",
  MORNING_BEFORE_0900: "d1-0900",
  NOON_BEFORE_1200: "d1-1200",
  DELIVERY_START_0000: "d0-0000",
  AFTER_DELIVERY_0000: "after-0000",
};
export const ruleAlias = (rule: Rule, metadata: Metadata) =>
  aliases[
    metadata.cutoff.presets.find(
      (p) =>
        p.rule.dayOffset === rule.dayOffset &&
        p.rule.localTime === rule.localTime,
    )?.id ?? ""
  ] ?? `custom:${rule.dayOffset}:${rule.localTime}`;
// "d1-0900" or "custom:-3:09:00" back to a rule; null if it is neither.
export function ruleFromAlias(alias: string, metadata: Metadata): Rule | null {
  const preset = metadata.cutoff.presets.find(
    (item) => aliases[item.id] === alias,
  );
  const custom = /^custom:(-?\d):([0-2]\d:[0-5]\d)$/.exec(alias);
  return (
    preset?.rule ??
    (custom ? { dayOffset: Number(custom[1]), localTime: custom[2] } : null)
  );
}
export const customAlias = (rule: Rule) =>
  `custom:${rule.dayOffset}:${rule.localTime}`;
// The London day and time of an instant, as a rule relative to the delivery date.
export function londonRule(utc: string, date: string): Rule {
  const part = Object.fromEntries(
    new Intl.DateTimeFormat("en-GB", {
      timeZone: "Europe/London",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    })
      .formatToParts(new Date(utc))
      .map((p) => [p.type, p.value]),
  );
  const day = `${part.year}-${part.month}-${part.day}`;
  return {
    dayOffset: Math.round((Date.parse(day) - Date.parse(date)) / 86400000),
    localTime: `${part.hour}:${part.minute}`,
  };
}
export function canonicalParams(
  search: URLSearchParams,
  replay: boolean,
  metadata: Metadata,
) {
  const p = new URLSearchParams(search);
  const allowed = [
    "rule",
    ...(replay
      ? ["date", "cutoff", "interval", "filter", "sort"]
      : ["from", "to", "view"]),
    ...(import.meta.env.VITE_API_MODE === "mock"
      ? ["scenario", "mockError", "mockDelay", "mockHealth"]
      : []),
  ];
  for (const key of [...p.keys()]) if (!allowed.includes(key)) p.delete(key);
  if (replay) {
    if (!p.has("date")) p.set("date", "2026-01-16");
    if (p.has("cutoff")) p.delete("rule");
  } else {
    p.set("from", p.get("from") ?? metadata.summaryDefaults.from);
    p.set("to", p.get("to") ?? metadata.summaryDefaults.to);
  }
  if (!p.has("cutoff") && !p.has("rule"))
    p.set("rule", ruleAlias(metadata.cutoff.defaultRule, metadata));
  return p;
}
// Checked here so a bad link shows a clear message and keeps the last valid result.
const isDate = (value: string | null): value is string =>
  !!value &&
  /^\d{4}-\d{2}-\d{2}$/.test(value) &&
  Number.isFinite(Date.parse(value));
function checkRule(rule: Rule, metadata: Metadata) {
  const { range } = metadata.cutoff;
  const [hours, minutes] = rule.localTime.split(":").map(Number);
  if (
    hours > 23 ||
    minutes > 59 ||
    rule.dayOffset < range.minDayOffset ||
    rule.dayOffset > range.maxDayOffset ||
    (rule.dayOffset === range.maxDayOffset &&
      rule.localTime > range.maxLocalTimeAtMaxOffset)
  )
    throw new Error(
      `The decision time must be between ${-range.minDayOffset} days before and ${range.maxDayOffset} days after the delivery day.`,
    );
}
export function apiParams(
  p: URLSearchParams,
  replay: boolean,
  metadata: Metadata,
) {
  const supported = metadata.supportedDeliveryWindow;
  const inWindow = (value: string) =>
    value >= supported.from && value <= supported.to;
  const span = `${dateLabel(supported.from, true)} and ${dateLabel(supported.to, true)}`;
  const result = new URLSearchParams();
  const date = p.get("date") ?? "2026-01-16";
  if (replay) {
    if (!isDate(date) || !inWindow(date))
      throw new Error(`Choose a delivery date between ${span}.`);
    result.set("deliveryDate", date);
  } else {
    const from = p.get("from") ?? metadata.summaryDefaults.from;
    const to = p.get("to") ?? metadata.summaryDefaults.to;
    if (!isDate(from) || !isDate(to) || !inWindow(from) || !inWindow(to))
      throw new Error(`Choose dates between ${span}.`);
    if (from > to)
      throw new Error("The start date must be before the end date.");
    result.set("from", from);
    result.set("to", to);
  }
  if (replay && p.has("cutoff")) {
    const value = p.get("cutoff")!;
    if (
      !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(value) ||
      !Number.isFinite(Date.parse(value))
    )
      throw new Error(
        "The cutoff must be a valid UTC instant with seconds and Z.",
      );
    checkRule(londonRule(value, date), metadata);
    result.set("decisionCutoff", value);
  } else {
    const rule = ruleFromAlias(
      p.get("rule") ?? ruleAlias(metadata.cutoff.defaultRule, metadata),
      metadata,
    );
    if (!rule)
      throw new Error(
        "Unknown decision-time rule. Select a preset to continue.",
      );
    checkRule(rule, metadata);
    result.set("cutoffDayOffset", String(rule.dayOffset));
    result.set("cutoffLocalTime", rule.localTime);
  }
  return result;
}

export function replayLink(
  date: string,
  rule: Rule,
  metadata: Metadata,
  current?: URLSearchParams,
) {
  const p = new URLSearchParams({ date, rule: ruleAlias(rule, metadata) });
  if (current?.has("scenario")) p.set("scenario", current.get("scenario")!);
  return `/replay?${p}`;
}
