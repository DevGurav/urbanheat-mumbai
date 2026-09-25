import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Slider,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import PlayArrowRoundedIcon from "@mui/icons-material/PlayArrowRounded";
import SaveRoundedIcon from "@mui/icons-material/SaveRounded";
import DownloadRoundedIcon from "@mui/icons-material/DownloadRounded";
import ParkRoundedIcon from "@mui/icons-material/ParkRounded";
import RoofingRoundedIcon from "@mui/icons-material/RoofingRounded";
import TuneRoundedIcon from "@mui/icons-material/TuneRounded";
import InsightsRoundedIcon from "@mui/icons-material/InsightsRounded";
import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import LocationOnRoundedIcon from "@mui/icons-material/LocationOnRounded";
import { useMemo, useState } from "react";
import type { Feature, Geometry } from "geojson";
import { GeoJSON, MapContainer, TileLayer } from "react-leaflet";

import {
  useCityGrid,
  useDeleteScenario,
  useGenerateReport,
  useHotspots,
  useSaveScenario,
  useSavedScenarios,
  useScenario,
} from "../api/hooks";

import type { Intervention, SavedScenario } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { MUTED_INK, sequentialScale } from "../viz/color";

const MUMBAI_CENTER: [number, number] = [19.076, 72.8777];

interface CellProperties {
  cell_id: number;
  ward_code: string;
}

