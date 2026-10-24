import { Routes, Route, Link, useSearchParams } from "react-router-dom";
import { Wind } from "lucide-react";
import { useMetadata } from "./api/queries";
import { Header } from "./app/Header";
import { AnalysisPage } from "./app/AnalysisPage";
import { ErrorPanel, Loading } from "./components/ui";
import { useOnline } from "./hooks/useOnline";
function DemoBanner() {
  const [p, setP] = useSearchParams();
  return (
    <div className="demo-banner">
      <span>
        <i />
        Demo data{" "}
        <span className="demo-note">
          · Recorded API responses for 5, 15, 16, 19 and 28 January
        </span>
      </span>
      <label>
        Scenario
        <select
          aria-label="Demo scenario"
          value={
            p.get("mockError")
              ? `error:${p.get("mockError")}`
              : (p.get("scenario") ?? "complete")
          }
          onChange={(e) => {
            const next = new URLSearchParams(p);
            next.delete("mockError");
            next.delete("scenario");
            if (e.target.value.startsWith("error:"))
              next.set("mockError", e.target.value.slice(6));
            else next.set("scenario", e.target.value);
            setP(next);
          }}
        >
          <option value="complete">Recorded data</option>
          <option value="edge">All statuses (synthetic, 16 Jan)</option>
          <option value="error:502">Source unavailable</option>
          <option value="error:503">Rate limited</option>
          <option value="error:504">Source timeout</option>
          <option value="error:malformed">Invalid response</option>
        </select>
      </label>
    </div>
  );
}
export default function App() {
  const metadata = useMetadata();
  const online = useOnline();
  return (
    <>
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <div className="app-shell">
        <Header />
        {import.meta.env.VITE_API_MODE === "mock" && <DemoBanner />}
        {!online && (
          <div role="alert" className="notice offline">
            You’re offline. Any displayed result is previously loaded evidence.
            New requests resume when connected.
          </div>
        )}
        <main id="main-content" tabIndex={-1}>
          {metadata.isPending ? (
            <Loading />
          ) : metadata.isError ? (
            <ErrorPanel
              error={metadata.error}
              retry={() => {
                void metadata.refetch();
              }}
            />
          ) : (
            <Routes>
              <Route
                path="/"
                element={
                  <AnalysisPage
                    key="overview"
                    metadata={metadata.data.response}
                    replay={false}
                  />
                }
              />
              <Route
                path="/replay"
                element={
                  <AnalysisPage
                    key="replay"
                    metadata={metadata.data.response}
                    replay
                  />
                }
              />
              <Route
                path="*"
                element={
                  <section className="panel error-panel">
                    <h1>Page not found</h1>
                    <Link to="/">Return to Overview</Link>
                  </section>
                }
              />
            </Routes>
          )}
        </main>
        <footer className="app-footer">
          <span>
            <Wind size={17} />
            Wind Forecast Intelligence
          </span>
          <span>Historical evidence. Clearer perspective.</span>
          <span>
            Europe/London
            {metadata.data &&
              ` · Contract ${metadata.data.response.contractVersion}`}
          </span>
        </footer>
      </div>
    </>
  );
}
