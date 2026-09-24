import {
  AppBar,
  Badge,
  Box,
  IconButton,
  Tab,
  Tabs,
  Toolbar,
  Tooltip,
  Typography,
} from "@mui/material";
import { useState } from "react";
import NotificationsNoneRoundedIcon from "@mui/icons-material/NotificationsNoneRounded";
import ThermostatRoundedIcon from "@mui/icons-material/ThermostatRounded";
import HomeRoundedIcon from "@mui/icons-material/HomeRounded";

import { SignInMenu } from "./auth/SignInMenu";
import { Alerts } from "./sections/Alerts";
import { Analytics } from "./sections/Analytics";
import { Chat } from "./sections/Chat";
import { HeatMap } from "./sections/HeatMap";
import { Overview } from "./sections/Overview";
import { Scenario } from "./sections/Scenario";

const SECTIONS = [
  { label: "Overview", key: "overview" },
  { label: "Heat intelligence", key: "map" },
  { label: "Hotspots", key: "analytics" },
  { label: "Scenarios", key: "scenario" },
  { label: "AI Copilot", key: "chat" },
  { label: "Alerts", key: "alerts" },
] as const;

type SectionKey = (typeof SECTIONS)[number]["key"];

function App() {
  const [section, setSection] = useState<SectionKey>("overview");

  const navigate = (key: Exclude<SectionKey, "overview" | "alerts">) => setSection(key);

  return (
    <Box className="app-shell">
      <AppBar position="sticky" className="app-bar" elevation={0}>
        <Toolbar className="app-toolbar">
          <Box className="brand" onClick={() => setSection("overview")} sx={{ cursor: "pointer" }}>
            <Box className="brand-mark">
              <ThermostatRoundedIcon />
            </Box>
            <Box>
              <Typography className="brand-name">UrbanHeat <span>AI</span></Typography>
              <Typography className="brand-subtitle">Mumbai climate intelligence</Typography>
            </Box>
          </Box>

          <Tabs
            value={section}
            onChange={(_, value: SectionKey) => setSection(value)}
            className="main-tabs"
            variant="scrollable"
            scrollButtons="auto"
          >
            {SECTIONS.map((s) => (
              <Tab key={s.key} value={s.key} label={s.label} />
            ))}
          </Tabs>

          <Box sx={{ flex: 1 }} />

          <Tooltip title="Monitoring alerts">
            <IconButton className="alert-button" onClick={() => setSection("alerts")}>
              <Badge color="warning" variant="dot">
                <NotificationsNoneRoundedIcon />
              </Badge>
            </IconButton>
          </Tooltip>
          <SignInMenu />
        </Toolbar>
      </AppBar>

      <Box className="app-content">
        {section === "overview" && <Overview onNavigate={navigate} />}
        {section === "map" && <HeatMap />}
        {section === "analytics" && <Analytics />}
        {section === "scenario" && <Scenario />}
        {section === "chat" && <Chat />}
        {section === "alerts" && <Alerts />}
      </Box>

      <Box className="mobile-home" onClick={() => setSection("overview")}>
        <HomeRoundedIcon fontSize="small" />
        <Typography variant="caption">Home</Typography>
      </Box>
    </Box>
  );
}

export default App;
