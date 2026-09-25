import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
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

const RANK_COLOR = SEQUENTIAL_BLUE[7];

export function Analytics() {
  return (
    <Box
      sx={{
        height: "100%",
        overflow: "auto",
        bgcolor: "#f4f8f7",
        p: { xs: 2, md: 3.5 },
      }}
    >
      <Box
        sx={{
          maxWidth: 1500,
          mx: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 3,
        }}
      >
        {/* PAGE HEADER */}
        <Box
          sx={{
            display: "flex",
            alignItems: { xs: "flex-start", md: "center" },
            justifyContent: "space-between",
            gap: 2,
            flexWrap: "wrap",
          }}
        >
          <Box>
            <Typography
              sx={{
                color: "#0b3b36",
                fontSize: { xs: "1.65rem", md: "2rem" },
                fontWeight: 800,
                letterSpacing: "-0.04em",
                lineHeight: 1.1,
              }}
            >
              Heat intelligence
            </Typography>

            <Typography
              sx={{
                mt: 0.7,
                color: MUTED_INK,
                fontSize: "0.92rem",
              }}
            >
              Explore Mumbai heat hotspots, weather conditions and thermal
              trends.
            </Typography>
          </Box>

          <Chip
            label="Live city analytics"
            sx={{
              height: 34,
              px: 0.8,
              borderRadius: 2,
              bgcolor: "#e0f2ec",
              color: "#11604f",
              fontWeight: 700,
              border: "1px solid #c6e5da",
            }}
          />
        </Box>

        <HotspotsPanel />
        <WeatherPanel />
        <TrendsPanel />
      </Box>
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
    <Card
      elevation={0}
      sx={{
        borderRadius: 3.5,
        border: "1px solid #dce8e5",
        bgcolor: "#ffffff",
        overflow: "hidden",
      }}
    >
      {/* HEADER */}
      <Box
        sx={{
          px: { xs: 2, md: 3 },
          py: 2.5,
          display: "flex",
          alignItems: { xs: "flex-start", md: "center" },
          justifyContent: "space-between",
          gap: 2,
          flexWrap: "wrap",
          background:
            "linear-gradient(135deg, rgba(7,66,61,0.06), rgba(31,117,102,0.02))",
          borderBottom: "1px solid #e5eeec",
        }}
      >
        <Box>
          <Typography
            sx={{
              color: "#0b3b36",
              fontWeight: 800,
              fontSize: "1.15rem",
              letterSpacing: "-0.02em",
            }}
          >
            Hotspot ranking
          </Typography>

          <Typography
            sx={{
              color: MUTED_INK,
              fontSize: "0.82rem",
              mt: 0.35,
            }}
          >
            Highest-risk locations across the city
          </Typography>
        </Box>

        <Box
          sx={{
            display: "flex",
            gap: 1,
            flexWrap: "wrap",
            width: { xs: "100%", sm: "auto" },
          }}
        >
          <ToggleButtonGroup
            value={by}
            exclusive
            size="small"
            onChange={(_, v: HotspotsBy | null) => v && setBy(v)}
            sx={{
              "& .MuiToggleButton-root": {
                px: 1.7,
                py: 0.65,
                textTransform: "none",
                fontWeight: 700,
                color: "#52706a",
                borderColor: "#d5e3df",
              },
              "& .Mui-selected": {
                bgcolor: "#0b5d50 !important",
                color: "#ffffff !important",
              },
            }}
          >
            <ToggleButton value="hvi">HVI</ToggleButton>
            <ToggleButton value="lst">LST</ToggleButton>
          </ToggleButtonGroup>

          <ToggleButtonGroup
            value={unit}
            exclusive
            size="small"
            onChange={(_, v: HotspotsUnit | null) => v && setUnit(v)}
            sx={{
              "& .MuiToggleButton-root": {
                px: 1.7,
                py: 0.65,
                textTransform: "none",
                fontWeight: 700,
                color: "#52706a",
                borderColor: "#d5e3df",
              },
              "& .Mui-selected": {
                bgcolor: "#164e63 !important",
                color: "#ffffff !important",
              },
            }}
          >
            <ToggleButton value="ward">Ward</ToggleButton>
            <ToggleButton value="cell">Cell</ToggleButton>
          </ToggleButtonGroup>
        </Box>
      </Box>

      <CardContent sx={{ p: { xs: 2, md: 3 } }}>
        {isLoading && (
          <Box
            sx={{
              minHeight: 300,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 1.5,
              }}
            >
              <CircularProgress size={30} sx={{ color: "#0b5d50" }} />

              <Typography variant="body2" color="text.secondary">
                Loading hotspot intelligence...
              </Typography>
            </Box>
          </Box>
        )}

        {isError && (
          <Alert
            severity="error"
            sx={{
              borderRadius: 2.5,
              mb: 1,
            }}
          >
            Couldn't load hotspots — is the backend running?
          </Alert>
        )}

        {data && (
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                lg: "minmax(0, 1.35fr) minmax(420px, 0.95fr)",
              },
              gap: 3,
              alignItems: "stretch",
            }}
          >
            {/* CHART */}
            <Paper
              elevation={0}
              sx={{
                minHeight: 390,
                borderRadius: 3,
                border: "1px solid #e1ebe8",
                bgcolor: "#fbfdfc",
                p: { xs: 1, md: 2 },
                overflow: "hidden",
              }}
            >
              <Box
                sx={{
                  px: 1,
                  pt: 0.5,
                  pb: 1,
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <Typography
                  sx={{
                    fontWeight: 750,
                    color: "#244b45",
                    fontSize: "0.9rem",
                  }}
                >
                  Top 10 {unit === "ward" ? "wards" : "cells"}
                </Typography>

                <Typography
                  sx={{
                    color: MUTED_INK,
                    fontSize: "0.75rem",
                  }}
                >
                  {by === "hvi" ? "Heat vulnerability" : "Surface temperature"}
                </Typography>
              </Box>

              <Box sx={{ width: "100%", height: 340 }}>
                <ResponsiveContainer>
                  <BarChart
                    data={chartData}
                    layout="vertical"
                    margin={{
                      top: 5,
                      right: 28,
                      bottom: 5,
                      left: unit === "cell" ? 15 : 8,
                    }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      horizontal={false}
                      stroke="#e2ebe8"
                    />

                    <XAxis
                      type="number"
                      tick={{
                        fontSize: 11,
                        fill: MUTED_INK,
                      }}
                      axisLine={{ stroke: "#d9e5e2" }}
                      tickLine={false}
                    />

                    <YAxis
                      type="category"
                      dataKey="id"
                      width={unit === "cell" ? 92 : 60}
                      tick={{
                        fontSize: 11,
                        fill: "#4b6862",
                      }}
                      axisLine={false}
                      tickLine={false}
                    />

                    <Tooltip
                      cursor={{ fill: "rgba(11,93,80,0.05)" }}
                      contentStyle={{
                        borderRadius: 12,
                        border: "1px solid #d8e6e2",
                        boxShadow: "0 10px 30px rgba(15,55,49,0.12)",
                        fontSize: 12,
                      }}
                      formatter={(value) =>
                        typeof value === "number"
                          ? value.toFixed(2)
                          : value
                      }
                      labelFormatter={(id) =>
                        `${unit === "ward" ? "Ward" : "Cell"} ${String(id)}`
                      }
                    />

                    <Bar
                      dataKey="value"
                      fill={RANK_COLOR}
                      radius={[0, 7, 7, 0]}
                      barSize={18}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </Box>
            </Paper>

            {/* TABLE */}
            <Paper
              elevation={0}
              sx={{
                borderRadius: 3,
                border: "1px solid #e1ebe8",
                bgcolor: "#ffffff",
                overflow: "hidden",
              }}
            >
              <Box
                sx={{
                  px: 2,
                  py: 1.6,
                  borderBottom: "1px solid #e5eeec",
                  bgcolor: "#f8fbfa",
                }}
              >
                <Typography
                  sx={{
                    fontWeight: 750,
                    color: "#244b45",
                    fontSize: "0.9rem",
                  }}
                >
                  Hotspot details
                </Typography>
              </Box>

              <TableContainer
                sx={{
                  maxHeight: 350,
                  "&::-webkit-scrollbar": {
                    width: 6,
                    height: 6,
                  },
                  "&::-webkit-scrollbar-thumb": {
                    bgcolor: "#cbdcd8",
                    borderRadius: 10,
                  },
                }}
              >
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell
                        sx={{
                          bgcolor: "#f8fbfa",
                          color: "#54716b",
                          fontWeight: 800,
                          fontSize: "0.72rem",
                          borderBottom: "1px solid #dfeae7",
                        }}
                      >
                        {unit === "ward" ? "Ward" : "Cell"}
                      </TableCell>

                      <TableCell
                        align="right"
                        sx={{
                          bgcolor: "#f8fbfa",
                          color: "#54716b",
                          fontWeight: 800,
                          fontSize: "0.72rem",
                          borderBottom: "1px solid #dfeae7",
                        }}
                      >
                        {by.toUpperCase()}
                      </TableCell>

                      <TableCell
                        align="right"
                        sx={{
                          bgcolor: "#f8fbfa",
                          color: "#54716b",
                          fontWeight: 800,
                          fontSize: "0.72rem",
                          borderBottom: "1px solid #dfeae7",
                        }}
                      >
                        Population
                      </TableCell>

                      <TableCell
                        sx={{
                          bgcolor: "#f8fbfa",
                          color: "#54716b",
                          fontWeight: 800,
                          fontSize: "0.72rem",
                          borderBottom: "1px solid #dfeae7",
                        }}
                      >
                        Top driver
                      </TableCell>
                    </TableRow>
                  </TableHead>

                  <TableBody>
                    {data.results.map((r, index) => (
                      <TableRow
                        key={r.id}
                        sx={{
                          "&:hover": {
                            bgcolor: "#f5faf8",
                          },
                          "& td": {
                            borderBottom: "1px solid #edf2f0",
                          },
                        }}
                      >
                        <TableCell>
                          <Box
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              gap: 1,
                            }}
                          >
                            <Box
                              sx={{
                                width: 24,
                                height: 24,
                                borderRadius: "7px",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                bgcolor:
                                  index < 3 ? "#dff1eb" : "#eef4f2",
                                color:
                                  index < 3 ? "#0b5d50" : "#607a74",
                                fontWeight: 800,
                                fontSize: "0.68rem",
                                flexShrink: 0,
                              }}
                            >
                              {index + 1}
                            </Box>

                            <Typography
                              sx={{
                                fontWeight: 700,
                                fontSize: "0.8rem",
                                color: "#284d47",
                              }}
                            >
                              {r.id}
                            </Typography>
                          </Box>
                        </TableCell>

                        <TableCell
                          align="right"
                          sx={{
                            fontWeight: 800,
                            color: "#174d44",
                            fontSize: "0.8rem",
                          }}
                        >
                          {r.value.toFixed(2)}
                        </TableCell>

                        <TableCell
                          align="right"
                          sx={{
                            color: "#5e7771",
                            fontSize: "0.78rem",
                          }}
                        >
                          {Math.round(r.population).toLocaleString()}
                        </TableCell>

                        <TableCell
                          sx={{
                            color: "#5e7771",
                            fontSize: "0.78rem",
                            maxWidth: 140,
                          }}
                        >
                          {r.top_driver ?? "—"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

function WeatherPanel() {
  const { data, isLoading, isError } = useWeather(7);

  const chartData = (data?.days ?? []).map((d) => ({
    date: d.date.slice(5),
    Max: d.temp_max_c,
    Min: d.temp_min_c,
  }));

  return (
    <Card
      elevation={0}
      sx={{
        borderRadius: 3.5,
        border: "1px solid #dce8e5",
        bgcolor: "#ffffff",
        overflow: "hidden",
      }}
    >
      <Box
        sx={{
          px: { xs: 2, md: 3 },
          py: 2.5,
          background:
            "linear-gradient(135deg, rgba(20,87,115,0.07), rgba(7,66,61,0.02))",
          borderBottom: "1px solid #e5eeec",
        }}
      >
        <Typography
          sx={{
            color: "#0b3b36",
            fontWeight: 800,
            fontSize: "1.15rem",
            letterSpacing: "-0.02em",
          }}
        >
          Weather outlook
        </Typography>

        <Typography
          sx={{
            color: MUTED_INK,
            fontSize: "0.82rem",
            mt: 0.35,
          }}
        >
          Seven-day air temperature forecast
        </Typography>
      </Box>

      <CardContent sx={{ p: { xs: 2, md: 3 } }}>
        {isLoading && (
          <Box
            sx={{
              height: 300,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 1.5,
              }}
            >
              <CircularProgress size={30} sx={{ color: "#164e63" }} />

              <Typography variant="body2" color="text.secondary">
                Loading weather forecast...
              </Typography>
            </Box>
          </Box>
        )}

        {isError && (
          <Alert
            severity="error"
            sx={{
              borderRadius: 2.5,
            }}
          >
            Couldn't load the forecast.
          </Alert>
        )}

        {data && (
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                md: "minmax(0, 1.6fr) minmax(210px, 0.5fr)",
              },
              gap: 3,
            }}
          >
            <Paper
              elevation={0}
              sx={{
                height: 330,
                borderRadius: 3,
                border: "1px solid #e1ebe8",
                bgcolor: "#fbfdfc",
                p: 1.5,
              }}
            >
              <ResponsiveContainer>
                <LineChart
                  data={chartData}
                  margin={{
                    top: 15,
                    right: 25,
                    bottom: 10,
                    left: 5,
                  }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="#e1ebe8"
                    vertical={false}
                  />

                  <XAxis
                    dataKey="date"
                    tick={{
                      fontSize: 11,
                      fill: MUTED_INK,
                    }}
                    axisLine={{ stroke: "#d9e5e2" }}
                    tickLine={false}
                  />

                  <YAxis
                    tick={{
                      fontSize: 11,
                      fill: MUTED_INK,
                    }}
                    axisLine={false}
                    tickLine={false}
                    label={{
                      value: "°C",
                      angle: -90,
                      position: "insideLeft",
                      fill: MUTED_INK,
                    }}
                  />

                  <Tooltip
                    contentStyle={{
                      borderRadius: 12,
                      border: "1px solid #d8e6e2",
                      boxShadow: "0 10px 30px rgba(15,55,49,0.12)",
                      fontSize: 12,
                    }}
                    formatter={(value) =>
                      typeof value === "number"
                        ? `${value.toFixed(1)}°C`
                        : value
                    }
                  />

                  <Legend
                    wrapperStyle={{
                      fontSize: 12,
                      paddingTop: 8,
                    }}
                  />

                  <Line
                    type="monotone"
                    dataKey="Max"
                    stroke={CATEGORICAL[1]}
                    strokeWidth={3}
                    dot={{
                      r: 4,
                      strokeWidth: 2,
                    }}
                    activeDot={{
                      r: 6,
                    }}
                  />

                  <Line
                    type="monotone"
                    dataKey="Min"
                    stroke={CATEGORICAL[0]}
                    strokeWidth={3}
                    dot={{
                      r: 4,
                      strokeWidth: 2,
                    }}
                    activeDot={{
                      r: 6,
                    }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </Paper>

            {/* WEATHER SUMMARY */}
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                gap: 1.5,
              }}
            >
              <Paper
                elevation={0}
                sx={{
                  flex: 1,
                  p: 2,
                  borderRadius: 3,
                  border: "1px solid #e1ebe8",
                  bgcolor: "#fffaf4",
                }}
              >
                <Typography
                  sx={{
                    color: "#8b5428",
                    fontSize: "0.72rem",
                    fontWeight: 800,
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                  }}
                >
                  Peak forecast
                </Typography>

                <Typography
                  sx={{
                    mt: 1,
                    fontSize: "1.8rem",
                    fontWeight: 800,
                    color: "#a95f21",
                    letterSpacing: "-0.04em",
                  }}
                >
                  {data.days.length > 0
                    ? `${Math.max(
                        ...data.days.map((d) => d.temp_max_c),
                      ).toFixed(1)}°C`
                    : "—"}
                </Typography>

                <Typography
                  sx={{
                    mt: 0.4,
                    color: MUTED_INK,
                    fontSize: "0.76rem",
                  }}
                >
                  Highest expected air temperature
                </Typography>
              </Paper>

              <Paper
                elevation={0}
                sx={{
                  flex: 1,
                  p: 2,
                  borderRadius: 3,
                  border: "1px solid #e1ebe8",
                  bgcolor: "#f3f8fb",
                }}
              >
                <Typography
                  sx={{
                    color: "#285d75",
                    fontSize: "0.72rem",
                    fontWeight: 800,
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                  }}
                >
                  Forecast window
                </Typography>

                <Typography
                  sx={{
                    mt: 1,
                    fontSize: "1.8rem",
                    fontWeight: 800,
                    color: "#164e63",
                    letterSpacing: "-0.04em",
                  }}
                >
                  {data.days.length}
                </Typography>

                <Typography
                  sx={{
                    mt: 0.4,
                    color: MUTED_INK,
                    fontSize: "0.76rem",
                  }}
                >
                  Days of available forecast data
                </Typography>
              </Paper>
            </Box>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

function TrendsPanel() {
  const { data, isLoading } = useTrends();

  return (
    <Card
      elevation={0}
      sx={{
        borderRadius: 3.5,
        border: "1px solid #dce8e5",
        bgcolor: "#ffffff",
        overflow: "hidden",
      }}
    >
      <Box
        sx={{
          px: { xs: 2, md: 3 },
          py: 2.5,
          background:
            "linear-gradient(135deg, rgba(123,72,32,0.05), rgba(7,66,61,0.02))",
          borderBottom: "1px solid #e5eeec",
        }}
      >
        <Typography
          sx={{
            color: "#0b3b36",
            fontWeight: 800,
            fontSize: "1.15rem",
            letterSpacing: "-0.02em",
          }}
        >
          LST trend
        </Typography>

        <Typography
          sx={{
            color: MUTED_INK,
            fontSize: "0.82rem",
            mt: 0.35,
          }}
        >
          Long-term land surface temperature analysis
        </Typography>
      </Box>

      <CardContent sx={{ p: { xs: 2, md: 3 } }}>
        {isLoading && (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1.5,
              py: 2,
            }}
          >
            <CircularProgress size={24} sx={{ color: "#0b5d50" }} />

            <Typography variant="body2" color="text.secondary">
              Loading historical trend data...
            </Typography>
          </Box>
        )}

        {data && !data.available && (
          <Paper
            elevation={0}
            sx={{
              borderRadius: 3,
              border: "1px solid #e7ddd2",
              bgcolor: "#fffaf5",
              p: { xs: 2, md: 2.5 },
            }}
          >
            <Alert
              severity="info"
              sx={{
                bgcolor: "transparent",
                p: 0,
                "& .MuiAlert-message": {
                  width: "100%",
                },
              }}
            >
              <Typography
                sx={{
                  fontWeight: 700,
                  color: "#5b5149",
                  mb: 0.4,
                }}
              >
                Historical trend unavailable
              </Typography>

              <Typography
                sx={{
                  color: "#756b63",
                  fontSize: "0.85rem",
                }}
              >
                {data.note}
              </Typography>
            </Alert>
          </Paper>
        )}

        {data && data.available && (
          <Box>
            <Divider sx={{ mb: 2 }} />

            <Typography
              variant="body2"
              sx={{
                color: MUTED_INK,
              }}
            >
              Historical LST trend data is available from the analytics
              service.
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
