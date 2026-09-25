import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  Collapse,
  IconButton,
  Paper,
  TextField,
  Typography,
} from "@mui/material";
import { useState } from "react";
import {
  MapContainer,
  TileLayer,
  GeoJSON as LeafletGeoJSON,
} from "react-leaflet";
import ReactMarkdown from "react-markdown";

import SendRoundedIcon from "@mui/icons-material/SendRounded";
import AutoAwesomeRoundedIcon from "@mui/icons-material/AutoAwesomeRounded";
import SmartToyRoundedIcon from "@mui/icons-material/SmartToyRounded";
import ExpandMoreRoundedIcon from "@mui/icons-material/ExpandMoreRounded";
import ExpandLessRoundedIcon from "@mui/icons-material/ExpandLessRounded";
import MapRoundedIcon from "@mui/icons-material/MapRounded";
import BuildRoundedIcon from "@mui/icons-material/BuildRounded";
import ErrorOutlineRoundedIcon from "@mui/icons-material/ErrorOutlineRounded";
import ThermostatRoundedIcon from "@mui/icons-material/ThermostatRounded";
import InsightsRoundedIcon from "@mui/icons-material/InsightsRounded";

import { ApiError } from "../api/client";
import { useAgentChat } from "../api/hooks";
import type {
  AgentChatResponse,
  AgentName,
  AgentToolCall,
} from "../api/types";
import { MUTED_INK, sequentialScale } from "../viz/color";

const MUMBAI_CENTER: [number, number] = [19.076, 72.8777];

const AGENT_LABEL: Record<AgentName, string> = {
  copilot: "Copilot",
  planning: "Planning",
  digital_twin: "Digital Twin",
};

type Turn =
  | { role: "user"; text: string }
  | { role: "assistant"; response: AgentChatResponse }
  | {
      role: "error";
      message: string;
      errorCode: string | null;
    };

