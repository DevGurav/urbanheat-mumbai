import { CssBaseline, ThemeProvider, createTheme } from "@mui/material";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App.tsx";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // The Gemini free tier's real quota is 20 req/day (BLUEPRINT.md, measured live) —
      // aggressive refetch-on-focus defaults would burn it on nothing. Individual queries
      // that genuinely need fresher data (e.g. /alerts) override this per-hook.
      refetchOnWindowFocus: false,
      staleTime: 60_000,
    },
  },
});

const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#c0392b" }, // heat, not the default MUI blue
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <App />
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
);
