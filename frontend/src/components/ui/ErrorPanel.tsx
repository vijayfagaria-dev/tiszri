import { useState, useEffect } from "react";
import { TriangleAlert } from "lucide-react";
import { ApiError } from "../../api/client";

export function ErrorPanel({
  error,
  retry,
  retryLabel = "Try again",
}: {
  error: Error;
  retry: () => void;
  retryLabel?: string;
}) {
  const [now, setNow] = useState(Date.now);
  const [started] = useState(Date.now);
  const wait =
    error instanceof ApiError
      ? Math.max(0, Math.ceil((started + error.retryAfter - now) / 1000))
      : 0;
  useEffect(() => {
    if (!wait) return;
    const timer = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(timer);
  }, [wait]);
  return (
    <section className="panel error-panel" role="alert">
      <TriangleAlert size={30} />
      <h2>We couldn’t load this analysis</h2>
      <p>{error.message}</p>
      {error instanceof ApiError && (
        <>
          <p className="muted">
            {error.code} · Request {error.requestId}
          </p>
          {error.details.map((d) => (
            <p key={d.field}>
              {d.field}: {d.message}
            </p>
          ))}
        </>
      )}
      <button disabled={wait > 0} onClick={retry}>
        {wait ? `Retry in ${wait}s` : retryLabel}
      </button>
    </section>
  );
}
