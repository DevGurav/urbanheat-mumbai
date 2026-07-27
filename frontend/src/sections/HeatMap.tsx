import {
  Alert,
  Box,
  CircularProgress,
  Drawer,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { useMemo, useState } from "react";
import type { Feature, Geometry } from "geojson";
import type { LatLngExpression, LeafletMouseEvent, Path } from "leaflet";
import { GeoJSON, MapContainer, TileLayer } from "react-leaflet";

import { useCityGrid, useExplainCell } from "../api/hooks";
import { DIVERGING, MUTED_INK, sequentialScale } from "../viz/color";
import { SequentialLegend } from "../viz/SequentialLegend";

const MUMBAI_CENTER: LatLngExpression = [19.076, 72.8777];

type LayerKey = "lst" | "ndvi" | "hvi" | "built";

const LAYER_META: Record<LayerKey, { label: string; unit: string }> = {
  lst: { label: "Surface temperature", unit: "°C" },
  ndvi: { label: "NDVI (vegetation)", unit: "" },
  hvi: { label: "Heat Vulnerability Index", unit: "" },
  built: { label: "Built-up fraction", unit: "" },
};

/** `/city/grid`'s feature properties (backend/routers/grid.py) — react-leaflet's `GeoJSON`
 * isn't generic-parameterized in this version, so properties arrive untyped from Leaflet's
 * own API; this is the one boundary where a cast stands in for it. */
interface CellProperties {
  cell_id: number;
  ward_code: string;
  value: number;
}

export function HeatMap() {
  const [layer, setLayer] = useState<LayerKey>("lst");
  const [selectedCellId, setSelectedCellId] = useState<number | null>(null);
  const { data, isLoading, isError } = useCityGrid(layer);
  const explain = useExplainCell(selectedCellId);
  const meta = LAYER_META[layer];

  const { colorFor, min, max } = useMemo(() => {
    const values = (data?.features ?? []).map((f) => (f.properties as CellProperties).value);
    if (values.length === 0) return { colorFor: () => MUTED_INK, min: 0, max: 0 };
    const lo = Math.min(...values);
    const hi = Math.max(...values);
    return { colorFor: sequentialScale(lo, hi), min: lo, max: hi };
  }, [data]);

  return (
    <Box sx={{ position: "relative", height: "100%" }}>
      {/* top: 16 + left: 60 clears Leaflet's default zoom control, which also docks
          top-left — found by screenshot, not by reading Leaflet's source. */}
      <Box sx={{ position: "absolute", top: 16, left: 60, zIndex: 1000 }}>
        <ToggleButtonGroup
          value={layer}
          exclusive
          onChange={(_, value: LayerKey | null) => value && setLayer(value)}
          size="small"
          sx={{ bgcolor: "background.paper" }}
        >
          <ToggleButton value="lst">LST</ToggleButton>
          <ToggleButton value="ndvi">NDVI</ToggleButton>
          <ToggleButton value="hvi">HVI</ToggleButton>
          <ToggleButton value="built">Built</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {isLoading && (
        <Box
          sx={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 999,
          }}
        >
          <CircularProgress />
        </Box>
      )}
      {isError && (
        <Alert severity="error" sx={{ position: "absolute", top: 72, left: 16, zIndex: 1000 }}>
          Couldn't load the grid — is the backend running?
        </Alert>
      )}

      <MapContainer
        center={MUMBAI_CENTER}
        zoom={11}
        preferCanvas
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        {data && (
          <GeoJSON
            // Force a clean remount per layer — a style/tooltip closure captured over the
            // previous layer's colorFor and label would otherwise linger on old features.
            key={layer}
            data={data}
            style={(feature) => {
              const value = (feature?.properties as CellProperties | undefined)?.value ?? min;
              return { fillColor: colorFor(value), fillOpacity: 0.75, color: "#ffffff", weight: 0.3 };
            }}
            onEachFeature={(feature: Feature<Geometry, CellProperties>, layerInstance) => {
              const { cell_id, ward_code, value } = feature.properties;
              layerInstance.bindTooltip(
                `Ward ${ward_code} · cell ${cell_id}<br/>${meta.label}: ${value.toFixed(2)}${meta.unit}`,
                { sticky: true },
              );
              layerInstance.on("click", () => setSelectedCellId(cell_id));
              layerInstance.on("mouseover", (e: LeafletMouseEvent) => {
                (e.target as Path).setStyle({ weight: 2, color: "#0b0b0b" });
              });
              layerInstance.on("mouseout", (e: LeafletMouseEvent) => {
                (e.target as Path).setStyle({ weight: 0.3, color: "#ffffff" });
              });
            }}
          />
        )}
      </MapContainer>

      {data && <SequentialLegend title={meta.label} unit={meta.unit} min={min} max={max} />}

      <Drawer
        anchor="right"
        open={selectedCellId !== null}
        onClose={() => setSelectedCellId(null)}
      >
        <Box sx={{ width: 340, p: 2 }}>
          {explain.isLoading && <CircularProgress />}
          {explain.isError && <Alert severity="error">Couldn't explain this cell.</Alert>}
          {explain.data && (
            <>
              <Typography variant="h6">Cell {explain.data.cell_id}</Typography>
              <Typography variant="body2" sx={{ color: MUTED_INK }}>
                Ward {explain.data.ward_code}
              </Typography>
              <Typography sx={{ mt: 1 }}>
                {explain.data.lst_mean.toFixed(1)}°C surface temperature (
                {explain.data.deviation >= 0 ? "+" : ""}
                {explain.data.deviation.toFixed(1)}°C vs city mean{" "}
                {explain.data.city_mean.toFixed(1)}°C)
              </Typography>
              <Typography variant="subtitle2" sx={{ mt: 2 }}>
                Why
              </Typography>
              {explain.data.drivers.map((d) => (
                <Box key={d.feature} sx={{ display: "flex", alignItems: "center", gap: 1, mt: 0.5 }}>
                  <Box
                    sx={{
                      width: 10,
                      height: 10,
                      borderRadius: "50%",
                      bgcolor: d.direction === "warming" ? DIVERGING.warming : DIVERGING.cooling,
                      flexShrink: 0,
                    }}
                  />
                  <Typography variant="body2">
                    {d.feature}: {d.shap_c >= 0 ? "+" : ""}
                    {d.shap_c.toFixed(2)}°C ({d.direction})
                  </Typography>
                </Box>
              ))}
            </>
          )}
        </Box>
      </Drawer>
    </Box>
  );
}