export function Chat() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const chat = useAgentChat();

  function send() {
    const message = input.trim();

    if (!message || chat.isPending) return;

    setTurns((t) => [...t, { role: "user", text: message }]);
    setInput("");

    chat.mutate(message, {
      onSuccess: (response) =>
        setTurns((t) => [
          ...t,
          {
            role: "assistant",
            response,
          },
        ]),

      onError: (err) => {
        const isApiError = err instanceof ApiError;

        setTurns((t) => [
          ...t,
          {
            role: "error",
            message: isApiError
              ? err.message
              : "Something went wrong.",
            errorCode: isApiError ? err.errorCode : null,
          },
        ]);
      },
    });
  }

  return (
    <Box
      sx={{
        height: "100%",
        width: "100%",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        bgcolor: "#f4f8f7",
      }}
    >
      {/* HEADER */}
      <Box
        sx={{
          px: { xs: 2, md: 4 },
          pt: { xs: 2, md: 3 },
          pb: 2,
          background:
            "linear-gradient(135deg, #073b35 0%, #0b5f52 55%, #168563 100%)",
          color: "#ffffff",
          position: "relative",
          overflow: "hidden",
          flexShrink: 0,
        }}
      >
        <Box
          sx={{
            position: "absolute",
            width: 240,
            height: 240,
            borderRadius: "50%",
            right: -70,
            top: -130,
            bgcolor: "rgba(255,255,255,0.06)",
          }}
        />

        <Box
          sx={{
            position: "absolute",
            width: 150,
            height: 150,
            borderRadius: "50%",
            right: 100,
            bottom: -110,
            bgcolor: "rgba(255,255,255,0.04)",
          }}
        />

        <Box
          sx={{
            position: "relative",
            zIndex: 1,
            maxWidth: 1200,
            mx: "auto",
            width: "100%",
          }}
        >
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1.5,
            }}
          >
            <Box
              sx={{
                width: 46,
                height: 46,
                borderRadius: 2.5,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                bgcolor: "rgba(255,255,255,0.14)",
                border: "1px solid rgba(255,255,255,0.18)",
                backdropFilter: "blur(8px)",
              }}
            >
              <AutoAwesomeRoundedIcon />
            </Box>

            <Box>
              <Typography
                variant="overline"
                sx={{
                  display: "block",
                  fontWeight: 800,
                  letterSpacing: ".14em",
                  lineHeight: 1.2,
                  color: "rgba(255,255,255,0.72)",
                }}
              >
                AI DECISION SUPPORT
              </Typography>

              <Typography
                variant="h4"
                sx={{
                  fontWeight: 800,
                  letterSpacing: "-.04em",
                  lineHeight: 1.15,
                }}
              >
                UrbanHeat Copilot
              </Typography>
            </Box>
          </Box>

          <Typography
            variant="body2"
            sx={{
              mt: 1.2,
              maxWidth: 700,
              color: "rgba(255,255,255,0.78)",
              lineHeight: 1.6,
            }}
          >
            Explore Mumbai's urban heat intelligence using natural
            language. Ask about hotspots, drivers, weather,
            interventions, or model explanations.
          </Typography>

          <Box
            sx={{
              display: "flex",
              flexWrap: "wrap",
              gap: 0.8,
              mt: 2,
            }}
          >
            <HeaderPill
              icon={<ThermostatRoundedIcon />}
              label="Heat intelligence"
            />

            <HeaderPill
              icon={<InsightsRoundedIcon />}
              label="Model insights"
            />

            <HeaderPill
              icon={<MapRoundedIcon />}
              label="Spatial analysis"
            />

            <HeaderPill
              icon={<AutoAwesomeRoundedIcon />}
              label="AI assistance"
            />
          </Box>
        </Box>
      </Box>

      {/* MAIN CHAT */}
      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          overflow: "auto",
          px: { xs: 1.5, md: 3 },
          py: 2,
        }}
      >
        <Box
          sx={{
            maxWidth: 1100,
            mx: "auto",
            width: "100%",
          }}
        >
          {/* INFORMATION */}
          <Alert
            icon={<AutoAwesomeRoundedIcon fontSize="small" />}
            severity="info"
            sx={{
              mb: 2,
              borderRadius: 3,
              bgcolor: "#eaf5f2",
              color: "#164d44",
              border: "1px solid #cce6df",

              "& .MuiAlert-icon": {
                color: "#168563",
              },
            }}
          >
            <Typography
              variant="body2"
              sx={{
                lineHeight: 1.55,
              }}
            >
              The free Gemini tier caps at ~20 requests/day for this
              project. Identical questions are cached, while distinct
              questions consume quota. Responses may take several
              seconds while the AI processes the request.
            </Typography>
          </Alert>

          {/* EMPTY STATE */}
          {turns.length === 0 && !chat.isPending && (
            <EmptyChatState
              onPrompt={(prompt) => {
                setInput(prompt);
              }}
            />
          )}

          {/* CONVERSATION */}
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              gap: 1.5,
            }}
          >
            {turns.map((turn, i) => (
              <TurnBubble
                key={i}
                turn={turn}
              />
            ))}

            {chat.isPending && <ThinkingBubble />}
          </Box>
        </Box>
      </Box>

      {/* INPUT */}
      <Box
        sx={{
          flexShrink: 0,
          borderTop: "1px solid #dce7e4",
          bgcolor: "rgba(255,255,255,0.96)",
          backdropFilter: "blur(12px)",
          px: { xs: 1.5, md: 3 },
          py: 1.5,
        }}
      >
        <Box
          sx={{
            maxWidth: 1100,
            mx: "auto",
            width: "100%",
          }}
        >
          <Paper
            elevation={0}
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1,
              p: 0.7,
              pl: 1.5,
              borderRadius: 3,
              border: "1px solid #d4e2df",
              bgcolor: "#f8fbfa",
              transition: "all .2s ease",

              "&:focus-within": {
                borderColor: "#168563",
                boxShadow: "0 0 0 3px rgba(22,133,99,0.10)",
                bgcolor: "#ffffff",
              },
            }}
          >
            <TextField
              fullWidth
              multiline
              maxRows={4}
              variant="standard"
              placeholder="Ask about heat, hotspots, weather, or a what-if scenario…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              disabled={chat.isPending}
              sx={{
                "& .MuiInput-root": {
                  "&:before": {
                    borderBottom: "none",
                  },
                  "&:after": {
                    borderBottom: "none",
                  },
                  "&:hover:not(.Mui-disabled):before": {
                    borderBottom: "none",
                  },
                },

                "& .MuiInputBase-root": {
                  fontSize: 14,
                  py: 0.5,
                },
              }}
            />

            <IconButton
              onClick={send}
              disabled={chat.isPending || !input.trim()}
              sx={{
                width: 44,
                height: 44,
                flexShrink: 0,
                bgcolor: "#0b6b5a",
                color: "#ffffff",

                "&:hover": {
                  bgcolor: "#075647",
                },

                "&.Mui-disabled": {
                  bgcolor: "#d9e5e2",
                  color: "#8aa19b",
                },
              }}
            >
              <SendRoundedIcon fontSize="small" />
            </IconButton>
          </Paper>

          <Typography
            variant="caption"
            sx={{
              display: "block",
              textAlign: "center",
              color: "#82918d",
              mt: 0.7,
              fontSize: 11,
            }}
          >
            UrbanHeat AI can assist with interpretation and planning.
            Verify critical decisions against source data.
          </Typography>
        </Box>
      </Box>
    </Box>
  );
}

