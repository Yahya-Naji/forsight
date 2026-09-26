"use client";
import Sidebar from "./Sidebar";
import CommandK from "./CommandK";

export default function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="shell">
      <Sidebar onAsk={() => window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }))} />
      <main className="main">{children}</main>
      <CommandK />
    </div>
  );
}
