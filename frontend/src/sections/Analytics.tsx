import {
  Alert,
  Box,
  CircularProgress,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useHotspots, useTrends, useWeather } from "../api/hooks";
import type { HotspotsBy, HotspotsUnit } from "../api/types";
import { CATEGORICAL, MUTED_INK, SEQUENTIAL_BLUE } from "../viz/color";

const RANK_COLOR = SEQUENTIAL_BLUE[7]; // step 450 — a single mid-dark step; one series, one hue

export function Analytics() {
  return (
    <Box sx={{ p: 3, display: "flex", flexDirection: "column", gap: 4, overflow: "auto" }}>
      <HotspotsPanel />
      <WeatherPanel />
      <TrendsPanel />
    </Box>
  );
}

function HotspotsPanel() {
  const [by, setBy] = useState<HotspotsBy>("hvi");
  const [unit, setUnit] = useState<HotspotsUnit>("ward");
  const { data, isLoading, isError } = useHotspots(10, by, unit);

  const chartData = (data?.results ?? []).map((r) => ({
    id: r.id,
    value: r.value,
    top_driver: r.top_driver,
  }));

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1 }}>
        <Typography variant="h6">Hotspots</Typography>
        <Box sx={{ display: "flex", gap: 2 }}>
          <ToggleButtonGroup
            value={by}
            exclusive
            size="small"
            onChange={(_, v: HotspotsBy | null) => v && setBy(v)}
          >
            <ToggleButton value="hvi">HVI</ToggleButton>
            <ToggleButton value="lst">LST</ToggleButton>
          </ToggleButtonGroup>
          <ToggleButtonGroup
            value={unit}
            exclusive
            size="small"
            onChange={(_, v: HotspotsUnit | null) => v && setUnit(v)}
          >
            <ToggleButton value="ward">Ward</ToggleButton>
            <ToggleButton value="cell">Cell</ToggleButton>
          </ToggleButtonGroup>
        </Box>
      </Box>

      {isLoading && <CircularProgress size={24} />}
      {isError && <Alert severity="error">Couldn't load hotspots — is the backend running?</Alert>}

      {data && (
        <Box sx={{ display: "flex", gap: 3, flexWrap: "wrap" }}>
          <Box sx={{ width: 420, height: 320 }}>
            <ResponsiveContainer>
              <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 24 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e1e0d9" />
                <XAxis type="number" tick={{ fontSize: 12, fill: MUTED_INK }} />
                <YAxis
                  type="category"
                  dataKey="id"
                  // Ward codes are short ("B", "H/E"); cell_ids are 11-digit numbers — a
                  // fixed width truncated them (found live: "549001410" instead of
                  // "10549001410", the leading digits silently cut).
                  width={unit === "cell" ? 90 : 60}
                  tick={{ fontSize: 12, fill: MUTED_INK }}
                />
                <Tooltip
                  formatter={(value) => (typeof value === "number" ? value.toFixed(2) : value)}
                  labelFormatter={(id) => `${unit === "ward" ? "Ward" : "Cell"} ${String(id)}`}
                />
                <Bar dataKey="value" fill={RANK_COLOR} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Box>

          <TableContainer component={Paper} variant="outlined" sx={{ maxWidth: 480 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{unit === "ward" ? "Ward" : "Cell"}</TableCell>
                  <TableCell align="right">{by.toUpperCase()}</TableCell>
                  <TableCell align="right">Population</TableCell>
                  <TableCell>Top driver</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.results.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell>{r.id}</TableCell>
                    <TableCell align="right">{r.value.toFixed(2)}</TableCell>
                    <TableCell align="right">{Math.round(r.population).toLocaleString()}</TableCell>
                    <TableCell>{r.top_driver ?? "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}
    </Box>
  );
}

function WeatherPanel() {
  const { data, isLoading, isError } = useWeather(7);
  const chartData = (data?.days ?? []).map((d) => ({
    date: d.date.slice(5), // MM-DD — the year is redundant at a 7-day horizon
    Max: d.temp_max_c,
    Min: d.temp_min_c,
  }));

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Weather forecast
      </Typography>
      {isLoading && <CircularProgress size={24} />}
      {isError && <Alert severity="error">Couldn't load the forecast.</Alert>}
      {data && (
        <Box sx={{ width: 500, height: 260 }}>
          <ResponsiveContainer>
            <LineChart data={chartData} margin={{ left: 8, right: 24 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e1e0d9" />
              <XAxis dataKey="date" tick={{ fontSize: 12, fill: MUTED_INK }} />
              <YAxis
                tick={{ fontSize: 12, fill: MUTED_INK }}
                label={{ value: "°C (air)", angle: -90, position: "insideLeft", fill: MUTED_INK }}
              />
              <Tooltip
                formatter={(value) => (typeof value === "number" ? `${value.toFixed(1)}°C` : value)}
              />
              <Legend />
              {/* Max=orange/Min=blue is a fixed, intuitive assignment (warm/cool), not a
                  re-ranked one — the categorical order stays the same every render. */}
              <Line type="monotone" dataKey="Max" stroke={CATEGORICAL[1]} strokeWidth={2} dot={{ r: 4 }} />
              <Line type="monotone" dataKey="Min" stroke={CATEGORICAL[0]} strokeWidth={2} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </Box>
      )}
    </Box>
  );
}

function TrendsPanel() {
  const { data, isLoading } = useTrends();
  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        LST trend
      </Typography>
      {isLoading && <CircularProgress size={24} />}
      {data && !data.available && (
        <Alert severity="info" sx={{ maxWidth: 500 }}>
          {data.note}
        </Alert>
      )}
    </Box>
  );
}
