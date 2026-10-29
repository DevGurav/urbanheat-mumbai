/**
 * A thin fetch wrapper — one typed function per backend endpoint. No codegen (Phase 5
 * kickoff decision, PROGRESS.md): every function here is hand-matched against
 * backend/routers/*.py and backend/schemas.py.
 *
 * Errors: every non-2xx response is api-reference.md's {detail, error_code} shape
 * (backend/errors.py + main.py's exception handler) — thrown as an ApiError so callers can
 * branch on error_code (e.g. "agent_layer_unavailable" vs "agent_upstream_unavailable").
 */
import type {
  AgentChatRequest,
  AgentChatResponse,
  AlertsResponse,
  ApiErrorBody,
  ExplainResponse,
  Health,
  HotspotsBy,
  HotspotsResponse,
  HotspotsUnit,
  MonitoringCheckResponse,
  PredictResponse,
  ReportRequest,
  SavedScenario,
  SavedScenarioRequest,
  SavedScenariosResponse,
  ScenarioRequest,
  ScenarioResponse,
  TrendsResponse,
  WeatherResponse,
} from "./types";

const BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  readonly status: number;
  readonly errorCode: string | null;

  constructor(status: number, body: ApiErrorBody) {
    super(body.detail);
    this.name = "ApiError";
    this.status = status;
    this.errorCode = body.error_code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({
      detail: response.statusText,
      error_code: null,
    }))) as ApiErrorBody;
    throw new ApiError(response.status, body);
  }
  // DELETE /scenarios/{id} returns 204 with no body — nothing to parse.
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/** POST /reports/generate returns a PDF binary, not JSON — its own fetch, not `request<T>`,
 * but the same {detail, error_code} parsing on a non-2xx response. */
async function requestBlob(path: string, init?: RequestInit): Promise<Blob> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({
      detail: response.statusText,
      error_code: null,
    }))) as ApiErrorBody;
    throw new ApiError(response.status, body);
  }
  return response.blob();
}

const OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast";

/** Browser-side fallback for GET /weather — mirrors backend/services.py's `_fetch_weather`. */
async function fetchWeatherDirect(days: number): Promise<WeatherResponse> {
  const params = new URLSearchParams({
    latitude: "19.076",
    longitude: "72.8777",
    daily:
      "temperature_2m_max,temperature_2m_min,relative_humidity_2m_mean,wind_speed_10m_max,precipitation_sum",
    forecast_days: String(days),
    wind_speed_unit: "ms",
    timezone: "Asia/Kolkata",
  });
  const response = await fetch(`${OPEN_METEO_URL}?${params.toString()}`);
  if (!response.ok) throw new ApiError(response.status, { detail: "Weather provider unavailable", error_code: "weather_upstream_unavailable" });
  const { daily } = (await response.json()) as {
    daily: {
      time: string[];
      temperature_2m_max: number[];
      temperature_2m_min: number[];
      relative_humidity_2m_mean: number[];
      wind_speed_10m_max: number[];
      precipitation_sum: number[];
    };
  };
  return {
    source: "open-meteo",
    days: daily.time.map((date, i) => ({
      date,
      temp_max_c: daily.temperature_2m_max[i],
      temp_min_c: daily.temperature_2m_min[i],
      humidity_mean_pct: daily.relative_humidity_2m_mean[i],
      wind_speed_max_ms: daily.wind_speed_10m_max[i],
      precipitation_sum_mm: daily.precipitation_sum[i],
    })),
  };
}

function authHeader(accessToken: string): HeadersInit {
  return { Authorization: `Bearer ${accessToken}` };
}

function query(params: Record<string, string | number | boolean | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined);
  if (entries.length === 0) return "";
  const search = new URLSearchParams(entries.map(([k, v]) => [k, String(v)]));
  return `?${search.toString()}`;
}

export const api = {
  health: () => request<Health>("/health"),

  cityGrid: (params: { layer?: "lst" | "ndvi" | "hvi" | "built"; bbox?: string } = {}) =>
    request<GeoJSON.FeatureCollection>(`/city/grid${query(params)}`),

  hotspots: (params: { n?: number; by?: HotspotsBy; unit?: HotspotsUnit } = {}) =>
    request<HotspotsResponse>(`/hotspots${query(params)}`),

  explainCell: (cellId: number, top = 3) =>
    request<ExplainResponse>(`/explain/${cellId}${query({ top })}`),

  weather: async (days = 7): Promise<WeatherResponse> => {
    try {
      return await request<WeatherResponse>(`/weather${query({ days })}`);
    } catch {
      // Open-Meteo's free tier rate-limits shared server IPs (the free host's 429s), but not an
      // individual visitor's browser, and it allows cross-origin calls. So when the backend
      // can't serve a forecast, ask the provider directly — same variables, same units.
      return fetchWeatherDirect(days);
    }
  },

  predict: (cellId: number) => request<PredictResponse>(`/predict${query({ cell_id: cellId })}`),

  scenario: (body: ScenarioRequest) =>
    request<ScenarioResponse>("/scenario", { method: "POST", body: JSON.stringify(body) }),

  trends: (ward?: string) => request<TrendsResponse>(`/trends${query({ ward })}`),

  agentChat: (body: AgentChatRequest) =>
    request<AgentChatResponse>("/agent/chat", { method: "POST", body: JSON.stringify(body) }),

  monitoringCheck: () =>
    request<MonitoringCheckResponse>("/monitoring/check", { method: "POST" }),

  alerts: (limit = 50) => request<AlertsResponse>(`/alerts${query({ limit })}`),

  // --- Saved scenarios (Phase 6) — every call needs the caller's Supabase session token;
  // /scenarios/* is JWT-gated (api-reference.md), unlike everything above.
  listSavedScenarios: (accessToken: string) =>
    request<SavedScenariosResponse>("/scenarios", { headers: authHeader(accessToken) }),

  saveScenario: (body: SavedScenarioRequest, accessToken: string) =>
    request<SavedScenario>("/scenarios", {
      method: "POST",
      body: JSON.stringify(body),
      headers: authHeader(accessToken),
    }),

  deleteScenario: (id: string, accessToken: string) =>
    request<void>(`/scenarios/${id}`, { method: "DELETE", headers: authHeader(accessToken) }),

  generateReport: (body: ReportRequest) =>
    requestBlob("/reports/generate", { method: "POST", body: JSON.stringify(body) }),
};
