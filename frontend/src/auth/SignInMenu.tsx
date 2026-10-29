import { Box, Button, CircularProgress, TextField, Typography } from "@mui/material";
import { useState, type FormEvent } from "react";

import { useAuth } from "./AuthProvider";

/** Lives in the AppBar (App.tsx). Renders nothing at all when no Supabase project is
 * configured (`available` false) — a dev clone without runbook.md §1.4 done yet still gets a
 * working dashboard, just without a sign-in affordance, rather than a broken control. */
export function SignInMenu() {
  const { session, loading, available, signInWithEmail, signOut } = useAuth();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  if (!available) return null;
  if (loading) return <CircularProgress size={20} color="inherit" />;

  if (session) {
    return (
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
        <Typography variant="body2">{session.user.email}</Typography>
        <Button color="inherit" size="small" onClick={() => void signOut()}>
          Sign out
        </Button>
      </Box>
    );
  }

  if (sent) {
    return <Typography variant="body2">Check your email for a sign-in link.</Typography>;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setSending(true);
    setError(null);
    const { error: signInError } = await signInWithEmail(email);
    setSending(false);
    if (signInError) setError(signInError);
    else setSent(true);
  };

  return (
    <Box
      component="form"
      onSubmit={(event: FormEvent<HTMLFormElement>) => void handleSubmit(event)}
      sx={{ display: "flex", alignItems: "center", gap: 1 }}
    >
      <TextField
        size="small"
        variant="standard"
        placeholder="you@example.com"
        type="email"
        required
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        sx={{ input: { color: "inherit" }, width: 180 }}
      />
      <Button type="submit" color="inherit" size="small" disabled={sending}>
        {sending ? "Sending…" : "Sign in"}
      </Button>
      {error && (
        <Typography variant="caption" color="error.light">
          {error}
        </Typography>
      )}
    </Box>
  );
}