function HeaderPill({
  icon,
  label,
}: {
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <Box
      sx={{
        display: "inline-flex",
        alignItems: "center",
        gap: 0.6,
        px: 1,
        py: 0.55,
        borderRadius: 10,
        bgcolor: "rgba(255,255,255,0.10)",
        border: "1px solid rgba(255,255,255,0.13)",
        color: "rgba(255,255,255,0.82)",
        fontSize: 11,
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          "& svg": {
            fontSize: 15,
          },
        }}
      >
        {icon}
      </Box>

      {label}
    </Box>
  );
}

function EmptyChatState({
  onPrompt,
}: {
  onPrompt: (prompt: string) => void;
}) {
  const prompts = [
    {
      icon: <ThermostatRoundedIcon />,
      title: "Explore heat",
      text: "Which areas of Mumbai have the highest heat?",
      prompt: "Which areas of Mumbai have the highest heat?",
    },
    {
      icon: <InsightsRoundedIcon />,
      title: "Understand drivers",
      text: "What are the main factors driving urban heat?",
      prompt: "What are the main factors driving urban heat?",
    },
    {
      icon: <MapRoundedIcon />,
      title: "Analyze hotspots",
      text: "Explain the current urban heat hotspots.",
      prompt: "Explain the current urban heat hotspots.",
    },
    {
      icon: <AutoAwesomeRoundedIcon />,
      title: "Try planning",
      text: "What interventions could reduce heat?",
      prompt: "What interventions could reduce heat?",
    },
  ];

  return (
    <Box
      sx={{
        py: { xs: 4, md: 6 },
        px: 1,
      }}
    >
      <Box
        sx={{
          textAlign: "center",
          maxWidth: 650,
          mx: "auto",
        }}
      >
        <Box
          sx={{
            width: 64,
            height: 64,
            mx: "auto",
            mb: 2,
            borderRadius: "20px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background:
              "linear-gradient(135deg, #0b6b5a, #25a17f)",
            color: "#ffffff",
            boxShadow: "0 10px 30px rgba(11,107,90,0.20)",
          }}
        >
          <SmartToyRoundedIcon sx={{ fontSize: 32 }} />
        </Box>

        <Typography
          variant="h5"
          sx={{
            fontWeight: 800,
            letterSpacing: "-.025em",
            color: "#163a34",
          }}
        >
          What would you like to explore?
        </Typography>

        <Typography
          variant="body2"
          sx={{
            mt: 0.8,
            color: "#70817d",
          }}
        >
          Ask the UrbanHeat AI Copilot about Mumbai's climate
          intelligence.
        </Typography>
      </Box>

      <Box
        sx={{
          maxWidth: 850,
          mx: "auto",
          mt: 3,
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            sm: "repeat(2, 1fr)",
          },
          gap: 1.5,
        }}
      >
        {prompts.map((item) => (
          <Paper
            key={item.title}
            elevation={0}
            onClick={() => onPrompt(item.prompt)}
            sx={{
              p: 1.7,
              borderRadius: 3,
              border: "1px solid #dce7e4",
              bgcolor: "#ffffff",
              cursor: "pointer",
              transition: "all .2s ease",

              "&:hover": {
                transform: "translateY(-2px)",
                borderColor: "#8acbb9",
                boxShadow: "0 8px 24px rgba(17,78,67,0.08)",
              },
            }}
          >
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
              }}
            >
              <Box
                sx={{
                  width: 34,
                  height: 34,
                  borderRadius: 2,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  bgcolor: "#eaf5f2",
                  color: "#0b6b5a",

                  "& svg": {
                    fontSize: 19,
                  },
                }}
              >
                {item.icon}
              </Box>

              <Typography
                variant="subtitle2"
                sx={{
                  fontWeight: 800,
                  color: "#24443e",
                }}
              >
                {item.title}
              </Typography>
            </Box>

            <Typography
              variant="body2"
              sx={{
                mt: 1,
                color: "#71827e",
                lineHeight: 1.5,
              }}
            >
              {item.text}
            </Typography>
          </Paper>
        ))}
      </Box>
    </Box>
  );
}

