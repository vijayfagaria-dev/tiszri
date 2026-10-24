import type { DayAnalysis } from "../../api/schemas";
import { dayLabel, time } from "../../lib/format";

const at = (instant: string) => `${dayLabel(instant)} at ${time(instant)}`;

// "Used the forecast published Thu 15 Jan at 07:30 GMT, ..." for the replay header.
export function forecastUsed(data: DayAnalysis) {
  const used = [...data.highlights.versionsUsed].sort();
  const latest = used[used.length - 1];
  const newer = data.highlights.newerVersionAfterCutoff;
  return (
    (used.length === 1
      ? `Used the forecast published ${at(latest)}, the latest before the decision time.`
      : `Used ${used.length} forecasts; the latest was published ${at(latest)}.`) +
    (newer ? ` A newer one, published ${at(newer)}, came too late.` : "")
  );
}
