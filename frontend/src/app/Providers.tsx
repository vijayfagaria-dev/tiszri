import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import type { ReactNode } from "react";
import { retry, retryDelay } from "../api/client";
import { ErrorBoundary } from "./ErrorBoundary";
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry, retryDelay, refetchOnWindowFocus: false },
  },
});
export function Providers({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>{children}</BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
