import Shell from "@/components/Shell";

// The console shell. The landing page sits outside this group so it can own the
// whole viewport rather than living inside a sidebar.
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <Shell>{children}</Shell>;
}
