/**
 * One TanStack Query hook per endpoint the UI actually calls. `POST /monitoring/check` has no
 * hook here — it's cron-only (agents.md §7), never called from the client.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./client";
import type { HotspotsBy, HotspotsUnit, SavedScenarioRequest, ScenarioRequest } from "./types";

export function useHealth() {
  return useQuery({ queryKey: ["health"], queryFn: api.health });
}

export function useCityGrid(layer: "lst" | "ndvi" | "hvi" | "built") {
  return useQuery({
    queryKey: ["city-grid", layer],
    queryFn: () => api.cityGrid({ layer }),
    // The grid only changes when the pipeline re-runs (architecture.md §5's cache note) —
    // safe to treat as fresh for the lifetime of a session.
    staleTime: Infinity,
  });
}

export function useHotspots(n: number, by: HotspotsBy, unit: HotspotsUnit) {
  return useQuery({
    queryKey: ["hotspots", n, by, unit],
    queryFn: () => api.hotspots({ n, by, unit }),
  });
}

export function useExplainCell(cellId: number | null) {
  return useQuery({
    queryKey: ["explain-cell", cellId],
    queryFn: () => api.explainCell(cellId as number),
    enabled: cellId !== null,
  });
}

export function useWeather(days = 7) {
  return useQuery({ queryKey: ["weather", days], queryFn: () => api.weather(days) });
}

export function usePredict(cellId: number | null) {
  return useQuery({
    queryKey: ["predict", cellId],
    queryFn: () => api.predict(cellId as number),
    enabled: cellId !== null,
  });
}

export function useTrends(ward?: string) {
  return useQuery({ queryKey: ["trends", ward], queryFn: () => api.trends(ward) });
}

export function useAlerts(limit = 50) {
  return useQuery({
    queryKey: ["alerts", limit],
    queryFn: () => api.alerts(limit),
    // Polled, not pushed (ADR-0003) — the feed is daily-refreshed (api-reference.md), so a
    // 5-minute poll catches a new alert well within a session without hammering the backend
    // for a file that changes at most once a day.
    refetchInterval: 5 * 60_000,
  });
}

export function useScenario() {
  return useMutation({
    mutationFn: (body: ScenarioRequest) => api.scenario(body),
  });
}

/**
 * Not a `useQuery` — a chat message isn't idempotent GET data, it's an action, and the
 * backend's own cache (Supervisor's (question, data_version) TTLCache) already handles
 * repeat-question caching server-side. `useMutation` also means there is no automatic
 * refetch-on-window-focus for a resource sitting on a 20 req/day quota.
 */
export function useAgentChat() {
  return useMutation({
    mutationFn: (message: string) => api.agentChat({ message }),
  });
}

// --- Saved scenarios (Phase 6) — every hook here needs the signed-in user's Supabase access
// token; `null` means "not signed in", which the query/mutation simply refuses to run.

export function useSavedScenarios(accessToken: string | null) {
  return useQuery({
    queryKey: ["saved-scenarios"],
    queryFn: () => api.listSavedScenarios(accessToken as string),
    enabled: accessToken !== null,
  });
}

export function useSaveScenario(accessToken: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: SavedScenarioRequest) => api.saveScenario(body, accessToken as string),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["saved-scenarios"] }),
  });
}

export function useDeleteScenario(accessToken: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteScenario(id, accessToken as string),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["saved-scenarios"] }),
  });
}
