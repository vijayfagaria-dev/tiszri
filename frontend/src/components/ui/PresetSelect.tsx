import type { Metadata } from "../../api/schemas";
import { aliases, presetLabels } from "../../app/url";

export function PresetSelect({
  metadata,
  value,
  onChange,
}: {
  metadata: Metadata;
  value: string;
  onChange: (alias: string) => void;
}) {
  return (
    <label className="preset-label">
      <span>Forecast viewed</span>
      <select
        aria-label="Forecast decision time"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {!metadata.cutoff.presets.some((p) => aliases[p.id] === value) && (
          <option value={value}>Custom decision time</option>
        )}
        {metadata.cutoff.presets.map((p) => (
          <option key={p.id} value={aliases[p.id]}>
            {presetLabels[p.id]}
          </option>
        ))}
      </select>
    </label>
  );
}
