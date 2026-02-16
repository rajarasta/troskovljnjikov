"use client";

import { Activity } from "lucide-react";
import { useAgentStore } from "@/stores/agentStore";

export default function AgentActivityButton() {
  const { events, togglePanel, activeAgents } = useAgentStore();
  const activeCount = activeAgents.size;

  return (
    <button
      onClick={togglePanel}
      className={`
        fixed bottom-4 right-4 z-50 flex items-center gap-2 px-4 py-2 rounded-full
        glass-panel border transition-all duration-200 hover:scale-105 active:scale-95
        ${activeCount > 0 ? "glow-purple border-accent-purple/40" : "border-border-default"}
      `}
    >
      <Activity
        className={`w-4 h-4 ${activeCount > 0 ? "text-accent-purple" : "text-text-muted"}`}
      />
      <span className="text-xs text-text-secondary">
        {activeCount > 0 ? `${activeCount} active` : "Agents"}
      </span>
      {activeCount > 0 && (
        <span className="w-2 h-2 rounded-full bg-accent-purple animate-pulse" />
      )}
      {events.length > 0 && (
        <span className="text-[10px] text-text-muted font-mono">
          {events.length}
        </span>
      )}
    </button>
  );
}
