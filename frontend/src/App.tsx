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
import { Scenario } from "./sections/Scenario";

const SECTIONS = [
  { label: "Heat intelligence", key: "map" },
  { label: "Hotspots", key: "analytics" },
  { label: "Scenarios", key: "scenario" },
  { label: "AI Copilot", key: "chat" },
  { label: "Alerts", key: "alerts" },
] as const;

type SectionKey = (typeof SECTIONS)[number]["key"];

function App() {
  const [section, setSection] = useState<SectionKey>("map");

  return (
    <Box className="app-shell">
      <AppBar
        position="sticky"
        elevation={0}
        sx={{
          background:
            "linear-gradient(135deg, #063B8F 0%, #0B5ED7 55%, #087FCE 100%)",
          color: "#ffffff",
          boxShadow: "0 4px 20px rgba(11, 94, 215, 0.25)",
        }}
      >
        <Toolbar className="app-toolbar">

          {/* BRAND */}
          <Box
            className="brand"
            onClick={() => setSection("map")}
            sx={{
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
            }}
          >
            <Box className="brand-mark">
              <ThermostatRoundedIcon />
            </Box>

            <Box>
              <Typography className="brand-name">
                UrbanHeat <span>AI</span>
              </Typography>

              <Typography className="brand-subtitle">
                Mumbai climate intelligence
              </Typography>
            </Box>
          </Box>

          {/* NAVIGATION */}
          <Tabs
            value={section}
            onChange={(_, value: SectionKey) => setSection(value)}
            variant="scrollable"
            scrollButtons="auto"
            sx={{
              marginLeft: 4,

              "& .MuiTab-root": {
                color: "rgba(255,255,255,0.70)",
                fontWeight: 600,
                textTransform: "none",
                fontSize: "0.95rem",
                minHeight: 64,
              },

              "& .MuiTab-root:hover": {
                color: "#ffffff",
              },

              "& .Mui-selected": {
                color: "#ffffff !important",
              },

              "& .MuiTabs-indicator": {
                backgroundColor: "#5EE7FF",
                height: 3,
                borderRadius: "3px 3px 0 0",
              },
            }}
          >
            {SECTIONS.map((s) => (
              <Tab
                key={s.key}
                value={s.key}
                label={s.label}
              />
            ))}
          </Tabs>

          <Box sx={{ flex: 1 }} />

          {/* ALERTS */}
          <Tooltip title="Monitoring alerts">
            <IconButton
              sx={{ color: "#ffffff" }}
              onClick={() => setSection("alerts")}
            >
              <Badge color="warning" variant="dot">
                <NotificationsNoneRoundedIcon />
              </Badge>
            </IconButton>
          </Tooltip>

          {/* SIGN IN */}
          <SignInMenu />
        </Toolbar>
      </AppBar>

      {/* CONTENT */}
      <Box className="app-content">
        {section === "map" && <HeatMap />}

        {section === "analytics" && <Analytics />}

        {section === "scenario" && <Scenario />}

        {section === "chat" && <Chat />}

        {section === "alerts" && <Alerts />}
      </Box>

      {/* MOBILE HOME */}
      <Box
        className="mobile-home"
        onClick={() => setSection("map")}
        sx={{
          cursor: "pointer",
        }}
      >
        <HomeRoundedIcon fontSize="small" />

        <Typography variant="caption">
          Home
        </Typography>
      </Box>
    </Box>
  );
}

export default App;