function ThinkingBubble() {
  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "flex-start",
        gap: 1,
      }}
    >
      <Box
        sx={{
          width: 34,
          height: 34,
          flexShrink: 0,
          borderRadius: "50%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          bgcolor: "#e5f3ef",
          color: "#0b6b5a",
        }}
      >
        <SmartToyRoundedIcon sx={{ fontSize: 18 }} />
      </Box>

      <Paper
        elevation={0}
        sx={{
          px: 1.7,
          py: 1.3,
          borderRadius: "4px 16px 16px 16px",
          border: "1px solid #dce7e4",
          bgcolor: "#ffffff",
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
          }}
        >
          <CircularProgress
            size={15}
            thickness={4}
            sx={{
              color: "#168563",
            }}
          />

          <Typography
            variant="body2"
            sx={{
              color: MUTED_INK,
            }}
          >
            Analyzing Mumbai heat intelligence…
          </Typography>
        </Box>
      </Paper>
    </Box>
  );
}

function TurnBubble({ turn }: { turn: Turn }) {
  /* USER MESSAGE */
  if (turn.role === "user") {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "flex-end",
          alignItems: "flex-end",
          gap: 1,
        }}
      >
        <Paper
          elevation={0}
          sx={{
            px: 1.8,
            py: 1.3,
            maxWidth: {
              xs: "88%",
              sm: "72%",
            },
            borderRadius: "18px 18px 4px 18px",
            bgcolor: "#0b6b5a",
            color: "#ffffff",
            boxShadow: "0 5px 18px rgba(11,107,90,0.12)",
          }}
        >
          <Typography
            variant="body2"
            sx={{
              lineHeight: 1.55,
            }}
          >
            {turn.text}
          </Typography>
        </Paper>
      </Box>
    );
  }

  /* ERROR MESSAGE */
  if (turn.role === "error") {
    const label =
      turn.errorCode === "agent_layer_unavailable"
        ? "The agent layer isn't configured (RAG index or GEMINI_API_KEY missing)."
        : turn.errorCode === "agent_upstream_unavailable"
        ? "The LLM call failed upstream — likely the daily quota is exhausted."
        : "Couldn't reach the agent.";

    return (
      <Box
        sx={{
          display: "flex",
          alignItems: "flex-start",
          gap: 1,
        }}
      >
        <Box
          sx={{
            width: 34,
            height: 34,
            flexShrink: 0,
            borderRadius: "50%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            bgcolor: "#fff1e9",
            color: "#c75b24",
          }}
        >
          <ErrorOutlineRoundedIcon sx={{ fontSize: 19 }} />
        </Box>

        <Alert
          severity="warning"
          sx={{
            maxWidth: "82%",
            borderRadius: "4px 16px 16px 16px",
          }}
        >
          <Typography
            variant="body2"
            sx={{
              fontWeight: 700,
            }}
          >
            {label}
          </Typography>

          <Typography
            variant="caption"
            sx={{
              display: "block",
              mt: 0.5,
              color: MUTED_INK,
            }}
          >
            {turn.message}
          </Typography>
        </Alert>
      </Box>
    );
  }

  /* ASSISTANT MESSAGE */
  const { response } = turn;

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "flex-start",
        gap: 1,
      }}
    >
      <Box
        sx={{
          width: 34,
          height: 34,
          flexShrink: 0,
          borderRadius: "50%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          bgcolor: "#e5f3ef",
          color: "#0b6b5a",
          border: "1px solid #cce6df",
        }}
      >
        <SmartToyRoundedIcon sx={{ fontSize: 18 }} />
      </Box>

      <Paper
        variant="outlined"
        sx={{
          p: { xs: 1.5, md: 2 },
          maxWidth: {
            xs: "88%",
            sm: "82%",
          },
          borderRadius: "4px 18px 18px 18px",
          borderColor: "#dce7e4",
          bgcolor: "#ffffff",
          boxShadow: "0 3px 14px rgba(24,65,57,0.04)",
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 1,
            mb: 1.2,
          }}
        >
          <Chip
            icon={<AutoAwesomeRoundedIcon />}
            label={AGENT_LABEL[response.agent]}
            size="small"
            sx={{
              height: 28,
              bgcolor: "#eaf5f2",
              color: "#0b6b5a",
              fontWeight: 700,

              "& .MuiChip-icon": {
                color: "#168563",
                fontSize: 16,
              },
            }}
          />

          {response.layer && (
            <Chip
              icon={<MapRoundedIcon />}
              label="Map"
              size="small"
              variant="outlined"
              sx={{
                height: 27,
                color: "#53716b",
                borderColor: "#cbdcd8",

                "& .MuiChip-icon": {
                  fontSize: 16,
                },
              }}
            />
          )}
        </Box>

        <Box
          sx={{
            fontSize: 14,
            lineHeight: 1.7,
            color: "#273d38",

            "& p": {
              m: 0,
              mb: 1,
            },

            "& p:last-child": {
              mb: 0,
            },

            "& ul, & ol": {
              m: 0,
              mb: 1,
              pl: 2.5,
            },

            "& li": {
              mb: 0.35,
            },

            "& h1, & h2, & h3": {
              fontSize: "1.05rem",
              fontWeight: 700,
              mt: 1.5,
              mb: 0.6,
              color: "#163a34",
            },

            "& strong": {
              fontWeight: 700,
              color: "#163a34",
            },

            "& code": {
              fontFamily: "monospace",
              fontSize: "0.9em",
              bgcolor: "#eef4f2",
              px: 0.6,
              py: 0.2,
              borderRadius: 0.7,
            },

            "& blockquote": {
              m: 0,
              my: 1,
              pl: 1.5,
              borderLeft: "3px solid #7cc5b1",
              color: "#61746f",
            },
          }}
        >
          <ReactMarkdown>
            {response.text}
          </ReactMarkdown>
        </Box>

        {response.tool_calls.length > 0 && (
          <ToolCallList calls={response.tool_calls} />
        )}

        {response.layer && (
          <LayerMap layer={response.layer} />
        )}
      </Paper>
    </Box>
  );
}

