import Shell from "@/components/Shell";
import { supabase } from "@/lib/supabase";

export const revalidate = 0;

// The console shell. The landing page sits outside this group so it can own the
// whole viewport rather than living inside a sidebar.
//
// The sidebar's pillar tree is fetched here, on the server, rather than in the
// browser: the browser bundle only sees env vars present at build time, and a
// menu that silently renders empty is worse than one fetched where the
// credentials already are.
export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const [branches, topics] = await Promise.all([
    supabase.from("nodes").select("id,name,sort").eq("kind", "branch").order("sort"),
    supabase.from("topics").select("id,name,node_id").is("retired_at", null).order("id"),
  ]);
  return <Shell tree={{ branches: branches.data ?? [], topics: topics.data ?? [] }}>{children}</Shell>;
}