export function Scenario() {
  const wards = useHotspots(24, "hvi", "ward");
  const grid = useCityGrid("lst");

  const [wardCode, setWardCode] = useState("");
  const [intervention, setIntervention] =
    useState<Intervention>("greening");
  const [coverage, setCoverage] = useState(1.0);

  const scenario = useScenario();

  const { session } = useAuth();
  const accessToken = session?.access_token ?? null;

  const savedScenarios = useSavedScenarios(accessToken);
  const saveScenario = useSaveScenario(accessToken);
  const deleteScenario = useDeleteScenario(accessToken);
  const generateReport = useGenerateReport();

  function handleDownloadReport() {
    if (!wardCode) return;

    generateReport.mutate(
      {
        ward_code: wardCode,
        intervention,
        coverage,
      },
      {
        onSuccess: (pdfBlob) => {
          const url = URL.createObjectURL(pdfBlob);
          const link = document.createElement("a");

          link.href = url;
          link.download = `urbanheat-ward-${wardCode}-report.pdf`;
          link.click();

          URL.revokeObjectURL(url);
        },
      },
    );
  }

  function handleLoad(saved: SavedScenario) {
    setWardCode(saved.ward_code);
    setIntervention(saved.intervention);
    setCoverage(saved.coverage);

    scenario.mutate({
      ward_code: saved.ward_code,
      intervention: saved.intervention,
      coverage: saved.coverage,
    });
  }

  const dlstByCell = useMemo(() => {
    if (!scenario.data) return null;

    return new Map(
      scenario.data.cells.map((c) => [c.cell_id, c.dlst]),
    );
  }, [scenario.data]);

  const overlay = useMemo((): GeoJSON.FeatureCollection | null => {
    if (!dlstByCell || !grid.data) return null;

    const features = grid.data.features.filter((f) =>
      dlstByCell.has(
        (f.properties as CellProperties).cell_id,
      ),
    );

    return {
      type: "FeatureCollection",
      features,
    };
  }, [dlstByCell, grid.data]);

  const colorFor = useMemo(() => {
    if (!scenario.data) return () => MUTED_INK;

    return sequentialScale(
      0,
      scenario.data.best_dlst,
    );
  }, [scenario.data]);

  function handleSubmit() {
    if (!wardCode) return;

    scenario.mutate({
      ward_code: wardCode,
      intervention,
      coverage,
    });
  }

  const interventionLabel =
    intervention === "cool_roof"
      ? "Cool roof"
      : "Urban greening";

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
        {/* =========================================================
            HEADER
        ========================================================= */}
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: {
              xs: "flex-start",
              md: "center",
            },
            gap: 2,
            flexWrap: "wrap",
          }}
        >
          <Box>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                mb: 0.7,
              }}
            >
              <Box
                sx={{
                  width: 40,
                  height: 40,
                  borderRadius: "12px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  bgcolor: "#dff1eb",
                  color: "#0b5d50",
                }}
              >
                <InsightsRoundedIcon />
              </Box>

              <Typography
                sx={{
                  color: "#0b3b36",
                  fontSize: {
                    xs: "1.65rem",
                    md: "2rem",
                  },
                  fontWeight: 800,
                  letterSpacing: "-0.04em",
                  lineHeight: 1.1,
                }}
              >
                Scenario simulator
              </Typography>
            </Box>

            <Typography
              sx={{
                color: MUTED_INK,
                fontSize: "0.92rem",
                maxWidth: 720,
              }}
            >
              Test urban cooling interventions and explore their
              potential impact across Mumbai.
            </Typography>
          </Box>

          <Chip
            icon={<TuneRoundedIcon />}
            label="Climate intervention lab"
            sx={{
              height: 36,
              px: 1,
              borderRadius: 2,
              bgcolor: "#e4f1ee",
              color: "#11604f",
              fontWeight: 700,
              border: "1px solid #c9e3dc",
              "& .MuiChip-icon": {
                color: "#11604f",
              },
            }}
          />
        </Box>

        {/* =========================================================
            CONFIGURATION CARD
        ========================================================= */}
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
                "linear-gradient(135deg, rgba(7,66,61,0.07), rgba(31,117,102,0.02))",
              borderBottom: "1px solid #e5eeec",
            }}
          >
            <Typography
              sx={{
                color: "#0b3b36",
                fontWeight: 800,
                fontSize: "1.1rem",
                letterSpacing: "-0.02em",
              }}
            >
              Build a cooling scenario
            </Typography>

            <Typography
              sx={{
                mt: 0.35,
                color: MUTED_INK,
                fontSize: "0.82rem",
              }}
            >
              Select a ward and intervention, then simulate the
              expected change in land surface temperature.
            </Typography>
          </Box>

          <CardContent
            sx={{
              p: { xs: 2, md: 3 },
            }}
          >
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  xs: "1fr",
                  md: "1.1fr 1.35fr 1fr",
                },
                gap: 2.5,
                alignItems: "stretch",
              }}
            >
              {/* WARD */}
              <Paper
                elevation={0}
                sx={{
                  p: 2,
                  borderRadius: 3,
                  border: "1px solid #e0ebe8",
                  bgcolor: "#fbfdfc",
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1,
                    mb: 1.4,
                  }}
                >
                  <LocationOnRoundedIcon
                    sx={{
                      color: "#0b5d50",
                      fontSize: 20,
                    }}
                  />

                  <Typography
                    sx={{
                      fontWeight: 750,
                      color: "#284d47",
                      fontSize: "0.88rem",
                    }}
                  >
                    Target ward
                  </Typography>
                </Box>

                <FormControl
                  size="small"
                  fullWidth
                >
                  <InputLabel id="scenario-ward-label">
                    Ward
                  </InputLabel>

                  <Select
                    labelId="scenario-ward-label"
                    label="Ward"
                    value={wardCode}
                    onChange={(e) =>
                      setWardCode(e.target.value)
                    }
                    sx={{
                      borderRadius: 2,
                      bgcolor: "#ffffff",
                    }}
                  >
                    {(wards.data?.results ?? []).map(
                      (w) => (
                        <MenuItem
                          key={w.id}
                          value={w.id}
                        >
                          {w.id}
                        </MenuItem>
                      ),
                    )}
                  </Select>
                </FormControl>

                <Typography
                  sx={{
                    mt: 1,
                    color: MUTED_INK,
                    fontSize: "0.72rem",
                  }}
                >
                  Choose one of the available Mumbai wards.
                </Typography>
              </Paper>

              {/* INTERVENTION */}
              <Paper
                elevation={0}
                sx={{
                  p: 2,
                  borderRadius: 3,
                  border: "1px solid #e0ebe8",
                  bgcolor: "#fbfdfc",
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1,
                    mb: 1.4,
                  }}
                >
                  {intervention === "greening" ? (
                    <ParkRoundedIcon
                      sx={{
                        color: "#23805f",
                        fontSize: 20,
                      }}
                    />
                  ) : (
                    <RoofingRoundedIcon
                      sx={{
                        color: "#28627a",
                        fontSize: 20,
                      }}
                    />
                  )}

                  <Typography
                    sx={{
                      fontWeight: 750,
                      color: "#284d47",
                      fontSize: "0.88rem",
                    }}
                  >
                    Cooling intervention
                  </Typography>
                </Box>

                <ToggleButtonGroup
                  value={intervention}
                  exclusive
                  fullWidth
                  size="small"
                  onChange={(
                    _,
                    value: Intervention | null,
                  ) =>
                    value &&
                    setIntervention(value)
                  }
                  sx={{
                    "& .MuiToggleButton-root": {
                      flex: 1,
                      py: 1,
                      textTransform: "none",
                      fontWeight: 700,
                      color: "#54716b",
                      borderColor: "#d5e3df",
                    },
                    "& .Mui-selected": {
                      bgcolor:
                        "#0b5d50 !important",
                      color:
                        "#ffffff !important",
                    },
                  }}
                >
                  <ToggleButton value="greening">
                    Greening
                  </ToggleButton>

                  <ToggleButton value="cool_roof">
                    Cool roof
                  </ToggleButton>
                </ToggleButtonGroup>

                <Typography
                  sx={{
                    mt: 1,
                    color: MUTED_INK,
                    fontSize: "0.72rem",
                  }}
                >
                  {intervention ===
                  "greening"
                    ? "Increase vegetation to model urban cooling."
                    : "Model reflective cool-roof deployment."}
                </Typography>
              </Paper>

              {/* COVERAGE */}
              <Paper
                elevation={0}
                sx={{
                  p: 2,
                  borderRadius: 3,
                  border: "1px solid #e0ebe8",
                  bgcolor:
                    intervention === "cool_roof"
                      ? "#f5fafc"
                      : "#f8faf9",
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 1,
                    mb: 1,
                  }}
                >
                  <Typography
                    sx={{
                      fontWeight: 750,
                      color: "#284d47",
                      fontSize: "0.88rem",
                    }}
                  >
                    Intervention coverage
                  </Typography>

                  <Chip
                    size="small"
                    label={
                      intervention ===
                      "cool_roof"
                        ? `${Math.round(
                            coverage * 100,
                          )}%`
                        : "Fixed target"
                    }
                    sx={{
                      height: 25,
                      bgcolor:
                        intervention ===
                        "cool_roof"
                          ? "#dceff5"
                          : "#e9f0ed",
                      color:
                        intervention ===
                        "cool_roof"
                          ? "#205e75"
                          : "#58716b",
                      fontWeight: 800,
                    }}
                  />
                </Box>

                <Slider
                  value={coverage}
                  onChange={(_, value) =>
                    setCoverage(
                      value as number,
                    )
                  }
                  min={0}
                  max={1}
                  step={0.1}
                  disabled={
                    intervention ===
                    "greening"
                  }
                  sx={{
                    color:
                      intervention ===
                      "cool_roof"
                        ? "#28627a"
                        : "#0b5d50",
                    mt: 1,
                  }}
                />

                <Box
                  sx={{
                    display: "flex",
                    justifyContent:
                      "space-between",
                    color: MUTED_INK,
                    fontSize: "0.68rem",
                  }}
                >
                  <span>0%</span>
                  <span>50%</span>
                  <span>100%</span>
                </Box>

                {intervention ===
                  "greening" && (
                  <Typography
                    sx={{
                      mt: 1,
                      color: MUTED_INK,
                      fontSize: "0.7rem",
                      lineHeight: 1.45,
                    }}
                  >
                    Coverage is ignored for
                    greening. The model raises
                    NDVI to its fixed target.
                  </Typography>
                )}
              </Paper>
            </Box>

            {/* ACTIONS */}
            <Box
              sx={{
                display: "flex",
                gap: 1.2,
                flexWrap: "wrap",
                mt: 2.5,
              }}
            >
              <Button
                variant="contained"
                startIcon={
                  <PlayArrowRoundedIcon />
                }
                onClick={handleSubmit}
                disabled={
                  !wardCode ||
                  scenario.isPending
                }
                sx={{
                  px: 2.5,
                  py: 1.15,
                  borderRadius: 2,
                  textTransform: "none",
                  fontWeight: 800,
                  bgcolor: "#0b5d50",
                  boxShadow:
                    "0 8px 20px rgba(11,93,80,0.18)",
                  "&:hover": {
                    bgcolor: "#084c42",
                    boxShadow:
                      "0 10px 24px rgba(11,93,80,0.24)",
                  },
                }}
              >
                {scenario.isPending
                  ? "Simulating…"
                  : "Run simulation"}
              </Button>

              {accessToken && (
                <Button
                  variant="outlined"
                  startIcon={
                    <SaveRoundedIcon />
                  }
                  onClick={() =>
                    saveScenario.mutate({
                      ward_code:
                        wardCode,
                      intervention,
                      coverage,
                    })
                  }
                  disabled={
                    !wardCode ||
                    saveScenario.isPending
                  }
                  sx={{
                    px: 2.2,
                    py: 1.1,
                    borderRadius: 2,
                    textTransform: "none",
                    fontWeight: 750,
                    borderColor: "#bcd5cf",
                    color: "#0b5d50",
                  }}
                >
                  {saveScenario.isPending
                    ? "Saving…"
                    : "Save scenario"}
                </Button>
              )}

              <Button
                variant="outlined"
                startIcon={
                  <DownloadRoundedIcon />
                }
                onClick={
                  handleDownloadReport
                }
                disabled={
                  !wardCode ||
                  generateReport.isPending
                }
                sx={{
                  px: 2.2,
                  py: 1.1,
                  borderRadius: 2,
                  textTransform: "none",
                  fontWeight: 750,
                  borderColor: "#c5d7df",
                  color: "#285d75",
                }}
              >
                {generateReport.isPending
                  ? "Generating…"
                  : "Download report"}
              </Button>
            </Box>
          </CardContent>
        </Card>

        {/* =========================================================
            REPORT ERROR
        ========================================================= */}
        {generateReport.isError && (
          <Alert
            severity="error"
            sx={{
              borderRadius: 2.5,
            }}
          >
            Couldn't generate the report —{" "}
            {generateReport.error instanceof
            Error
              ? generateReport.error.message
              : "is the backend running?"}
          </Alert>
        )}

        {/* =========================================================
            SAVED SCENARIOS
        ========================================================= */}
        {accessToken &&
          (savedScenarios.data
            ?.scenarios.length ?? 0) > 0 && (
            <Card
              elevation={0}
              sx={{
                borderRadius: 3.5,
                border:
                  "1px solid #dce8e5",
                bgcolor: "#ffffff",
              }}
            >
              <CardContent
                sx={{
                  p: {
                    xs: 2,
                    md: 2.5,
                  },
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    alignItems:
                      "center",
                    justifyContent:
                      "space-between",
                    gap: 2,
                    flexWrap:
                      "wrap",
                    mb: 1.5,
                  }}
                >
                  <Box>
                    <Typography
                      sx={{
                        fontWeight: 800,
                        color: "#244b45",
                        fontSize:
                          "0.98rem",
                      }}
                    >
                      Saved scenarios
                    </Typography>

                    <Typography
                      sx={{
                        color:
                          MUTED_INK,
                        fontSize:
                          "0.76rem",
                        mt: 0.25,
                      }}
                    >
                      Load a previous
                      intervention
                      configuration.
                    </Typography>
                  </Box>

                  <Chip
                    size="small"
                    label={`${savedScenarios.data?.scenarios.length ?? 0} saved`}
                    sx={{
                      bgcolor:
                        "#eaf2ef",
                      color:
                        "#507069",
                      fontWeight: 700,
                    }}
                  />
                </Box>

                <Box
                  sx={{
                    display: "flex",
                    flexWrap:
                      "wrap",
                    gap: 1,
                  }}
                >
                  {savedScenarios.data?.scenarios.map(
                    (s) => (
                      <Chip
                        key={s.id}
                        label={`${s.ward_code} · ${
                          s.intervention ===
                          "cool_roof"
                            ? "Cool roof"
                            : "Greening"
                        }${
                          s.intervention ===
                          "cool_roof"
                            ? ` (${Math.round(
                                s.coverage *
                                  100,
                              )}%)`
                            : ""
                        }`}
                        onClick={() =>
                          handleLoad(
                            s,
                          )
                        }
                        onDelete={() =>
                          deleteScenario.mutate(
                            s.id,
                          )
                        }
                        deleteIcon={
                          <DeleteIcon
                            fontSize="small"
                            aria-label="Delete"
                          />
                        }
                        variant="outlined"
                        sx={{
                          height: 34,
                          borderRadius: 2,
                          borderColor:
                            "#cfe0db",
                          color:
                            "#315850",
                          fontWeight: 650,
                          bgcolor:
                            "#fbfdfc",
                          "&:hover":
                            {
                              bgcolor:
                                "#eef7f3",
                            },
                        }}
                      />
                    ),
                  )}
                </Box>
              </CardContent>
            </Card>
          )}

        {/* =========================================================
            SIMULATION ERROR
        ========================================================= */}
        {scenario.isError && (
          <Alert
            severity="error"
            sx={{
              borderRadius: 2.5,
            }}
          >
            Couldn't run the scenario — is
            the backend running?
          </Alert>
        )}

        {/* =========================================================
            RESULTS
        ========================================================= */}
        {scenario.data && (
          <>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  xs: "1fr",
                  sm: "repeat(3, 1fr)",
                },
                gap: 2,
              }}
            >
              {/* CELLS */}
              <Paper
                elevation={0}
                sx={{
                  p: 2.2,
                  borderRadius: 3,
                  border:
                    "1px solid #dce8e5",
                  bgcolor: "#ffffff",
                  position:
                    "relative",
                  overflow:
                    "hidden",
                }}
              >
                <Box
                  sx={{
                    position:
                      "absolute",
                    width: 90,
                    height: 90,
                    borderRadius:
                      "50%",
                    bgcolor:
                      "rgba(11,93,80,0.07)",
                    right: -35,
                    top: -35,
                  }}
                />

                <Typography
                  sx={{
                    color:
                      MUTED_INK,
                    fontSize:
                      "0.7rem",
                    fontWeight: 800,
                    textTransform:
                      "uppercase",
                    letterSpacing:
                      "0.06em",
                  }}
                >
                  Cells analysed
                </Typography>

                <Typography
                  sx={{
                    mt: 0.8,
                    fontSize:
                      "1.9rem",
                    fontWeight: 850,
                    color:
                      "#0b5d50",
                    letterSpacing:
                      "-0.05em",
                  }}
                >
                  {scenario.data.n_cells.toLocaleString()}
                </Typography>

                <Typography
                  sx={{
                    color:
                      MUTED_INK,
                    fontSize:
                      "0.74rem",
                  }}
                >
                  Spatial cells in selected ward
                </Typography>
              </Paper>

              {/* MEAN */}
              <Paper
                elevation={0}
                sx={{
                  p: 2.2,
                  borderRadius: 3,
                  border:
                    "1px solid #dce8e5",
                  bgcolor: "#ffffff",
                  position:
                    "relative",
                  overflow:
                    "hidden",
                }}
              >
                <Box
                  sx={{
                    position:
                      "absolute",
                    width: 90,
                    height: 90,
                    borderRadius:
                      "50%",
                    bgcolor:
                      "rgba(40,98,122,0.07)",
                    right: -35,
                    top: -35,
                  }}
                />

                <Typography
                  sx={{
                    color:
                      MUTED_INK,
                    fontSize:
                      "0.7rem",
                    fontWeight: 800,
                    textTransform:
                      "uppercase",
                    letterSpacing:
                      "0.06em",
                  }}
                >
                  Mean ΔLST
                </Typography>

                <Typography
                  sx={{
                    mt: 0.8,
                    fontSize:
                      "1.9rem",
                    fontWeight: 850,
                    color:
                      "#285d75",
                    letterSpacing:
                      "-0.05em",
                  }}
                >
                  {scenario.data.mean_dlst.toFixed(
                    2,
                  )}
                  °C
                </Typography>

                <Typography
                  sx={{
                    color:
                      MUTED_INK,
                    fontSize:
                      "0.74rem",
                  }}
                >
                  Average modelled cooling
                </Typography>
              </Paper>

              {/* BEST */}
              <Paper
                elevation={0}
                sx={{
                  p: 2.2,
                  borderRadius: 3,
                  border:
                    "1px solid #dce8e5",
                  bgcolor: "#ffffff",
                  position:
                    "relative",
                  overflow:
                    "hidden",
                }}
              >
                <Box
                  sx={{
                    position:
                      "absolute",
                    width: 90,
                    height: 90,
                    borderRadius:
                      "50%",
                    bgcolor:
                      "rgba(35,128,95,0.08)",
                    right: -35,
                    top: -35,
                  }}
                />

                <Typography
                  sx={{
                    color:
                      MUTED_INK,
                    fontSize:
                      "0.7rem",
                    fontWeight: 800,
                    textTransform:
                      "uppercase",
                    letterSpacing:
                      "0.06em",
                  }}
                >
                  Maximum cooling
                </Typography>

                <Typography
                  sx={{
                    mt: 0.8,
                    fontSize:
                      "1.9rem",
                    fontWeight: 850,
                    color:
                      "#23805f",
                    letterSpacing:
                      "-0.05em",
                  }}
                >
                  {scenario.data.best_dlst.toFixed(
                    2,
                  )}
                  °C
                </Typography>

                <Typography
                  sx={{
                    color:
                      MUTED_INK,
                    fontSize:
                      "0.74rem",
                  }}
                >
                  Strongest modelled cell response
                </Typography>
              </Paper>
            </Box>

            {/* CLAMP WARNING */}
            {scenario.data.clamped && (
              <Alert
                severity="warning"
                icon={
                  <WarningAmberRoundedIcon />
                }
                sx={{
                  borderRadius: 3,
                  border:
                    "1px solid #ead9bb",
                  bgcolor: "#fffaf2",
                  alignItems:
                    "flex-start",
                }}
              >
                <Typography
                  sx={{
                    fontWeight: 800,
                    mb: 0.35,
                  }}
                >
                  Model envelope warning
                </Typography>

                <Typography
                  variant="body2"
                >
                  {scenario.data.clamped_cells}{" "}
                  of{" "}
                  {scenario.data.n_cells}{" "}
                  cells were clamped to
                  the training envelope —
                  those cells' ΔLST is capped,
                  not extrapolated.
                </Typography>
              </Alert>
            )}

            {/* CAVEAT */}
            <Alert
              severity="info"
              icon={
                <InfoOutlinedIcon />
              }
              sx={{
                borderRadius: 3,
                border:
                  "1px solid #cbdfe7",
                bgcolor: "#f4f9fb",
              }}
            >
              {scenario.data.caveat}
            </Alert>

            {/* =====================================================
                MAP RESULT
            ===================================================== */}
            <Card
              elevation={0}
              sx={{
                borderRadius: 3.5,
                border:
                  "1px solid #dce8e5",
                bgcolor: "#ffffff",
                overflow:
                  "hidden",
              }}
            >
              <Box
                sx={{
                  px: {
                    xs: 2,
                    md: 3,
                  },
                  py: 2.3,
                  display: "flex",
                  justifyContent:
                    "space-between",
                  alignItems:
                    "center",
                  gap: 2,
                  flexWrap:
                    "wrap",
                  background:
                    "linear-gradient(135deg, rgba(11,93,80,0.07), rgba(40,98,122,0.03))",
                  borderBottom:
                    "1px solid #e5eeec",
                }}
              >
                <Box>
                  <Typography
                    sx={{
                      fontWeight: 800,
                      color:
                        "#0b3b36",
                      fontSize:
                        "1.12rem",
                    }}
                  >
                    Cooling impact map
                  </Typography>

                  <Typography
                    sx={{
                      color:
                        MUTED_INK,
                      fontSize:
                        "0.8rem",
                      mt: 0.3,
                    }}
                  >
                    {wardCode} ·{" "}
                    {interventionLabel}
                    {intervention ===
                    "cool_roof"
                      ? ` · ${Math.round(
                          coverage * 100,
                        )}% coverage`
                      : ""}
                  </Typography>
                </Box>

                <Chip
                  label="ΔLST"
                  sx={{
                    bgcolor:
                      "#dff1eb",
                    color:
                      "#0b5d50",
                    fontWeight: 800,
                  }}
                />
              </Box>

              <CardContent
                sx={{
                  p: {
                    xs: 1.5,
                    md: 2.5,
                  },
                }}
              >
                <Box
                  sx={{
                    height: {
                      xs: 390,
                      md: 510,
                    },
                    width: "100%",
                    borderRadius: 3,
                    overflow:
                      "hidden",
                    border:
                      "1px solid #dce8e5",
                    position:
                      "relative",
                  }}
                >
                  <MapContainer
                    center={
                      MUMBAI_CENTER
                    }
                    zoom={12}
                    preferCanvas
                    style={{
                      height: "100%",
                      width: "100%",
                    }}
                  >
                    <TileLayer
                      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />

                    {overlay &&
                      overlay.features
                        .length >
                        0 && (
                        <GeoJSON
                          key={`${wardCode}-${intervention}-${coverage}`}
                          data={overlay}
                          style={(
                            feature,
                          ) => {
                            const cellId =
                              (
                                feature?.properties as CellProperties | undefined
                              )?.cell_id;

                            const dlst =
                              cellId !==
                              undefined
                                ? (dlstByCell?.get(
                                    cellId,
                                  ) ??
                                  0)
                                : 0;

                            return {
                              fillColor:
                                colorFor(
                                  dlst,
                                ),
                              fillOpacity:
                                0.86,
                              color:
                                "#ffffff",
                              weight: 0.45,
                            };
                          }}
                          onEachFeature={(
                            feature: Feature<
                              Geometry,
                              CellProperties
                            >,
                            layerInstance,
                          ) => {
                            const dlst =
                              dlstByCell?.get(
                                feature
                                  .properties
                                  .cell_id,
                              ) ?? 0;

                            layerInstance.bindTooltip(
                              `Cell ${feature.properties.cell_id}: ${dlst.toFixed(
                                2,
                              )}°C`,
                              {
                                sticky:
                                  true,
                              },
                            );
                          }}
                        />
                      )}
                  </MapContainer>

                  {/* MAP OVERLAY */}
                  <Paper
                    elevation={0}
                    sx={{
                      position:
                        "absolute",
                      left: 16,
                      bottom: 16,
                      zIndex: 1000,
                      p: 1.5,
                      minWidth: 175,
                      borderRadius: 2.5,
                      bgcolor:
                        "rgba(255,255,255,0.94)",
                      backdropFilter:
                        "blur(10px)",
                      border:
                        "1px solid rgba(210,225,220,0.9)",
                      boxShadow:
                        "0 8px 25px rgba(20,60,52,0.12)",
                    }}
                  >
                    <Typography
                      sx={{
                        fontSize:
                          "0.72rem",
                        fontWeight: 800,
                        color:
                          "#315850",
                        mb: 1,
                      }}
                    >
                      Cooling intensity
                    </Typography>

                    <Box
                      sx={{
                        height: 10,
                        borderRadius: 10,
                        background:
                          "linear-gradient(90deg, #eaf5f1, #b7ddd0, #76bda7, #3b8f78, #0b5d50)",
                      }}
                    />

                    <Box
                      sx={{
                        display:
                          "flex",
                        justifyContent:
                          "space-between",
                        mt: 0.6,
                      }}
                    >
                      <Typography
                        sx={{
                          fontSize:
                            "0.65rem",
                          color:
                            MUTED_INK,
                        }}
                      >
                        Low
                      </Typography>

                      <Typography
                        sx={{
                          fontSize:
                            "0.65rem",
                          color:
                            MUTED_INK,
                        }}
                      >
                        High
                      </Typography>
                    </Box>
                  </Paper>
                </Box>
              </CardContent>
            </Card>
          </>
        )}

        {/* GRID LOADING */}
        {grid.isLoading && (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 1,
              py: 1,
            }}
          >
            <CircularProgress
              size={16}
              sx={{
                color: "#0b5d50",
              }}
            />

            <Typography
              sx={{
                fontSize:
                  "0.75rem",
                color: MUTED_INK,
              }}
            >
              Loading map geometry...
            </Typography>
          </Box>
        )}

        {/* FOOTER NOTE */}
        {!scenario.data &&
          !scenario.isPending && (
            <Paper
              elevation={0}
              sx={{
                p: 3,
                borderRadius: 3,
                border:
                  "1px dashed #cbdcd8",
                bgcolor:
                  "rgba(255,255,255,0.65)",
                textAlign:
                  "center",
              }}
            >
              <InsightsRoundedIcon
                sx={{
                  fontSize: 34,
                  color: "#a5c4bc",
                  mb: 1,
                }}
              />

              <Typography
                sx={{
                  fontWeight: 750,
                  color: "#45645d",
                }}
              >
                Configure a scenario to begin
              </Typography>

              <Typography
                sx={{
                  mt: 0.5,
                  color: MUTED_INK,
                  fontSize:
                    "0.8rem",
                }}
              >
                Select a ward and cooling
                intervention above, then run
                the simulation.
              </Typography>
            </Paper>
          )}
      </Box>
    </Box>
  );
}
