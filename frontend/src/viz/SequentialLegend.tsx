import { Box, Paper, Typography } from "@mui/material";

import { MUTED_INK, SEQUENTIAL_BLUE } from "./color";

/** A labeled gradient bar for a sequential (magnitude) scale — the choropleth's legend.
 * Values, not just color, so the map is never color-alone (dataviz skill, interaction.md).
 */
export function SequentialLegend({
  min,
  max,
  unit,
  title,
}: {
  min: number;
  max: number;
  unit: string;
  title: string;
}) {
  const gradient = `linear-gradient(to right, ${SEQUENTIAL_BLUE.join(", ")})`;
  return (
    <Paper
      elevation={2}
      sx={{ position: "absolute", bottom: 16, left: 16, p: 1.5, minWidth: 200, zIndex: 1000 }}
    >
      <Typography variant="caption" sx={{ color: MUTED_INK }}>
        {title}
      </Typography>
      <Box sx={{ height: 10, borderRadius: 1, background: gradient, mt: 0.5 }} />
      <Box sx={{ display: "flex", justifyContent: "space-between", mt: 0.5 }}>
        <Typography variant="caption" sx={{ color: MUTED_INK }}>
          {min.toFixed(1)}
          {unit}
        </Typography>
        <Typography variant="caption" sx={{ color: MUTED_INK }}>
          {max.toFixed(1)}
          {unit}
        </Typography>
      </Box>
    </Paper>
  );
}
