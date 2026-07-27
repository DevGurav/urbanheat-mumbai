import { Box, Typography } from "@mui/material";

/** Stand-in for a section not built yet — PROGRESS.md's Phase 5 board, one group at a time. */
export function Placeholder({ title }: { title: string }) {
  return (
    <Box sx={{ p: 4 }}>
      <Typography variant="h5" gutterBottom>
        {title}
      </Typography>
      <Typography color="text.secondary">Not built yet.</Typography>
    </Box>
  );
}
