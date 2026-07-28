import { AppBar, Box, Tab, Tabs, Toolbar, Typography } from "@mui/material";
import { useState } from "react";

import { Alerts } from "./sections/Alerts";
import { Analytics } from "./sections/Analytics";
import { Chat } from "./sections/Chat";
import { HeatMap } from "./sections/HeatMap";
import { Scenario } from "./sections/Scenario";

const SECTIONS = [
  { label: "Heat map", key: "map" },
  { label: "Analytics", key: "analytics" },
  { label: "Scenario simulator", key: "scenario" },
  { label: "Copilot", key: "chat" },
  { label: "Alerts", key: "alerts" },
] as const;

type SectionKey = (typeof SECTIONS)[number]["key"];

function App() {
  const [section, setSection] = useState<SectionKey>("map");

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <AppBar position="static" color="primary" enableColorOnDark>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ mr: 4 }}>
            UrbanHeat AI
          </Typography>
          <Tabs
            value={section}
            onChange={(_, value: SectionKey) => setSection(value)}
            textColor="inherit"
            indicatorColor="secondary"
          >
            {SECTIONS.map((s) => (
              <Tab key={s.key} value={s.key} label={s.label} />
            ))}
          </Tabs>
        </Toolbar>
      </AppBar>

      <Box sx={{ flex: 1, overflow: "auto" }}>
        {section === "map" && <HeatMap />}
        {section === "analytics" && <Analytics />}
        {section === "scenario" && <Scenario />}
        {section === "chat" && <Chat />}
        {section === "alerts" && <Alerts />}
      </Box>
    </Box>
  );
}

export default App;
