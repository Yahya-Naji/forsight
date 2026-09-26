import { createClient } from "@supabase/supabase-js";

// Anon key only — read access via RLS (migration 010). Never the service key.
// Blank-but-present env vars are treated as missing so `next build` succeeds
// without configuration, as the console is designed to.
const env = (name: string) => {
  const v = process.env[name];
  return v && v.trim() ? v.trim() : undefined;
};

export const supabase = createClient(
  env("NEXT_PUBLIC_SUPABASE_URL") ?? "https://placeholder.supabase.co",
  env("NEXT_PUBLIC_SUPABASE_ANON_KEY") ?? "public-anon-key-placeholder"
);
