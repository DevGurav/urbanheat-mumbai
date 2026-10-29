import { useMemo, useState } from "react";
import {
  Box,
  Button,
  Chip,
  Divider,
  IconButton,
  Paper,
  Typography,
} from "@mui/material";

import { useAlerts } from "../api/hooks";
import type { AlertPayload } from "../api/types";

import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import ErrorOutlineRoundedIcon from "@mui/icons-material/ErrorOutlineRounded";
import CheckCircleOutlineRoundedIcon from "@mui/icons-material/CheckCircleOutlineRounded";
import NotificationsActiveRoundedIcon from "@mui/icons-material/NotificationsActiveRounded";
import ThermostatRoundedIcon from "@mui/icons-material/ThermostatRounded";
import LocationOnOutlinedIcon from "@mui/icons-material/LocationOnOutlined";
import AccessTimeRoundedIcon from "@mui/icons-material/AccessTimeRounded";
import MoreHorizRoundedIcon from "@mui/icons-material/MoreHorizRounded";

type AlertSeverity = "High" | "Medium" | "Low";

type AlertItem = {
  id: string;
  title: string;
  location: string;
  temperature: string;
  severity: AlertSeverity;
  time: string;
  description: string;
  acknowledged: boolean;
};

/** The real Monitoring feed (GET /alerts, agents.md §7) mapped onto this page's card shape.
 * The backend's three levels are IMD-style absolute thresholds: advisory, heat wave, severe
 * heat wave. Nothing here is invented — an empty feed renders as an empty state. */
const SEVERITY_LABEL: Record<AlertPayload["severity"], AlertSeverity> = {
  advisory: "Low",
  heat_wave: "Medium",
  severe_heat_wave: "High",
};

const SEVERITY_TITLE: Record<AlertPayload["severity"], string> = {
  advisory: "Heat advisory",
  heat_wave: "Heat wave",
  severe_heat_wave: "Severe heat wave",
};

function toAlertItem(alert: AlertPayload): AlertItem {
  return {
    id: `${alert.date}-${alert.severity}`,
    title: SEVERITY_TITLE[alert.severity],
    location: alert.wards_affected.length
      ? `Wards ${alert.wards_affected.join(", ")}`
      : "Citywide",
    temperature: `${alert.forecast_max_c.toFixed(1)}°C forecast max`,
    severity: SEVERITY_LABEL[alert.severity],
    time: alert.date,
    description: alert.summary,
    acknowledged: false,
  };
}

function severityStyles(severity: AlertSeverity) {
  if (severity === "High") {
    return {
      color: "#d32f2f",
      background: "#fff1f1",
      border: "#ffcdd2",
    };
  }

  if (severity === "Medium") {
    return {
      color: "#ed6c02",
      background: "#fff7ed",
      border: "#ffe0b2",
    };
  }

  return {
    color: "#2e7d32",
    background: "#f1f8f3",
    border: "#c8e6c9",
  };
}

