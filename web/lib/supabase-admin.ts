import { createClient } from "@supabase/supabase-js";

// SERVER ONLY. The service key bypasses RLS, so this module must never be
// imported from a client component — anon has SELECT-only policies, which is
// precisely why recording a run needs this client rather than lib/supabase.
//
// `??` is not enough here: an env var present but EMPTY ("SUPABASE_SERVICE_KEY=")
// is a string, so it slips past a nullish check and createClient throws at module
// load, breaking `next build`. Treat blank as missing.
const env = (name: string) => {
  const v = process.env[name];
  return v && v.trim() ? v.trim() : undefined;
};

const url = env("SUPABASE_URL") ?? env("NEXT_PUBLIC_SUPABASE_URL");
const key = env("SUPABASE_SERVICE_KEY");

export const supabaseAdmin = createClient(
  url ?? "https://placeholder.supabase.co",
  key ?? "service-key-placeholder",
  { auth: { persistSession: false } }
);

export const hasServiceKey = () => Boolean(url && key);