function ToolCallList({
  calls,
}: {
  calls: AgentToolCall[];
}) {
  const [open, setOpen] = useState(false);

  return (
    <Box
      sx={{
        mt: 1.5,
        pt: 1.2,
        borderTop: "1px solid #e5eeeb",
      }}
    >
      <Box
        onClick={() => setOpen((o) => !o)}
        sx={{
          display: "inline-flex",
          alignItems: "center",
          gap: 0.4,
          cursor: "pointer",
          color: "#5f7771",
          userSelect: "none",
        }}
      >
        <BuildRoundedIcon sx={{ fontSize: 15 }} />

        <Typography
          variant="caption"
          sx={{
            fontWeight: 700,
          }}
        >
          {open ? "Hide" : "Show"} {calls.length} tool call
          {calls.length === 1 ? "" : "s"}
        </Typography>

        {open ? (
          <ExpandLessRoundedIcon sx={{ fontSize: 17 }} />
        ) : (
          <ExpandMoreRoundedIcon sx={{ fontSize: 17 }} />
        )}
      </Box>

      <Collapse in={open}>
        <Box
          sx={{
            mt: 1,
            display: "flex",
            flexDirection: "column",
            gap: 0.7,
          }}
        >
          {calls.map((c, i) => (
            <Box
              key={i}
              sx={{
                p: 1.2,
                borderRadius: 2,
                bgcolor: "#f5f8f7",
                border: "1px solid #e1ebe8",
              }}
            >
              <Typography
                variant="caption"
                component="div"
                sx={{
                  fontWeight: 700,
                  color: "#31534b",
                }}
              >
                {c.name}({JSON.stringify(c.args)})
              </Typography>

              <Typography
                variant="caption"
                component="div"
                sx={{
                  mt: 0.4,
                  color: MUTED_INK,
                  fontFamily: "monospace",
                  wordBreak: "break-all",
                  lineHeight: 1.5,
                }}
              >
                {c.result.length > 300
                  ? `${c.result.slice(0, 300)}…`
                  : c.result}
              </Typography>
            </Box>
          ))}
        </Box>
      </Collapse>
    </Box>
  );
}

