import { NavLink, useSearchParams } from "react-router-dom";
import { Wind } from "lucide-react";
import { useHealth } from "../api/queries";
export function Header() {
  const health = useHealth();
  const [params] = useSearchParams();
  const search = new URLSearchParams();
  if (params.has("rule")) search.set("rule", params.get("rule")!);
  if (params.has("scenario")) search.set("scenario", params.get("scenario")!);
  const state = health.isError
    ? "Unreachable"
    : health.isPending
      ? "Checking"
      : health.data?.response.status === "NOT_READY"
        ? "Not ready"
        : health.data?.response.checks.upstream === "OK"
          ? "Healthy"
          : health.data?.response.checks.upstream === "DEGRADED"
            ? "Degraded"
            : "Unknown";
  return (
    <header className="app-header">
      <a className="brand" href="/">
        <Wind size={35} strokeWidth={1.6} />
        <span>Wind Forecast Intelligence</span>
      </a>
      <span className="dataset-badge">GB National Wind</span>
      <nav aria-label="Main navigation">
        <NavLink to={`/?${search}`} end>
          Overview
        </NavLink>
        <NavLink to={`/replay?${search}`}>Day Replay</NavLink>
      </nav>
      <div className={`health ${state === "Healthy" ? "healthy" : ""}`}>
        <i />
        <div>
          <small>
            {import.meta.env.VITE_API_MODE === "mock"
              ? "Demo source"
              : "Elexon source"}
          </small>
          <strong>{state}</strong>
        </div>
      </div>
    </header>
  );
}
