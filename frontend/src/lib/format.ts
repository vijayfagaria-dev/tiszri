export const number = (value: number | null | undefined, signed = false) =>
  value == null
    ? "Unavailable"
    : new Intl.NumberFormat("en-GB", {
        maximumFractionDigits: 0,
        signDisplay: signed ? "exceptZero" : "auto",
      }).format(value);
export const mw = (value: number | null | undefined, signed = false) =>
  value == null ? "Unavailable" : `${number(value, signed)} MW`;
export const percent = (value: number) => `${Math.floor(value * 1000) / 10}%`;
const londonTime = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Europe/London",
  hour: "2-digit",
  minute: "2-digit",
  timeZoneName: "short",
});
// Browsers name the London zone "GMT+0" / "GMT+1" rather than GMT / BST.
export const time = (value: string) =>
  londonTime
    .formatToParts(new Date(value))
    .map((part) =>
      part.type !== "timeZoneName"
        ? part.value
        : ["BST", "GMT+1"].includes(part.value)
          ? "BST"
          : "GMT",
    )
    .join("");
export const dateLabel = (value: string, year = false) =>
  new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/London",
    day: "numeric",
    month: "short",
    ...(year ? { year: "numeric" } : {}),
  }).format(new Date(value));
export const stamp = (value: string) =>
  `${dateLabel(value, true)}, ${time(value)}`;
export const minutes = (value: number) =>
  `${value < 0 ? "−" : ""}${Math.floor(Math.abs(value) / 60)}h ${Math.abs(value) % 60}m`;
export const shiftDate = (date: string, by: number) =>
  new Date(Date.parse(`${date}T12:00:00Z`) + by * 86400000)
    .toISOString()
    .slice(0, 10);
