import {
  Alert,
  Box,
  Button,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Slider,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { useMemo, useState } from "react";
import type { Feature, Geometry } from "geojson";
import { GeoJSON, MapContainer, TileLayer } from "react-leaflet";

import { useCityGrid, useHotspots, useScenario } from "../api/hooks";
import type { Intervention } from "../api/types";
import { MUTED_INK, sequentialScale } from "../viz/color";

const MUMBAI_CENTER: [number, number] = [19.076, 72.8777];

interface CellProperties {
  cell_id: number;
  ward_code: string;
}

export function Scenario() {
  const wards = useHotspots(24, "hvi", "ward"); // every ward, not a ranking — reused for the
  // dropdown rather than inventing a "list wards" endpoint the backend doesn't have
  const grid = useCityGrid("lst"); // geometry source — /scenario returns cell_id + dlst, no
  // shape, the same join backend/agents/supervisor.py's build_agent_layer does server-side

  const [wardCode, setWardCode] = useState("");
  const [intervention, setIntervention] = useState<Intervention>("greening");
  const [coverage, setCoverage] = useState(1.0);
  const scenario = useScenario();

  const dlstByCell = useMemo(() => {
    if (!scenario.data) return null;
    return new Map(scenario.data.cells.map((c) => [c.cell_id, c.dlst]));
  }, [scenario.data]);

  const overlay = useMemo((): GeoJSON.FeatureCollection | null => {
    if (!dlstByCell || !grid.data) return null;
    const features = grid.data.features.filter((f) =>
      dlstByCell.has((f.properties as CellProperties).cell_id),
    );
    return { type: "FeatureCollection", features };
  }, [dlstByCell, grid.data]);

  const colorFor = useMemo(() => {
    if (!scenario.data) return () => MUTED_INK;
    // dlst is always <= 0 (a scenario only ever cools or holds — ml/scenario.py floors
    // greening at 0). One-directional magnitude, so sequential, not diverging: 0 = lightest
    // (no change), best_dlst = darkest (most cooling).
    return sequentialScale(0, scenario.data.best_dlst);
  }, [scenario.data]);

  function handleSubmit() {
    if (!wardCode) return;
    scenario.mutate({ ward_code: wardCode, intervention, coverage });
  }

  return (
    <Box sx={{ p: 3, display: "flex", flexDirection: "column", gap: 3, overflow: "auto" }}>
      <Typography variant="h6">Scenario simulator</Typography>

      <Box sx={{ display: "flex", gap: 2, alignItems: "flex-start", flexWrap: "wrap" }}>
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel id="ward-label">Ward</InputLabel>
          <Select
            labelId="ward-label"
            label="Ward"
            value={wardCode}
            onChange={(e) => setWardCode(e.target.value)}
          >
            {(wards.data?.results ?? []).map((w) => (
              <MenuItem key={w.id} value={w.id}>
                {w.id}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <ToggleButtonGroup
          value={intervention}
          exclusive
          size="small"
          onChange={(_, v: Intervention | null) => v && setIntervention(v)}
        >
          <ToggleButton value="greening">Greening</ToggleButton>
          <ToggleButton value="cool_roof">Cool roof</ToggleButton>
        </ToggleButtonGroup>

        <Box sx={{ width: 220 }}>
          <Typography variant="caption" sx={{ color: MUTED_INK }}>
            Cool-roof coverage: {intervention === "cool_roof" ? `${Math.round(coverage * 100)}%` : "—"}
          </Typography>
          <Slider
            value={coverage}
            onChange={(_, v) => setCoverage(v as number)}
            min={0}
            max={1}
            step={0.1}
            disabled={intervention === "greening"}
            size="small"
          />
          {intervention === "greening" && (
            <Typography variant="caption" sx={{ color: MUTED_INK }}>
              Ignored for greening — it always raises NDVI to a fixed target, not a coverage
              fraction.
            </Typography>
          )}
        </Box>

        <Button variant="contained" onClick={handleSubmit} disabled={!wardCode || scenario.isPending}>
          {scenario.isPending ? "Simulating…" : "Simulate"}
        </Button>
      </Box>

      {scenario.isError && (
        <Alert severity="error">Couldn't run the scenario — is the backend running?</Alert>
      )}

      {scenario.data && (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <Typography>
            {scenario.data.n_cells} cells · mean {scenario.data.mean_dlst.toFixed(2)}°C · best{" "}
            {scenario.data.best_dlst.toFixed(2)}°C
          </Typography>

          {/* Prominent, not a footnote — a clamped number that reads like a normal one is
              exactly the failure mode this disclosure exists to prevent (ADR-0006). */}
          {scenario.data.clamped && (
            <Alert severity="warning">
              {scenario.data.clamped_cells} of {scenario.data.n_cells} cells were clamped to
              the training envelope — those cells' feature values fell outside what the model
              was trained on, so their ΔLST is capped, not extrapolated.
            </Alert>
          )}

          <Alert severity="info">{scenario.data.caveat}</Alert>

          <Box sx={{ height: 360, width: "100%", maxWidth: 700 }}>
            <MapContainer
              center={MUMBAI_CENTER}
              zoom={12}
              preferCanvas
              style={{ height: "100%", width: "100%" }}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
              />
              {overlay && overlay.features.length > 0 && (
                <GeoJSON
                  key={`${wardCode}-${intervention}-${coverage}`}
                  data={overlay}
                  style={(feature) => {
                    const cellId = (feature?.properties as CellProperties | undefined)?.cell_id;
                    const dlst = cellId !== undefined ? (dlstByCell?.get(cellId) ?? 0) : 0;
                    return { fillColor: colorFor(dlst), fillOpacity: 0.85, color: "#ffffff", weight: 0.5 };
                  }}
                  onEachFeature={(feature: Feature<Geometry, CellProperties>, layerInstance) => {
                    const dlst = dlstByCell?.get(feature.properties.cell_id) ?? 0;
                    layerInstance.bindTooltip(`Cell ${feature.properties.cell_id}: ${dlst.toFixed(2)}°C`);
                  }}
                />
              )}
            </MapContainer>
          </Box>
        </Box>
      )}

      {grid.isLoading && <CircularProgress size={16} />}
    </Box>
  );
}
