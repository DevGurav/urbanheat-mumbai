import ErrorIcon from "@mui/icons-material/Error";
import ReportProblemIcon from "@mui/icons-material/ReportProblem";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import { Alert as MuiAlert, Box, Chip, CircularProgress, Paper, Typography } from "@mui/material";
import type { SvgIconComponent } from "@mui/icons-material";

import { useAlerts } from "../api/hooks";
import type { AlertPayload, AlertSeverity } from "../api/types";
import { MUTED_INK, STATUS } from "../viz/color";

const SEVERITY_META: Record<AlertSeverity, { label: string; color: string; Icon: SvgIconComponent }> = {
  advisory: { label: "Advisory", color: STATUS.warning, Icon: WarningAmberIcon },
  heat_wave: { label: "Heat wave", color: STATUS.serious, Icon: ReportProblemIcon },
  severe_heat_wave: { label: "Severe heat wave", color: STATUS.critical, Icon: ErrorIcon },
};

export function Alerts() {
  const { data, isLoading, isError } = useAlerts(50);

  return (
    <Box sx={{ p: 3, display: "flex", flexDirection: "column", gap: 2, overflow: "auto" }}>
      <Typography variant="h6">Alerts</Typography>
      <Typography variant="caption" sx={{ color: MUTED_INK }}>
        Advisory only — not an official IMD warning. Polled every 5 minutes; the underlying
        feed refreshes at most once a day (`GET /alerts`, ADR-0003).
      </Typography>

      {isLoading && <CircularProgress size={24} />}
      {isError && <MuiAlert severity="error">Couldn't load alerts — is the backend running?</MuiAlert>}

      {data && data.alerts.length === 0 && (
        <MuiAlert severity="success" variant="outlined">
          No active alerts. Most days, for Mumbai, that's the honest state — the Monitoring
          agent's threshold (45 °C+) is deliberately conservative (ADR-0010).
        </MuiAlert>
      )}

      {data && data.alerts.length > 0 && (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
          {data.alerts.map((alert, i) => (
            <AlertCard key={i} alert={alert} />
          ))}
        </Box>
      )}
    </Box>
  );
}

function AlertCard({ alert }: { alert: AlertPayload }) {
  const meta = SEVERITY_META[alert.severity];
  return (
    <Paper variant="outlined" sx={{ p: 2, borderLeft: `4px solid ${meta.color}` }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
        <Chip
          icon={<meta.Icon sx={{ color: `${meta.color} !important` }} />}
          label={meta.label}
          size="small"
          sx={{ bgcolor: `${meta.color}22`, fontWeight: 600 }}
        />
        <Typography variant="caption" sx={{ color: MUTED_INK }}>
          {alert.date} · forecast max {alert.forecast_max_c.toFixed(1)}°C
        </Typography>
      </Box>
      <Typography variant="body2" sx={{ mb: 1 }}>
        {alert.summary}
      </Typography>
      <Typography variant="caption" sx={{ color: MUTED_INK }}>
        Wards: {alert.wards_affected.join(", ")}
      </Typography>
      <Typography variant="caption" component="div" sx={{ color: MUTED_INK, mt: 0.5, fontStyle: "italic" }}>
        {alert.caveat}
      </Typography>
    </Paper>
  );
}
