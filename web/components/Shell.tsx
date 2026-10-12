"use client";
import Sidebar, { type PillarTreeData } from "./Sidebar";
import CommandK from "./CommandK";

export default function Shell({ children, tree }: { children: React.ReactNode; tree?: PillarTreeData }) {
  return (
    <div className="shell">
      <Sidebar tree={tree} onAsk={() => window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }))} />
      <main className="main">{children}</main>
      <CommandK />
    </div>
  );
}
