export function Loading() {
  return (
    <section className="loading panel" role="status" aria-live="polite">
      <span className="loader" />
      <h2>Reading the wind…</h2>
      <p>Loading forecast evidence and matched half-hours.</p>
      <div className="skeleton-grid">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} />
        ))}
      </div>
    </section>
  );
}
