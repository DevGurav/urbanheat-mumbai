/**
 * TypeScript mirrors of backend/schemas.py — hand-written, not generated (Phase 5 kickoff,
 * PROGRESS.md, 2026-07-27): conventions.md's "API response types mirror the backend Pydantic
 * schemas" is read literally. Field names match the JSON wire format exactly (snake_case),
 * not camelCased, so there is one name to keep in sync with the backend, not two.
 *
 * Every response carrying model output includes `model_version`; a temperature field carries
 * `measurement` so it can never be mistaken for air temperature (ADR-0005).
 */

export const MEASUREMENT = "land_surface_temperature" as const;

export interface Health {
  status: string;
  model_version: string;
  data_version: string;
  uptime_s: number;
  n_cells: number;
}

export interface Driver {
  feature: string;
  value: number;
  shap_c: number;
  direction: "warming" | "cooling";
}

export interface ExplainResponse {
  cell_id: number;
  ward_code: string;
  lst_mean: number;
  city_mean: number;
  deviation: number;
  measurement: typeof MEASUREMENT;
  drivers: Driver[];
  model_version: string;
}

export interface HotspotEntry {
  id: string;
  ward_code: string;
  value: number;
  population: number;
  top_driver: string | null;
  top_driver_shap_c: number | null;
}

export type HotspotsBy = "hvi" | "lst";
export type HotspotsUnit = "ward" | "cell";

export interface HotspotsResponse {
  by: HotspotsBy;
  unit: HotspotsUnit;
  model_version: string;
  data_version: string;
  results: HotspotEntry[];
}

export interface WeatherDay {
  date: string;
  temp_max_c: number;
  temp_min_c: number;
  humidity_mean_pct: number;
  wind_speed_max_ms: number;
  precipitation_sum_mm: number;
}

export interface WeatherResponse {
  source: string;
  days: WeatherDay[];
}

export interface PredictResponse {
  cell_id: number;
  ward_code: string;
  predicted_lst: number;
  observed_lst: number;
  residual: number;
  measurement: typeof MEASUREMENT;
  model_version: string;
}

export type Intervention = "greening" | "cool_roof";

export interface ScenarioRequest {
  ward_code: string;
  intervention: Intervention;
  /** Cool-roof coverage fraction (0-1). Ignored for greening. */
  coverage?: number;
}

export interface ScenarioCell {
  cell_id: number;
  lst_mean: number;
  dlst: number;
}

export interface ScenarioResponse {
  ward_code: string;
  intervention: Intervention;
  coverage: number;
  measurement: typeof MEASUREMENT;
  n_cells: number;
  mean_dlst: number;
  best_dlst: number;
  clamped: boolean;
  clamped_cells: number;
  caveat: string;
  model_version: string;
  cells: ScenarioCell[];
}

export interface TrendsResponse {
  available: boolean;
  note: string;
}

export interface AgentChatRequest {
  message: string;
  /** Accepted for contract compatibility; not used yet (no persisted chat memory). */
  session_id?: string | null;
}

export interface AgentToolCall {
  name: string;
  args: Record<string, unknown>;
  result: string;
}

export type AgentName = "copilot" | "planning" | "digital_twin";

export interface AgentChatResponse {
  agent: AgentName;
  text: string;
  tool_calls: AgentToolCall[];
  /** GeoJSON FeatureCollection from a simulate_scenario call, or null — not every answer maps. */
  layer: GeoJSON.FeatureCollection | null;
}

export type AlertSeverity = "advisory" | "heat_wave" | "severe_heat_wave";

export interface AlertPayload {
  date: string;
  severity: AlertSeverity;
  forecast_max_c: number;
  wards_affected: string[];
  summary: string;
  caveat: string;
}

export interface MonitoringCheckResponse {
  triggered: boolean;
  alert: AlertPayload | null;
}

export interface AlertsResponse {
  alerts: AlertPayload[];
}

export interface SavedScenarioRequest {
  ward_code: string;
  intervention: Intervention;
  coverage?: number;
}

export interface SavedScenario {
  id: string;
  ward_code: string;
  intervention: Intervention;
  coverage: number;
  saved_at: string;
}

export interface SavedScenariosResponse {
  scenarios: SavedScenario[];
}

/** {detail, error_code} — api-reference.md's error shape, every non-2xx response. */
export interface ApiErrorBody {
  detail: string;
  error_code: string | null;
}
