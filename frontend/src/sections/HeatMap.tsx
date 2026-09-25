import {
  Alert,
  Box,
  CircularProgress,
  Drawer,
  IconButton,
  Paper,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";

import { useMemo, useState } from "react";

import type { Feature, Geometry } from "geojson";
import type { LatLngExpression, LeafletMouseEvent, Path } from "leaflet";

import { GeoJSON, MapContainer, TileLayer } from "react-leaflet";

import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import ThermostatRoundedIcon from "@mui/icons-material/ThermostatRounded";
import LocationOnRoundedIcon from "@mui/icons-material/LocationOnRounded";
import TrendingUpRoundedIcon from "@mui/icons-material/TrendingUpRounded";
import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import ForestRoundedIcon from "@mui/icons-material/ForestRounded";
import DomainRoundedIcon from "@mui/icons-material/DomainRounded";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import GridViewRoundedIcon from "@mui/icons-material/GridViewRounded";

import { useCityGrid, useExplainCell } from "../api/hooks";
import { DIVERGING, MUTED_INK } from "../viz/color";

const MUMBAI_CENTER: LatLngExpression = [19.076, 72.8777];

type LayerKey = "lst" | "ndvi" | "hvi" | "built";

const LAYER_META: Record<
  LayerKey,
  {
    label: string;
    shortLabel: string;
    unit: string;
    description: string;
    lowLabel: string;
    highLabel: string;
    colors: string[];
  }
> = {
  lst: {
    label: "Surface temperature",
    shortLabel: "LST",
    unit: "°C",
    description: "Land surface temperature across Mumbai",
    lowLabel: "Cooler",
    highLabel: "Hotter",
    colors: [
      "#fff7bc",
      "#fee391",
      "#fec44f",
      "#fe9929",
      "#ec7014",
      "#cc4c02",
      "#990000",
    ],
  },

  ndvi: {
    label: "Vegetation",
    shortLabel: "NDVI",
    unit: "",
    description: "Vegetation density and health",
    lowLabel: "Low vegetation",
    highLabel: "Healthy vegetation",
    colors: [
      "#8c510a",
      "#bf812d",
      "#dfc27d",
      "#f6e8c3",
      "#c7e9c0",
      "#74c476",
      "#238b45",
      "#005a32",
    ],
  },

  hvi: {
    label: "Heat Vulnerability Index",
    shortLabel: "HVI",
    unit: "",
    description: "Relative heat vulnerability",
    lowLabel: "Low vulnerability",
    highLabel: "High vulnerability",
    colors: [
      "#15803d",
      "#65a30d",
      "#eab308",
      "#f59e0b",
      "#f97316",
      "#ef4444",
      "#991b1b",
    ],
  },

  built: {
    label: "Built-up fraction",
    shortLabel: "Built",
    unit: "",
    description: "Built-up surface intensity",
    lowLabel: "Low built-up",
    highLabel: "High built-up",
    colors: [
      "#f8fafc",
      "#e7e5e4",
      "#d6d3d1",
      "#a8a29e",
      "#78716c",
      "#57534e",
      "#292524",
    ],
  },
};

/**
 * `/city/grid` feature properties.
 * Backend/API behaviour is unchanged.
 */
interface CellProperties {
  cell_id: number;
  ward_code: string;
  value: number;
}

/**
 * Convert a hex color into RGB.
 */
function hexToRgb(hex: string): [number, number, number] {
  const clean = hex.replace("#", "");

  const value =
    clean.length === 3
      ? clean
          .split("")
          .map((c) => c + c)
          .join("")
      : clean;

  return [
    parseInt(value.substring(0, 2), 16),
    parseInt(value.substring(2, 4), 16),
    parseInt(value.substring(4, 6), 16),
  ];
}

/**
 * Interpolate between two colors.
 */
function interpolateColor(
  start: string,
  end: string,
  amount: number
): string {
  const [r1, g1, b1] = hexToRgb(start);
  const [r2, g2, b2] = hexToRgb(end);

  const r = Math.round(r1 + (r2 - r1) * amount);
  const g = Math.round(g1 + (g2 - g1) * amount);
  const b = Math.round(b1 + (b2 - b1) * amount);

  return `rgb(${r}, ${g}, ${b})`;
}

/**
 * Create a color from a value using the currently selected
 * layer's color theme.
 */
function createColorScale(
  min: number,
  max: number,
  colors: string[]
) {
  return (value: number): string => {
    if (!Number.isFinite(value)) {
      return colors[0];
    }

    if (max <= min) {
      return colors[Math.floor(colors.length / 2)];
    }

    const normalized = Math.max(
      0,
      Math.min(1, (value - min) / (max - min))
    );

    const scaled = normalized * (colors.length - 1);
    const index = Math.min(
      colors.length - 2,
      Math.floor(scaled)
    );

    const localAmount = scaled - index;

    return interpolateColor(
      colors[index],
      colors[index + 1],
      localAmount
    );
  };
}

export function HeatMap() {
  const [layer, setLayer] = useState<LayerKey>("lst");
  const [selectedCellId, setSelectedCellId] = useState<number | null>(
    null
  );

  const { data, isLoading, isError } = useCityGrid(layer);
  const explain = useExplainCell(selectedCellId);

  const meta = LAYER_META[layer];

  const { colorFor, min, max } = useMemo(() => {
    const values = (data?.features ?? [])
      .map(
        (f) =>
          (f.properties as CellProperties).value
      )
      .filter((value) => Number.isFinite(value));

    if (values.length === 0) {
      return {
        colorFor: () => MUTED_INK,
        min: 0,
        max: 0,
      };
    }

    const lo = Math.min(...values);
    const hi = Math.max(...values);

    return {
      colorFor: createColorScale(
        lo,
        hi,
        meta.colors
      ),
      min: lo,
      max: hi,
    };
  }, [data, meta]);

  const formattedMin =
    layer === "lst"
      ? `${min.toFixed(1)}°C`
      : min.toFixed(2);

  const formattedMax =
    layer === "lst"
      ? `${max.toFixed(1)}°C`
      : max.toFixed(2);

  return (
    <Box
      sx={{
        position: "relative",
        height: "calc(100vh - 72px)",
        minHeight: 650,
        overflow: "hidden",
        bgcolor: "#e8eef0",
      }}
    >
      {/* =========================================================
          MAP
      ========================================================= */}

      <MapContainer
        center={MUMBAI_CENTER}
        zoom={11}
        preferCanvas
        zoomControl
        style={{
          height: "100%",
          width: "100%",
        }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {data && (
          <GeoJSON
            key={layer}
            data={data}
            style={(feature) => {
              const value =
                (
                  feature?.properties as
                    | CellProperties
                    | undefined
                )?.value ?? min;

              return {
                fillColor: colorFor(value),
                fillOpacity: 0.72,
                color: "#ffffff",
                weight: 0.4,
              };
            }}
            onEachFeature={(
              feature: Feature<Geometry, CellProperties>,
              layerInstance
            ) => {
              const {
                cell_id,
                ward_code,
                value,
              } = feature.properties;

              layerInstance.bindTooltip(
                `
                <div style="
                  font-family: Inter, Arial, sans-serif;
                  min-width: 160px;
                  padding: 3px;
                ">
                  <div style="
                    color:#64748b;
                    font-size:11px;
                    margin-bottom:4px;
                    text-transform:uppercase;
                    letter-spacing:.05em;
                  ">
                    ${meta.shortLabel}
                  </div>

                  <div style="
                    font-size:17px;
                    font-weight:800;
                    color:#0f172a;
                    margin-bottom:3px;
                  ">
                    ${value.toFixed(2)}${meta.unit}
                  </div>

                  <div style="
                    color:#64748b;
                    font-size:11px;
                  ">
                    Ward ${ward_code} · Cell ${cell_id}
                  </div>
                </div>
                `,
                {
                  sticky: true,
                  direction: "top",
                }
              );

              layerInstance.on("click", () =>
                setSelectedCellId(cell_id)
              );

              layerInstance.on(
                "mouseover",
                (e: LeafletMouseEvent) => {
                  (e.target as Path).setStyle({
                    weight: 2,
                    color: "#111827",
                    fillOpacity: 0.88,
                  });

                  (e.target as Path).bringToFront();
                }
              );

              layerInstance.on(
                "mouseout",
                (e: LeafletMouseEvent) => {
                  const currentValue =
                    (
                      feature.properties as CellProperties
                    ).value;

                  (e.target as Path).setStyle({
                    weight: 0.4,
                    color: "#ffffff",
                    fillOpacity: 0.72,
                    fillColor: colorFor(currentValue),
                  });
                }
              );
            }}
          />
        )}
      </MapContainer>

      {/* =========================================================
          TOP LEFT — TITLE
      ========================================================= */}

      <Paper
        elevation={0}
        sx={{
          position: "absolute",
          top: 20,
          left: 62,
          zIndex: 1000,
          width: {
            xs: "calc(100% - 82px)",
            sm: 370,
          },
          p: 2,
          borderRadius: 3,
          background:
            "linear-gradient(145deg, rgba(255,255,255,.98), rgba(248,250,250,.96))",
          border: "1px solid rgba(15,23,42,.08)",
          boxShadow:
            "0 14px 40px rgba(15,23,42,.16)",
          backdropFilter: "blur(12px)",
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1.3,
          }}
        >
          <Box
            sx={{
              width: 44,
              height: 44,
              borderRadius: 2.2,
              display: "grid",
              placeItems: "center",
              color: "#fff",
              background:
                layer === "lst"
                  ? "linear-gradient(135deg, #991b1b, #ef4444)"
                  : layer === "ndvi"
                    ? "linear-gradient(135deg, #166534, #4ade80)"
                    : layer === "hvi"
                      ? "linear-gradient(135deg, #b91c1c, #f97316)"
                      : "linear-gradient(135deg, #44403c, #78716c)",
              boxShadow:
                layer === "lst"
                  ? "0 6px 18px rgba(220,38,38,.28)"
                  : layer === "ndvi"
                    ? "0 6px 18px rgba(22,101,52,.28)"
                    : layer === "hvi"
                      ? "0 6px 18px rgba(249,115,22,.28)"
                      : "0 6px 18px rgba(68,64,60,.25)",
              flexShrink: 0,
              transition: "all .25s ease",
            }}
          >
            {layer === "ndvi" ? (
              <ForestRoundedIcon />
            ) : layer === "built" ? (
              <DomainRoundedIcon />
            ) : layer === "hvi" ? (
              <WarningAmberRoundedIcon />
            ) : (
              <ThermostatRoundedIcon />
            )}
          </Box>

          <Box sx={{ minWidth: 0 }}>
            <Typography
              sx={{
                fontSize: 19,
                fontWeight: 850,
                color: "#102a2a",
                letterSpacing: "-.025em",
                lineHeight: 1.15,
              }}
            >
              Urban Heat Overview
            </Typography>

            <Typography
              sx={{
                mt: 0.35,
                fontSize: 12,
                color: "#64748b",
              }}
            >
              Mumbai · {meta.label}
            </Typography>
          </Box>
        </Box>
      </Paper>

      {/* =========================================================
          TOP RIGHT — STATUS
      ========================================================= */}

      <Paper
        elevation={0}
        sx={{
          position: "absolute",
          top: 20,
          right: 20,
          zIndex: 1000,
          display: {
            xs: "none",
            md: "block",
          },
          borderRadius: 3,
          px: 1.6,
          py: 1.15,
          background: "rgba(255,255,255,.95)",
          border: "1px solid rgba(15,23,42,.08)",
          boxShadow:
            "0 10px 30px rgba(15,23,42,.12)",
          backdropFilter: "blur(10px)",
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
          }}
        >
          <Box
            sx={{
              width: 9,
              height: 9,
              borderRadius: "50%",
              bgcolor: "#16a34a",
              boxShadow:
                "0 0 0 4px rgba(22,163,74,.12)",
            }}
          />

          <Typography
            sx={{
              fontSize: 12,
              fontWeight: 750,
              color: "#334155",
            }}
          >
            Mumbai grid active
          </Typography>
        </Box>
      </Paper>

      {/* =========================================================
          LEFT — LAYER SELECTOR
      ========================================================= */}

      <Paper
        elevation={0}
        sx={{
          position: "absolute",
          left: 20,
          top: 142,
          zIndex: 1000,
          width: {
            xs: "calc(100% - 40px)",
            sm: 255,
          },
          borderRadius: 3,
          p: 1.2,
          background: "rgba(255,255,255,.96)",
          border: "1px solid rgba(15,23,42,.08)",
          boxShadow:
            "0 12px 35px rgba(15,23,42,.14)",
          backdropFilter: "blur(12px)",
        }}
      >
        <Typography
          sx={{
            px: 1,
            pt: 0.6,
            pb: 1,
            fontSize: 11,
            fontWeight: 800,
            color: "#64748b",
            letterSpacing: ".08em",
            textTransform: "uppercase",
          }}
        >
          Intelligence layer
        </Typography>

        <ToggleButtonGroup
          value={layer}
          exclusive
          orientation="vertical"
          onChange={(_, value: LayerKey | null) => {
            if (value) {
              setLayer(value);
              setSelectedCellId(null);
            }
          }}
          sx={{
            width: "100%",
            gap: 0.55,

            "& .MuiToggleButton-root": {
              width: "100%",
              justifyContent: "flex-start",
              textTransform: "none",
              border: "0 !important",
              borderRadius: "10px !important",
              px: 1.2,
              py: 1,
              color: "#475569",
              fontWeight: 650,
            },

            "& .MuiToggleButton-root:hover": {
              bgcolor: "#f1f5f9",
            },

            "& .Mui-selected": {
              bgcolor: "#f1f5f9 !important",
              color: "#0f172a !important",
            },
          }}
        >
          <ToggleButton value="lst">
            <ThermostatRoundedIcon
              sx={{
                mr: 1,
                fontSize: 19,
                color:
                  layer === "lst"
                    ? "#dc2626"
                    : "#64748b",
              }}
            />

            <Box sx={{ textAlign: "left" }}>
              <Typography
                sx={{
                  fontSize: 12,
                  fontWeight: 800,
                }}
              >
                Surface temperature
              </Typography>

              <Typography
                sx={{
                  fontSize: 10,
                  color: "#94a3b8",
                }}
              >
                LST · °C
              </Typography>
            </Box>
          </ToggleButton>

          <ToggleButton value="ndvi">
            <ForestRoundedIcon
              sx={{
                mr: 1,
                fontSize: 19,
                color:
                  layer === "ndvi"
                    ? "#15803d"
                    : "#64748b",
              }}
            />

            <Box sx={{ textAlign: "left" }}>
              <Typography
                sx={{
                  fontSize: 12,
                  fontWeight: 800,
                }}
              >
                Vegetation
              </Typography>

              <Typography
                sx={{
                  fontSize: 10,
                  color: "#94a3b8",
                }}
              >
                NDVI
              </Typography>
            </Box>
          </ToggleButton>

          <ToggleButton value="hvi">
            <WarningAmberRoundedIcon
              sx={{
                mr: 1,
                fontSize: 19,
                color:
                  layer === "hvi"
                    ? "#ea580c"
                    : "#64748b",
              }}
            />

            <Box sx={{ textAlign: "left" }}>
              <Typography
                sx={{
                  fontSize: 12,
                  fontWeight: 800,
                }}
              >
                Heat vulnerability
              </Typography>

              <Typography
                sx={{
                  fontSize: 10,
                  color: "#94a3b8",
                }}
              >
                HVI
              </Typography>
            </Box>
          </ToggleButton>

          <ToggleButton value="built">
            <DomainRoundedIcon
              sx={{
                mr: 1,
                fontSize: 19,
                color:
                  layer === "built"
                    ? "#57534e"
                    : "#64748b",
              }}
            />

            <Box sx={{ textAlign: "left" }}>
              <Typography
                sx={{
                  fontSize: 12,
                  fontWeight: 800,
                }}
              >
                Built-up intensity
              </Typography>

              <Typography
                sx={{
                  fontSize: 10,
                  color: "#94a3b8",
                }}
              >
                Built-up fraction
              </Typography>
            </Box>
          </ToggleButton>
        </ToggleButtonGroup>
      </Paper>

      {/* =========================================================
          RIGHT — KEY INSIGHTS
      ========================================================= */}

      <Paper
        elevation={0}
        sx={{
          position: "absolute",
          top: 90,
          right: 20,
          zIndex: 1000,
          width: 285,
          display: {
            xs: "none",
            lg: "block",
          },
          borderRadius: 3,
          p: 2,
          background: "rgba(255,255,255,.96)",
          border: "1px solid rgba(15,23,42,.08)",
          boxShadow:
            "0 12px 35px rgba(15,23,42,.14)",
          backdropFilter: "blur(12px)",
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            mb: 1.8,
          }}
        >
          <TrendingUpRoundedIcon
            sx={{
              color:
                layer === "lst"
                  ? "#dc2626"
                  : layer === "ndvi"
                    ? "#15803d"
                    : layer === "hvi"
                      ? "#ea580c"
                      : "#57534e",
              fontSize: 20,
            }}
          />

          <Typography
            sx={{
              fontSize: 14,
              fontWeight: 850,
              color: "#0f172a",
            }}
          >
            Key Insights
          </Typography>
        </Box>

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 1,
          }}
        >
          <Box
            sx={{
              p: 1.25,
              borderRadius: 2,
              bgcolor:
                layer === "lst"
                  ? "#fff7ed"
                  : layer === "ndvi"
                    ? "#f0fdf4"
                    : layer === "hvi"
                      ? "#fff7ed"
                      : "#f5f5f4",
              border:
                layer === "lst"
                  ? "1px solid #fed7aa"
                  : layer === "ndvi"
                    ? "1px solid #bbf7d0"
                    : layer === "hvi"
                      ? "1px solid #fed7aa"
                      : "1px solid #d6d3d1",
            }}
          >
            <Typography
              sx={{
                fontSize: 10,
                color:
                  layer === "lst"
                    ? "#9a3412"
                    : layer === "ndvi"
                      ? "#166534"
                      : layer === "hvi"
                        ? "#c2410c"
                        : "#57534e",
                fontWeight: 700,
              }}
            >
              Current layer
            </Typography>

            <Typography
              sx={{
                mt: 0.35,
                fontSize: 16,
                fontWeight: 850,
                color:
                  layer === "lst"
                    ? "#7c2d12"
                    : layer === "ndvi"
                      ? "#14532d"
                      : layer === "hvi"
                        ? "#9a3412"
                        : "#292524",
              }}
            >
              {meta.shortLabel}
            </Typography>
          </Box>

          <Box
            sx={{
              p: 1.25,
              borderRadius: 2,
              bgcolor: "#f8fafc",
              border: "1px solid #e2e8f0",
            }}
          >
            <Typography
              sx={{
                fontSize: 10,
                color: "#64748b",
                fontWeight: 700,
              }}
            >
              Grid cells
            </Typography>

            <Typography
              sx={{
                mt: 0.35,
                fontSize: 16,
                fontWeight: 850,
                color: "#334155",
              }}
            >
              {data?.features?.length ?? "—"}
            </Typography>
          </Box>
        </Box>

        <Box
          sx={{
            mt: 1,
            p: 1.35,
            borderRadius: 2,
            bgcolor: "#f8fafc",
            border: "1px solid #e2e8f0",
          }}
        >
          <Typography
            sx={{
              fontSize: 11,
              color: "#64748b",
              lineHeight: 1.5,
            }}
          >
            {meta.description}. Click a grid cell to
            inspect the underlying heat drivers.
          </Typography>
        </Box>

        {layer === "lst" && (
          <Box
            sx={{
              mt: 1,
              display: "flex",
              alignItems: "center",
              gap: 1,
              px: 1,
              py: 0.9,
              borderRadius: 2,
              bgcolor: "#fff1f2",
            }}
          >
            <ThermostatRoundedIcon
              sx={{
                fontSize: 17,
                color: "#dc2626",
              }}
            />

            <Typography
              sx={{
                fontSize: 11,
                fontWeight: 700,
                color: "#991b1b",
              }}
            >
              Warmer zones are highlighted in red
            </Typography>
          </Box>
        )}

        {layer === "ndvi" && (
          <Box
            sx={{
              mt: 1,
              display: "flex",
              alignItems: "center",
              gap: 1,
              px: 1,
              py: 0.9,
              borderRadius: 2,
              bgcolor: "#f0fdf4",
            }}
          >
            <ForestRoundedIcon
              sx={{
                fontSize: 17,
                color: "#15803d",
              }}
            />

            <Typography
              sx={{
                fontSize: 11,
                fontWeight: 700,
                color: "#166534",
              }}
            >
              Greener zones indicate healthier vegetation
            </Typography>
          </Box>
        )}

        {layer === "hvi" && (
          <Box
            sx={{
              mt: 1,
              display: "flex",
              alignItems: "center",
              gap: 1,
              px: 1,
              py: 0.9,
              borderRadius: 2,
              bgcolor: "#fff7ed",
            }}
          >
            <WarningAmberRoundedIcon
              sx={{
                fontSize: 17,
                color: "#ea580c",
              }}
            />

            <Typography
              sx={{
                fontSize: 11,
                fontWeight: 700,
                color: "#9a3412",
              }}
            >
              Red zones indicate higher vulnerability
            </Typography>
          </Box>
        )}

        {layer === "built" && (
          <Box
            sx={{
              mt: 1,
              display: "flex",
              alignItems: "center",
              gap: 1,
              px: 1,
              py: 0.9,
              borderRadius: 2,
              bgcolor: "#f5f5f4",
            }}
          >
            <DomainRoundedIcon
              sx={{
                fontSize: 17,
                color: "#57534e",
              }}
            />

            <Typography
              sx={{
                fontSize: 11,
                fontWeight: 700,
                color: "#44403c",
              }}
            >
              Darker zones indicate greater built-up intensity
            </Typography>
          </Box>
        )}
      </Paper>

      {/* =========================================================
          BOTTOM LEFT — DYNAMIC LEGEND
      ========================================================= */}

      {data && (
        <Paper
          elevation={0}
          sx={{
            position: "absolute",
            left: 20,
            bottom: 22,
            zIndex: 1000,
            width: {
              xs: "calc(100% - 40px)",
              sm: 320,
            },
            borderRadius: 3,
            p: 1.8,
            background: "rgba(255,255,255,.96)",
            border: "1px solid rgba(15,23,42,.08)",
            boxShadow:
              "0 12px 35px rgba(15,23,42,.14)",
            backdropFilter: "blur(12px)",
          }}
        >
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              mb: 1.2,
            }}
          >
            <Typography
              sx={{
                fontSize: 12,
                fontWeight: 850,
                color: "#0f172a",
              }}
            >
              {meta.label}
            </Typography>

            <Typography
              sx={{
                fontSize: 10,
                color: "#64748b",
              }}
            >
              {data.features.length} cells
            </Typography>
          </Box>

          {/* Gradient */}
          <Box
            sx={{
              height: 13,
              borderRadius: 999,
              background: `linear-gradient(
                90deg,
                ${meta.colors.join(", ")}
              )`,
              border: "1px solid rgba(15,23,42,.08)",
            }}
          />

          {/* Values */}
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              mt: 0.65,
            }}
          >
            <Typography
              sx={{
                fontSize: 10,
                fontWeight: 700,
                color: "#64748b",
              }}
            >
              {formattedMin}
            </Typography>

            <Typography
              sx={{
                fontSize: 10,
                color: "#94a3b8",
              }}
            >
              {meta.lowLabel}
            </Typography>

            <Typography
              sx={{
                fontSize: 10,
                color: "#94a3b8",
              }}
            >
              {meta.highLabel}
            </Typography>

            <Typography
              sx={{
                fontSize: 10,
                fontWeight: 700,
                color: "#64748b",
              }}
            >
              {formattedMax}
            </Typography>
          </Box>
        </Paper>
      )}

      {/* =========================================================
          LOADING
      ========================================================= */}

      {isLoading && (
        <Box
          sx={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 999,
            bgcolor: "rgba(248,250,252,.35)",
            backdropFilter: "blur(2px)",
          }}
        >
          <Paper
            elevation={0}
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1.5,
              px: 2.2,
              py: 1.5,
              borderRadius: 3,
              bgcolor: "rgba(255,255,255,.96)",
              boxShadow:
                "0 12px 35px rgba(15,23,42,.15)",
            }}
          >
            <CircularProgress size={22} />

            <Typography
              sx={{
                fontSize: 13,
                fontWeight: 700,
                color: "#334155",
              }}
            >
              Loading Mumbai heat grid…
            </Typography>
          </Paper>
        </Box>
      )}

      {/* =========================================================
          ERROR
      ========================================================= */}

      {isError && (
        <Alert
          severity="error"
          sx={{
            position: "absolute",
            top: 90,
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 1000,
            width: {
              xs: "calc(100% - 40px)",
              sm: "auto",
            },
            boxShadow:
              "0 10px 30px rgba(15,23,42,.15)",
            borderRadius: 2.5,
          }}
        >
          Couldn't load the grid — is the backend running?
        </Alert>
      )}

      {/* =========================================================
          CELL DETAILS DRAWER
      ========================================================= */}

      <Drawer
        anchor="right"
        open={selectedCellId !== null}
        onClose={() => setSelectedCellId(null)}
        sx={{
          "& .MuiDrawer-paper": {
            width: {
              xs: "100%",
              sm: 410,
            },
            bgcolor: "#f8fafc",
          },
        }}
      >
        <Box
          sx={{
            p: 2.5,
            borderBottom: "1px solid #e2e8f0",
            bgcolor: "#ffffff",
          }}
        >
          <Box
            sx={{
              display: "flex",
              alignItems: "flex-start",
              justifyContent: "space-between",
              gap: 2,
            }}
          >
            <Box>
              <Typography
                sx={{
                  fontSize: 11,
                  fontWeight: 800,
                  color: "#64748b",
                  letterSpacing: ".08em",
                  textTransform: "uppercase",
                }}
              >
                Cell intelligence
              </Typography>

              {explain.data && (
                <Typography
                  sx={{
                    mt: 0.5,
                    fontSize: 25,
                    fontWeight: 850,
                    color: "#0f172a",
                    letterSpacing: "-.035em",
                  }}
                >
                  Cell {explain.data.cell_id}
                </Typography>
              )}
            </Box>

            <IconButton
              onClick={() => setSelectedCellId(null)}
              size="small"
              sx={{
                bgcolor: "#f1f5f9",
                "&:hover": {
                  bgcolor: "#e2e8f0",
                },
              }}
            >
              <CloseRoundedIcon fontSize="small" />
            </IconButton>
          </Box>

          {explain.data && (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 0.7,
                mt: 0.8,
              }}
            >
              <LocationOnRoundedIcon
                sx={{
                  fontSize: 16,
                  color: "#087f78",
                }}
              />

              <Typography
                sx={{
                  fontSize: 12,
                  color: MUTED_INK,
                }}
              >
                Ward {explain.data.ward_code}
              </Typography>
            </Box>
          )}
        </Box>

        <Box sx={{ p: 2.5 }}>
          {explain.isLoading && (
            <Box
              sx={{
                minHeight: 250,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <CircularProgress />
            </Box>
          )}

          {explain.isError && (
            <Alert
              severity="error"
              sx={{
                borderRadius: 2,
              }}
            >
              Couldn't explain this cell.
            </Alert>
          )}

          {explain.data && (
            <>
              <Paper
                elevation={0}
                sx={{
                  p: 2,
                  borderRadius: 3,
                  color: "#fff",
                  background:
                    "linear-gradient(135deg, #991b1b 0%, #ef4444 100%)",
                  boxShadow:
                    "0 10px 28px rgba(220,38,38,.22)",
                }}
              >
                <Typography
                  sx={{
                    fontSize: 11,
                    opacity: 0.78,
                    fontWeight: 700,
                    textTransform: "uppercase",
                    letterSpacing: ".07em",
                  }}
                >
                  Surface temperature
                </Typography>

                <Typography
                  sx={{
                    mt: 0.3,
                    fontSize: 35,
                    fontWeight: 850,
                    lineHeight: 1,
                  }}
                >
                  {explain.data.lst_mean.toFixed(1)}°C
                </Typography>

                <Typography
                  sx={{
                    mt: 1,
                    fontSize: 12,
                    opacity: 0.88,
                  }}
                >
                  {explain.data.deviation >= 0
                    ? "+"
                    : ""}
                  {explain.data.deviation.toFixed(1)}°C
                  vs city mean of{" "}
                  {explain.data.city_mean.toFixed(1)}°C
                </Typography>
              </Paper>

              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: 1,
                  mt: 1.5,
                }}
              >
                <Box
                  sx={{
                    p: 1.5,
                    borderRadius: 2.5,
                    bgcolor: "#ffffff",
                    border: "1px solid #e2e8f0",
                  }}
                >
                  <Typography
                    sx={{
                      fontSize: 10,
                      color: "#64748b",
                      fontWeight: 700,
                    }}
                  >
                    City mean
                  </Typography>

                  <Typography
                    sx={{
                      mt: 0.4,
                      fontSize: 18,
                      fontWeight: 850,
                      color: "#0f172a",
                    }}
                  >
                    {explain.data.city_mean.toFixed(1)}°C
                  </Typography>
                </Box>

                <Box
                  sx={{
                    p: 1.5,
                    borderRadius: 2.5,
                    bgcolor:
                      explain.data.deviation >= 0
                        ? "#fff7ed"
                        : "#eff6ff",
                    border:
                      explain.data.deviation >= 0
                        ? "1px solid #fed7aa"
                        : "1px solid #bfdbfe",
                  }}
                >
                  <Typography
                    sx={{
                      fontSize: 10,
                      color:
                        explain.data.deviation >= 0
                          ? "#9a3412"
                          : "#1d4ed8",
                      fontWeight: 700,
                    }}
                  >
                    Deviation
                  </Typography>

                  <Typography
                    sx={{
                      mt: 0.4,
                      fontSize: 18,
                      fontWeight: 850,
                      color:
                        explain.data.deviation >= 0
                          ? "#c2410c"
                          : "#1d4ed8",
                    }}
                  >
                    {explain.data.deviation >= 0
                      ? "+"
                      : ""}
                    {explain.data.deviation.toFixed(1)}°C
                  </Typography>
                </Box>
              </Box>

              <Box sx={{ mt: 3 }}>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1,
                    mb: 1.4,
                  }}
                >
                  <GridViewRoundedIcon
                    sx={{
                      fontSize: 19,
                      color: "#dc2626",
                    }}
                  />

                  <Typography
                    sx={{
                      fontSize: 15,
                      fontWeight: 850,
                      color: "#0f172a",
                    }}
                  >
                    Why is this area hot?
                  </Typography>
                </Box>

                <Typography
                  sx={{
                    fontSize: 11,
                    color: "#64748b",
                    lineHeight: 1.5,
                    mb: 1.5,
                  }}
                >
                  Model drivers contributing to the
                  cell's temperature.
                </Typography>

                {explain.data.drivers.map((d) => (
                  <Box
                    key={d.feature}
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 1.2,
                      p: 1.3,
                      mb: 0.8,
                      borderRadius: 2,
                      bgcolor: "#ffffff",
                      border: "1px solid #e2e8f0",
                    }}
                  >
                    <Box
                      sx={{
                        width: 10,
                        height: 10,
                        borderRadius: "50%",
                        bgcolor:
                          d.direction === "warming"
                            ? DIVERGING.warming
                            : DIVERGING.cooling,
                        flexShrink: 0,
                      }}
                    />

                    <Box
                      sx={{
                        flex: 1,
                        minWidth: 0,
                      }}
                    >
                      <Typography
                        sx={{
                          fontSize: 12,
                          fontWeight: 750,
                          color: "#334155",
                        }}
                      >
                        {d.feature}
                      </Typography>

                      <Typography
                        sx={{
                          mt: 0.15,
                          fontSize: 10,
                          color: "#94a3b8",
                          textTransform: "capitalize",
                        }}
                      >
                        {d.direction}
                      </Typography>
                    </Box>

                    <Typography
                      sx={{
                        fontSize: 12,
                        fontWeight: 850,
                        color:
                          d.direction === "warming"
                            ? "#dc2626"
                            : "#2563eb",
                      }}
                    >
                      {d.shap_c >= 0 ? "+" : ""}
                      {d.shap_c.toFixed(2)}°C
                    </Typography>
                  </Box>
                ))}
              </Box>

              <Box
                sx={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 1,
                  mt: 2.5,
                  p: 1.4,
                  borderRadius: 2,
                  bgcolor: "#f1f5f9",
                }}
              >
                <InfoOutlinedIcon
                  sx={{
                    fontSize: 17,
                    color: "#64748b",
                    mt: 0.1,
                  }}
                />

                <Typography
                  sx={{
                    fontSize: 10.5,
                    lineHeight: 1.55,
                    color: "#64748b",
                  }}
                >
                  Positive SHAP contribution indicates a
                  warming influence, while negative
                  contribution indicates a cooling influence.
                </Typography>
              </Box>
            </>
          )}
        </Box>
      </Drawer>
    </Box>
  );
}
