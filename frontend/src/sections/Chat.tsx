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
import { MapContainer, TileLayer, GeoJSON as LeafletGeoJSON } from "react-leaflet";
import ReactMarkdown from "react-markdown";

import { ApiError } from "../api/client";
import { useAgentChat } from "../api/hooks";
import type { AgentChatResponse, AgentName, AgentToolCall } from "../api/types";
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
  | { role: "error"; message: string; errorCode: string | null };

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
      onSuccess: (response) => setTurns((t) => [...t, { role: "assistant", response }]),
      onError: (err) => {
        const isApiError = err instanceof ApiError;
        setTurns((t) => [
          ...t,
          {
            role: "error",
            message: isApiError ? err.message : "Something went wrong.",
            errorCode: isApiError ? err.errorCode : null,
          },
        ]);
      },
    });
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <Alert severity="info" sx={{ borderRadius: 0 }}>
        The free Gemini tier caps at ~20 requests/day for this project (measured live,
        `BLUEPRINT.md`) — identical questions are cached, but distinct ones spend real quota.
        Each reply can take several seconds; that is the LLM, not a stall.
      </Alert>

      <Box sx={{ flex: 1, overflow: "auto", p: 2, display: "flex", flexDirection: "column", gap: 2 }}>
        {turns.map((turn, i) => (
          <TurnBubble key={i} turn={turn} />
        ))}
        {chat.isPending && (
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <CircularProgress size={16} />
            <Typography variant="body2" sx={{ color: MUTED_INK }}>
              Thinking…
            </Typography>
          </Box>
        )}
      </Box>

      <Box sx={{ display: "flex", gap: 1, p: 2, borderTop: "1px solid #e1e0d9" }}>
        <TextField
          fullWidth
          size="small"
          placeholder="Ask about heat, hotspots, or a what-if scenario…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          disabled={chat.isPending}
        />
        <IconButton color="primary" onClick={send} disabled={chat.isPending || !input.trim()}>
          ➤
        </IconButton>
      </Box>
    </Box>
  );
}

function TurnBubble({ turn }: { turn: Turn }) {
  if (turn.role === "user") {
    return (
      <Paper sx={{ p: 1.5, alignSelf: "flex-end", maxWidth: "70%", bgcolor: "primary.main", color: "primary.contrastText" }}>
        <Typography variant="body2">{turn.text}</Typography>
      </Paper>
    );
  }

  if (turn.role === "error") {
    // The two 503s api-reference.md documents mean different things: not configured at all
    // vs. configured but the upstream call failed (a broken/exhausted key). Both are honest
    // states, not "the app is broken" — say which one happened.
    const label =
      turn.errorCode === "agent_layer_unavailable"
        ? "The agent layer isn't configured (RAG index or GEMINI_API_KEY missing)."
        : turn.errorCode === "agent_upstream_unavailable"
          ? "The LLM call failed upstream — likely the daily quota (~20 req/day) is exhausted."
          : "Couldn't reach the agent.";
    return (
      <Alert severity="warning" sx={{ maxWidth: "80%" }}>
        {label}
        <br />
        <Typography variant="caption" sx={{ color: MUTED_INK }}>
          {turn.message}
        </Typography>
      </Alert>
    );
  }

  const { response } = turn;
  return (
    <Paper variant="outlined" sx={{ p: 1.5, maxWidth: "80%" }}>
      <Chip label={AGENT_LABEL[response.agent]} size="small" sx={{ mb: 1 }} />
      <Box
        sx={{
          fontSize: 14,
          lineHeight: 1.6,
          "& p": { m: 0, mb: 1 },
          "& ul, & ol": { m: 0, mb: 1, pl: 2.5 },
          "& h1, & h2, & h3": { fontSize: "1.05rem", fontWeight: 600, mt: 1.5, mb: 0.5 },
          "& strong": { fontWeight: 600 },
          "& code": { fontFamily: "monospace", fontSize: "0.9em", bgcolor: "#f4f3ec", px: 0.5, borderRadius: 0.5 },
        }}
      >
        <ReactMarkdown>{response.text}</ReactMarkdown>
      </Box>
      {response.tool_calls.length > 0 && <ToolCallList calls={response.tool_calls} />}
      {response.layer && <LayerMap layer={response.layer} />}
    </Paper>
  );
}

function ToolCallList({ calls }: { calls: AgentToolCall[] }) {
  const [open, setOpen] = useState(false);
  return (
    <Box sx={{ mt: 1 }}>
      <Typography
        variant="caption"
        onClick={() => setOpen((o) => !o)}
        sx={{ color: MUTED_INK, cursor: "pointer", textDecoration: "underline" }}
      >
        {open ? "Hide" : "Show"} {calls.length} tool call{calls.length === 1 ? "" : "s"}
      </Typography>
      <Collapse in={open}>
        <Box sx={{ mt: 0.5, display: "flex", flexDirection: "column", gap: 0.5 }}>
          {calls.map((c, i) => (
            <Box key={i} sx={{ bgcolor: "#f9f9f7", p: 1, borderRadius: 1 }}>
              <Typography variant="caption" component="div" sx={{ fontWeight: 600 }}>
                {c.name}({JSON.stringify(c.args)})
              </Typography>
              <Typography
                variant="caption"
                component="div"
                sx={{ color: MUTED_INK, fontFamily: "monospace", wordBreak: "break-all" }}
              >
                {c.result.length > 300 ? `${c.result.slice(0, 300)}…` : c.result}
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

function LayerMap({ layer }: { layer: GeoJSON.FeatureCollection }) {
  const values = layer.features.map((f) => (f.properties as OverlayProperties).dlst);
  const colorFor = sequentialScale(0, Math.min(...values, 0));
  return (
    <Box sx={{ height: 260, mt: 1, borderRadius: 1, overflow: "hidden" }}>
      <MapContainer center={MUMBAI_CENTER} zoom={11} preferCanvas style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        <LeafletGeoJSON
          data={layer}
          style={(feature) => {
            const dlst = (feature?.properties as OverlayProperties | undefined)?.dlst ?? 0;
            return { fillColor: colorFor(dlst), fillOpacity: 0.85, color: "#ffffff", weight: 0.5 };
          }}
        />
      </MapContainer>
    </Box>
  );
}
