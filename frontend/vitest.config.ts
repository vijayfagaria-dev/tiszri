import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  test: {
    include: ["src/test/**/*.test.{ts,tsx}"],
    environment: "node",
    env: { VITE_API_MODE: "mock" },
  },
});
