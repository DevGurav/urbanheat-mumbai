import { useState } from "react";
import {
  Avatar,
  Box,
  Button,
  Divider,
  Menu,
  MenuItem,
  Typography,
} from "@mui/material";

import LoginRoundedIcon from "@mui/icons-material/LoginRounded";
import PersonOutlineRoundedIcon from "@mui/icons-material/PersonOutlineRounded";
import SettingsOutlinedIcon from "@mui/icons-material/SettingsOutlined";
import LogoutRoundedIcon from "@mui/icons-material/LogoutRounded";
import KeyboardArrowDownRoundedIcon from "@mui/icons-material/KeyboardArrowDownRounded";

export function SignInMenu() {
  const [signedIn, setSignedIn] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const menuOpen = Boolean(anchorEl);

  const handleOpenMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleCloseMenu = () => {
    setAnchorEl(null);
  };

  const handleSignIn = () => {
    setSignedIn(true);
  };

  const handleSignOut = () => {
    setSignedIn(false);
    setAnchorEl(null);
  };

  /* ================= LOGGED OUT ================= */

  if (!signedIn) {
    return (
      <Button
        onClick={handleSignIn}
        variant="contained"
        startIcon={<LoginRoundedIcon />}
        sx={{
          textTransform: "none",
          borderRadius: "10px",
          px: 2,
          py: 0.9,
          fontSize: 13,
          fontWeight: 700,
          backgroundColor: "#1976d2",
          boxShadow: "none",

          "&:hover": {
            backgroundColor: "#1565c0",
            boxShadow: "0 5px 14px rgba(25,118,210,0.22)",
          },
        }}
      >
        Sign in
      </Button>
    );
  }

  /* ================= LOGGED IN ================= */

  return (
    <>
      <Button
        onClick={handleOpenMenu}
        endIcon={<KeyboardArrowDownRoundedIcon />}
        sx={{
          textTransform: "none",
          color: "#172033",
          borderRadius: "11px",
          px: 0.8,
          py: 0.5,
          minWidth: 0,

          "&:hover": {
            backgroundColor: "#f4f7fb",
          },
        }}
      >
        <Avatar
          sx={{
            width: 34,
            height: 34,
            mr: 1,
            fontSize: 13,
            fontWeight: 800,
            background:
              "linear-gradient(135deg, #1976d2 0%, #42a5f5 100%)",
          }}
        >
          PA
        </Avatar>

        <Box
          sx={{
            display: {
              xs: "none",
              sm: "block",
            },
            textAlign: "left",
            mr: 0.5,
          }}
        >
          <Typography
            sx={{
              fontSize: 12.5,
              fontWeight: 700,
              lineHeight: 1.2,
              color: "#172033",
            }}
          >
            Punit Ayare
          </Typography>

          <Typography
            sx={{
              fontSize: 10.5,
              color: "#7b8494",
              lineHeight: 1.3,
            }}
          >
            Administrator
          </Typography>
        </Box>
      </Button>

      <Menu
        anchorEl={anchorEl}
        open={menuOpen}
        onClose={handleCloseMenu}
        anchorOrigin={{
          vertical: "bottom",
          horizontal: "right",
        }}
        transformOrigin={{
          vertical: "top",
          horizontal: "right",
        }}
        sx={{
          "& .MuiPaper-root": {
            mt: 1,
            minWidth: 250,
            borderRadius: "14px",
            border: "1px solid #e5e9f0",
            boxShadow: "0 12px 35px rgba(20,35,60,0.12)",
            overflow: "hidden",
          },
        }}
      >
        {/* ACCOUNT HEADER */}
        <Box
          sx={{
            px: 2,
            py: 1.8,
            backgroundColor: "#f8fafc",
          }}
        >
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1.3,
            }}
          >
            <Avatar
              sx={{
                width: 42,
                height: 42,
                fontSize: 14,
                fontWeight: 800,
                background:
                  "linear-gradient(135deg, #1976d2 0%, #42a5f5 100%)",
              }}
            >
              PA
            </Avatar>

            <Box>
              <Typography
                sx={{
                  fontSize: 13.5,
                  fontWeight: 800,
                  color: "#172033",
                }}
              >
                Punit Ayare
              </Typography>

              <Typography
                sx={{
                  fontSize: 11,
                  color: "#7b8494",
                  mt: 0.2,
                }}
              >
                UrbanHeat AI
              </Typography>
            </Box>
          </Box>
        </Box>

        <Divider />

        {/* PROFILE */}
        <MenuItem
          onClick={handleCloseMenu}
          sx={{
            py: 1.25,
            px: 2,
            gap: 1.4,
            fontSize: 13,
          }}
        >
          <PersonOutlineRoundedIcon
            sx={{
              fontSize: 20,
              color: "#64748b",
            }}
          />

          <Box>
            <Typography
              sx={{
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              Profile
            </Typography>

            <Typography
              sx={{
                fontSize: 10.5,
                color: "#8993a3",
              }}
            >
              View your account
            </Typography>
          </Box>
        </MenuItem>

        {/* SETTINGS */}
        <MenuItem
          onClick={handleCloseMenu}
          sx={{
            py: 1.25,
            px: 2,
            gap: 1.4,
            fontSize: 13,
          }}
        >
          <SettingsOutlinedIcon
            sx={{
              fontSize: 20,
              color: "#64748b",
            }}
          />

          <Box>
            <Typography
              sx={{
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              Settings
            </Typography>

            <Typography
              sx={{
                fontSize: 10.5,
                color: "#8993a3",
              }}
            >
              Manage preferences
            </Typography>
          </Box>
        </MenuItem>

        <Divider />

        {/* SIGN OUT */}
        <MenuItem
          onClick={handleSignOut}
          sx={{
            py: 1.25,
            px: 2,
            gap: 1.4,
            color: "#d32f2f",
            fontSize: 13,
            fontWeight: 600,
          }}
        >
          <LogoutRoundedIcon
            sx={{
              fontSize: 20,
            }}
          />

          Sign out
        </MenuItem>
      </Menu>
    </>
  );
}
