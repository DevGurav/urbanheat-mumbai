import { AppBar, Box, Tab, Tabs, Toolbar, Typography } from "@mui/material";
import { useState } from "react";

import { SignInMenu } from "./auth/SignInMenu";
import { Alerts } from "./sections/Alerts";
import { Analytics } from "./sections/Analytics";
import { Chat } from "./sections/Chat";
import { HeatMap } from "./sections/HeatMap";
import { Scenario } from "./sections/Scenario";

const SECTIONS = [
  { label: "Heat map", key: "map" },
  { label: "Analytics", key: "analytics" },
  { label: "Scenario", key: "scenario" },
  { label: "Copilot", key: "chat" },
  { label: "Alerts", key: "alerts" },
] as const;

type SectionKey = (typeof SECTIONS)[number]["key"];

function App() {
  const [section, setSection] = useState<SectionKey>("map");

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        backgroundColor: "#f7f9fc",
      }}
    >
      {/* HEADER */}
      <AppBar
        position="static"
        elevation={0}
        sx={{
          backgroundColor: "#ffffff",
          color: "#172033",
          borderBottom: "1px solid #e7eaf0",
        }}
      >
        <Toolbar
          sx={{
            minHeight: "68px !important",
            px: {
              xs: 2,
              md: 3,
            },
            gap: 2,
          }}
        >
          {/* BRAND */}
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1.3,
              mr: {
                xs: 1,
                md: 3,
              },
              flexShrink: 0,
            }}
          >
            {/* Logo */}
            <Box
              sx={{
                width: 38,
                height: 38,
                borderRadius: "11px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background:
                  "linear-gradient(135deg, #1976d2 0%, #42a5f5 100%)",
                boxShadow: "0 5px 14px rgba(25,118,210,0.22)",
              }}
            >
              <Typography
                sx={{
                  color: "#ffffff",
                  fontSize: 20,
                  fontWeight: 800,
                  lineHeight: 1,
                }}
              >
                U
              </Typography>
            </Box>

            {/* Brand */}
            <Box sx={{ display: { xs: "none", sm: "block" } }}>
              <Typography
                sx={{
                  fontSize: 17,
                  fontWeight: 800,
                  lineHeight: 1.1,
                  letterSpacing: "-0.3px",
                  color: "#172033",
                }}
              >
                UrbanHeat
                <Box
                  component="span"
                  sx={{
                    color: "#1976d2",
                    ml: 0.4,
                  }}
                >
                  AI
                </Box>
              </Typography>

              <Typography
                sx={{
                  fontSize: 10,
                  color: "#7b8494",
                  mt: 0.25,
                  letterSpacing: "0.4px",
                }}
              >
                URBAN CLIMATE INTELLIGENCE
              </Typography>
            </Box>
          </Box>

          {/* NAVIGATION */}
          <Tabs
            value={section}
            onChange={(_, value: SectionKey) => setSection(value)}
            variant="scrollable"
            scrollButtons={false}
            sx={{
              minHeight: 68,

              "& .MuiTabs-flexContainer": {
                gap: 0.4,
              },

              "& .MuiTab-root": {
                minHeight: 68,
                minWidth: "auto",
                px: {
                  xs: 1.2,
                  md: 1.6,
                },
                textTransform: "none",
                fontSize: 13.5,
                fontWeight: 600,
                color: "#697386",
                position: "relative",
              },

              "& .MuiTab-root:hover": {
                color: "#1976d2",
              },

              "& .Mui-selected": {
                color: "#1976d2 !important",
                fontWeight: 700,
              },

              "& .MuiTabs-indicator": {
                height: 3,
                borderRadius: "3px 3px 0 0",
                backgroundColor: "#1976d2",
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

          {/* SPACER */}
          <Box sx={{ flex: 1 }} />

          {/* RIGHT SIDE */}
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1,
            }}
          >
            {/* System status */}
            <Box
              sx={{
                display: {
                  xs: "none",
                  lg: "flex",
                },
                alignItems: "center",
                gap: 0.8,
                px: 1.4,
                py: 0.7,
                borderRadius: 2,
                backgroundColor: "#f5f8fc",
                border: "1px solid #e7ebf2",
              }}
            >
              <Box
                sx={{
                  width: 7,
                  height: 7,
                  borderRadius: "50%",
                  backgroundColor: "#22c55e",
                  boxShadow: "0 0 0 3px rgba(34,197,94,0.10)",
                }}
              />

              <Typography
                sx={{
                  fontSize: 11.5,
                  fontWeight: 600,
                  color: "#596579",
                }}
              >
                System online
              </Typography>
            </Box>

            {/* Authentication */}
            <SignInMenu />
          </Box>
        </Toolbar>
      </AppBar>

      {/* CONTENT */}
      <Box
        sx={{
          flex: 1,
          overflow: "auto",
          backgroundColor: "#f7f9fc",
        }}
      >
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
