import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

// A dev clone with no Supabase project yet (runbook.md §1.4 is author-action, not automatic)
// must still boot and show every read-only section — only sign-in should be affected, so this
// is `null`, not a thrown error, when the two VITE_ vars aren't set.
export const supabase: SupabaseClient | null =
  url && anonKey ? createClient(url, anonKey) : null;