interface OverlayProperties {
  dlst: number;
}

function LayerMap({
  layer,
}: {
  layer: GeoJSON.FeatureCollection;
}) {
  const values = layer.features.map(
    (f) =>
      (f.properties as OverlayProperties).dlst
  );

  const colorFor = sequentialScale(
    0,
    Math.min(...values, 0)
  );

  return (
    <Box
      sx={{
        height: 280,
        mt: 1.5,
        borderRadius: 3,
        overflow: "hidden",
        position: "relative",
        border: "1px solid #d7e4e1",
        boxShadow: "0 6px 20px rgba(26,71,62,0.08)",
      }}
    >
      {/* MAP LABEL */}
      <Box
        sx={{
          position: "absolute",
          top: 10,
          left: 10,
          zIndex: 500,
          display: "flex",
          alignItems: "center",
          gap: 0.7,
          px: 1.1,
          py: 0.7,
          borderRadius: 2,
          bgcolor: "rgba(255,255,255,0.93)",
          backdropFilter: "blur(8px)",
          border: "1px solid rgba(214,226,222,0.9)",
          boxShadow: "0 3px 12px rgba(0,0,0,0.08)",
        }}
      >
        <MapRoundedIcon
          sx={{
            fontSize: 17,
            color: "#0b6b5a",
          }}
        />

        <Typography
          variant="caption"
          sx={{
            fontWeight: 800,
            color: "#31534b",
          }}
        >
          AI spatial result
        </Typography>
      </Box>

      {/* MAP */}
      <MapContainer
        center={MUMBAI_CENTER}
        zoom={11}
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

        <LeafletGeoJSON
          data={layer}
          style={(feature) => {
            const dlst =
              (
                feature?.properties as
                  | OverlayProperties
                  | undefined
              )?.dlst ?? 0;

            return {
              fillColor: colorFor(dlst),
              fillOpacity: 0.85,
              color: "#ffffff",
              weight: 0.7,
            };
          }}
        />
      </MapContainer>

      {/* MAP LEGEND */}
      <Box
        sx={{
          position: "absolute",
          bottom: 10,
          right: 10,
          zIndex: 500,
          px: 1.1,
          py: 0.8,
          borderRadius: 2,
          bgcolor: "rgba(255,255,255,0.94)",
          backdropFilter: "blur(8px)",
          border: "1px solid rgba(214,226,222,0.9)",
          boxShadow: "0 3px 12px rgba(0,0,0,0.08)",
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 0.7,
          }}
        >
          <Box
            sx={{
              width: 80,
              height: 7,
              borderRadius: 5,
              background:
                "linear-gradient(90deg, #168563, #e0b82f, #d94747)",
            }}
          />

          <Typography
            variant="caption"
            sx={{
              fontWeight: 700,
              color: "#506863",
            }}
          >
            ΔLST
          </Typography>
        </Box>
      </Box>
    </Box>
  );
}
