import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  // `yarn dev:api` talks to the backend from `make dev`; mock mode never reaches it.
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
});