export function Alerts() {
  const { data, isLoading, isError } = useAlerts(50);
  // Acknowledging is a per-browser view state — the backend has no acknowledge endpoint.
  const [acknowledgedIds, setAcknowledgedIds] = useState<ReadonlySet<string>>(new Set());

  const alerts = useMemo(
    () =>
      (data?.alerts ?? []).map((a) => {
        const item = toAlertItem(a);
        return { ...item, acknowledged: acknowledgedIds.has(item.id) };
      }),
    [data, acknowledgedIds]
  );

  const activeAlerts = alerts.filter((alert) => !alert.acknowledged).length;

  const highAlerts = alerts.filter(
    (alert) => alert.severity === "High" && !alert.acknowledged
  ).length;

  const acknowledgedAlerts = alerts.filter((alert) => alert.acknowledged).length;

  const acknowledgeAlert = (id: string) => {
    setAcknowledgedIds((current) => new Set(current).add(id));
  };

  return (
    <Box
      sx={{
        minHeight: "100%",
        p: {
          xs: 2,
          md: 3,
          lg: 4,
        },
      }}
    >
      {/* ================= PAGE HEADER ================= */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: {
            xs: "flex-start",
            md: "center",
          },
          flexDirection: {
            xs: "column",
            md: "row",
          },
          gap: 2,
          mb: 3,
        }}
      >
        <Box>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1.2,
              mb: 0.7,
            }}
          >
            <Box
              sx={{
                width: 42,
                height: 42,
                borderRadius: "12px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                backgroundColor: "#eaf3ff",
                color: "#1976d2",
              }}
            >
              <NotificationsActiveRoundedIcon />
            </Box>

            <Typography
              sx={{
                fontSize: {
                  xs: 24,
                  md: 28,
                },
                fontWeight: 800,
                color: "#172033",
                letterSpacing: "-0.5px",
              }}
            >
              Heat alerts
            </Typography>
          </Box>

          <Typography
            sx={{
              color: "#697386",
              fontSize: 14,
              maxWidth: 650,
            }}
          >
            Monitor abnormal heat conditions and review alerts generated by
            the UrbanHeat intelligence system.
          </Typography>
        </Box>

        <Chip
          icon={<CheckCircleOutlineRoundedIcon />}
          label="Monitoring active"
          sx={{
            height: 34,
            borderRadius: "9px",
            fontWeight: 700,
            color: "#2e7d32",
            backgroundColor: "#eef8f1",
            border: "1px solid #c8e6c9",
          }}
        />
      </Box>

      {/* ================= SUMMARY ================= */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            sm: "repeat(3, 1fr)",
          },
          gap: 2,
          mb: 3,
        }}
      >
        {/* ACTIVE */}
        <Paper
          elevation={0}
          sx={{
            p: 2.2,
            borderRadius: "15px",
            border: "1px solid #e5e9f0",
            backgroundColor: "#ffffff",
          }}
        >
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
            }}
          >
            <Box>
              <Typography
                sx={{
                  fontSize: 12,
                  color: "#7b8494",
                  fontWeight: 600,
                  mb: 0.6,
                }}
              >
                ACTIVE ALERTS
              </Typography>

              <Typography
                sx={{
                  fontSize: 28,
                  fontWeight: 800,
                  color: "#172033",
                }}
              >
                {activeAlerts}
              </Typography>
            </Box>

            <Box
              sx={{
                width: 38,
                height: 38,
                borderRadius: "10px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#1976d2",
                backgroundColor: "#eaf3ff",
              }}
            >
              <NotificationsActiveRoundedIcon />
            </Box>
          </Box>
        </Paper>

        {/* HIGH PRIORITY */}
        <Paper
          elevation={0}
          sx={{
            p: 2.2,
            borderRadius: "15px",
            border: "1px solid #e5e9f0",
            backgroundColor: "#ffffff",
          }}
        >
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
            }}
          >
            <Box>
              <Typography
                sx={{
                  fontSize: 12,
                  color: "#7b8494",
                  fontWeight: 600,
                  mb: 0.6,
                }}
              >
                HIGH PRIORITY
              </Typography>

              <Typography
                sx={{
                  fontSize: 28,
                  fontWeight: 800,
                  color: "#d32f2f",
                }}
              >
                {highAlerts}
              </Typography>
            </Box>

            <Box
              sx={{
                width: 38,
                height: 38,
                borderRadius: "10px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#d32f2f",
                backgroundColor: "#fff1f1",
              }}
            >
              <ErrorOutlineRoundedIcon />
            </Box>
          </Box>
        </Paper>

        {/* ACKNOWLEDGED */}
        <Paper
          elevation={0}
          sx={{
            p: 2.2,
            borderRadius: "15px",
            border: "1px solid #e5e9f0",
            backgroundColor: "#ffffff",
          }}
        >
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
            }}
          >
            <Box>
              <Typography
                sx={{
                  fontSize: 12,
                  color: "#7b8494",
                  fontWeight: 600,
                  mb: 0.6,
                }}
              >
                ACKNOWLEDGED
              </Typography>

              <Typography
                sx={{
                  fontSize: 28,
                  fontWeight: 800,
                  color: "#172033",
                }}
              >
                {acknowledgedAlerts}
              </Typography>
            </Box>

            <Box
              sx={{
                width: 38,
                height: 38,
                borderRadius: "10px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#2e7d32",
                backgroundColor: "#eef8f1",
              }}
            >
              <CheckCircleOutlineRoundedIcon />
            </Box>
          </Box>
        </Paper>
      </Box>

      {/* ================= ALERT LIST ================= */}
      <Paper
        elevation={0}
        sx={{
          borderRadius: "16px",
          border: "1px solid #e5e9f0",
          backgroundColor: "#ffffff",
          overflow: "hidden",
        }}
      >
        {/* HEADER */}
        <Box
          sx={{
            px: {
              xs: 2,
              md: 2.5,
            },
            py: 2,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <Box>
            <Typography
              sx={{
                fontSize: 16,
                fontWeight: 800,
                color: "#172033",
              }}
            >
              Recent alerts
            </Typography>

            <Typography
              sx={{
                fontSize: 12,
                color: "#8993a3",
                mt: 0.3,
              }}
            >
              Latest heat events detected across monitored areas
            </Typography>
          </Box>

          <IconButton
            size="small"
            sx={{
              color: "#697386",
              border: "1px solid #e5e9f0",
              borderRadius: "8px",
            }}
          >
            <MoreHorizRoundedIcon fontSize="small" />
          </IconButton>
        </Box>

        <Divider />

        {/* STATES */}
        {(isLoading || isError || alerts.length === 0) && (
          <Box sx={{ p: 3 }}>
            <Typography sx={{ fontSize: 14, fontWeight: 700, color: "#172033", mb: 0.5 }}>
              {isLoading
                ? "Loading alerts…"
                : isError
                  ? "Couldn't load alerts"
                  : "No heat alerts"}
            </Typography>
            <Typography sx={{ fontSize: 13, color: "#697386" }}>
              {isLoading
                ? "Fetching the latest monitoring results."
                : isError
                  ? "The alerts service didn't respond. It may be waking up, so try again in a minute."
                  : "The monitor checks the forecast every morning at 06:00 IST and logs an alert only when the forecast maximum reaches 37 °C or more."}
            </Typography>
          </Box>
        )}

        {/* ALERTS */}
        {alerts.map((alert, index) => {
          const styles = severityStyles(alert.severity);

          return (
            <Box key={alert.id}>
              <Box
                sx={{
                  p: {
                    xs: 2,
                    md: 2.5,
                  },
                  display: "flex",
                  gap: 2,
                  flexDirection: {
                    xs: "column",
                    md: "row",
                  },
                  opacity: alert.acknowledged ? 0.65 : 1,
                }}
              >
                {/* ICON */}
                <Box
                  sx={{
                    width: 44,
                    height: 44,
                    borderRadius: "12px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    color: styles.color,
                    backgroundColor: styles.background,
                  }}
                >
                  {alert.severity === "High" ? (
                    <ErrorOutlineRoundedIcon />
                  ) : (
                    <WarningAmberRoundedIcon />
                  )}
                </Box>

                {/* CONTENT */}
                <Box
                  sx={{
                    flex: 1,
                    minWidth: 0,
                  }}
                >
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: {
                        xs: "flex-start",
                        sm: "center",
                      },
                      flexDirection: {
                        xs: "column",
                        sm: "row",
                      },
                      gap: 1,
                      mb: 0.7,
                    }}
                  >
                    <Typography
                      sx={{
                        fontSize: 14,
                        fontWeight: 800,
                        color: "#172033",
                      }}
                    >
                      {alert.title}
                    </Typography>

                    <Chip
                      label={alert.severity}
                      size="small"
                      sx={{
                        height: 23,
                        fontSize: 10.5,
                        fontWeight: 800,
                        color: styles.color,
                        backgroundColor: styles.background,
                        border: `1px solid ${styles.border}`,
                      }}
                    />

                    {alert.acknowledged && (
                      <Chip
                        label="Acknowledged"
                        size="small"
                        sx={{
                          height: 23,
                          fontSize: 10.5,
                          fontWeight: 700,
                          color: "#2e7d32",
                          backgroundColor: "#eef8f1",
                        }}
                      />
                    )}
                  </Box>

                  <Typography
                    sx={{
                      fontSize: 13,
                      color: "#697386",
                      mb: 1.2,
                      lineHeight: 1.5,
                    }}
                  >
                    {alert.description}
                  </Typography>

                  <Box
                    sx={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: 2,
                    }}
                  >
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 0.6,
                      }}
                    >
                      <LocationOnOutlinedIcon
                        sx={{
                          fontSize: 16,
                          color: "#8993a3",
                        }}
                      />

                      <Typography
                        sx={{
                          fontSize: 11.5,
                          color: "#697386",
                          fontWeight: 600,
                        }}
                      >
                        {alert.location}
                      </Typography>
                    </Box>

                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 0.6,
                      }}
                    >
                      <ThermostatRoundedIcon
                        sx={{
                          fontSize: 16,
                          color: styles.color,
                        }}
                      />

                      <Typography
                        sx={{
                          fontSize: 11.5,
                          color: "#697386",
                          fontWeight: 700,
                        }}
                      >
                        {alert.temperature}
                      </Typography>
                    </Box>

                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 0.6,
                      }}
                    >
                      <AccessTimeRoundedIcon
                        sx={{
                          fontSize: 15,
                          color: "#8993a3",
                        }}
                      />

                      <Typography
                        sx={{
                          fontSize: 11.5,
                          color: "#8993a3",
                        }}
                      >
                        {alert.time}
                      </Typography>
                    </Box>
                  </Box>
                </Box>

                {/* ACTION */}
                <Box
                  sx={{
                    display: "flex",
                    alignItems: {
                      xs: "flex-start",
                      md: "center",
                    },
                    flexShrink: 0,
                  }}
                >
                  {!alert.acknowledged && (
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => acknowledgeAlert(alert.id)}
                      startIcon={<CheckCircleOutlineRoundedIcon />}
                      sx={{
                        textTransform: "none",
                        borderRadius: "9px",
                        fontSize: 11.5,
                        fontWeight: 700,
                        borderColor: "#d9dee7",
                        color: "#596579",
                        whiteSpace: "nowrap",

                        "&:hover": {
                          borderColor: "#1976d2",
                          color: "#1976d2",
                          backgroundColor: "#f5f9ff",
                        },
                      }}
                    >
                      Acknowledge
                    </Button>
                  )}
                </Box>
              </Box>

              {index < alerts.length - 1 && <Divider />}
            </Box>
          );
        })}
      </Paper>

      {/* FOOTER NOTE */}
      <Box
        sx={{
          mt: 2,
          px: 0.5,
        }}
      >
        <Typography
          sx={{
            fontSize: 11,
            color: "#9aa3b2",
          }}
        >
          Alerts are model-derived advisories based on forecast air temperature
          against IMD's absolute thresholds, not an official IMD warning.
          Interpret them together with the heat-map and analytics data.
        </Typography>
      </Box>
    </Box>
  );
}
