import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import { Providers } from "./app/Providers";

async function bootstrap() {
  if (import.meta.env.VITE_API_MODE === "mock") {
    const { worker } = await import("./mocks/browser");
    await worker.start({ onUnhandledRequest: "bypass" });
  }
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <Providers>
        <App />
      </Providers>
    </StrictMode>,
  );
}
void bootstrap().catch(() => {
  document.getElementById("root")!.textContent =
    "The application could not start. Reload the page or check the mock worker setup.";
});
