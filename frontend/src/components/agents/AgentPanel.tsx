"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X, Trash2, Activity } from "lucide-react";
import { useAgentStore } from "@/stores/agentStore";
import AgentTimeline from "./AgentTimeline";

// ── Slide-out panel variants ────────────────────────────────────────

const backdropVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
  exit: { opacity: 0 },
};

const panelVariants = {
  hidden: { x: 320 },
  visible: {
    x: 0,
    transition: { type: "spring", damping: 25, stiffness: 200 },
  },
  exit: {
    x: 320,
    transition: { type: "spring", damping: 30, stiffness: 250 },
  },
};

// ── Active agent indicator ──────────────────────────────────────────

function ActiveAgentBadge({
  agentId,
  agentType,
}: {
  agentId: string;
  agentType: string | undefined;
}) {
  return (
    <div className="flex items-center gap-2 px-2.5 py-1.5 rounded bg-accent-purple/10 border border-accent-purple/20">
      <span className="w-1.5 h-1.5 rounded-full bg-accent-purple animate-pulse shrink-0" />
      <span className="text-xs text-accent-purple font-medium capitalize truncate">
        {agentType ?? "agent"}
      </span>
      <span className="text-[10px] text-text-muted font-mono truncate">
        {agentId}
      </span>
    </div>
  );
}

// ── Component ───────────────────────────────────────────────────────

export default function AgentPanel() {
  const { events, activeAgents, isPanelOpen, togglePanel, clearEvents } =
    useAgentStore();

  const activeEntries = Array.from(activeAgents.entries());

  return (
    <AnimatePresence>
      {isPanelOpen && (
        <>
          {/* Semi-transparent backdrop */}
          <motion.div
            key="agent-panel-backdrop"
            variants={backdropVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            onClick={togglePanel}
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
          />

          {/* Slide-out panel */}
          <motion.aside
            key="agent-panel"
            variants={panelVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="fixed top-0 right-0 bottom-0 z-50 w-80 flex flex-col
                       glass-panel border-l border-border-default glow-purple"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border-default shrink-0">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-accent-purple" />
                <h2 className="text-sm font-semibold text-accent-purple">
                  Agent Activity
                </h2>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-text-muted font-mono">
                  {events.length} events
                </span>
                {events.length > 0 && (
                  <button
                    onClick={clearEvents}
                    className="p-1 rounded hover:bg-bg-hover text-text-muted hover:text-status-danger transition-colors"
                    title="Clear all events"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
                <button
                  onClick={togglePanel}
                  className="p-1 rounded hover:bg-bg-hover text-text-muted hover:text-text-primary transition-colors"
                  title="Close panel"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Active agents section */}
            {activeEntries.length > 0 && (
              <div className="px-4 py-2.5 border-b border-border-default shrink-0">
                <p className="text-[10px] text-text-muted uppercase tracking-wider mb-1.5">
                  Active Agents
                </p>
                <div className="flex flex-col gap-1">
                  {activeEntries.map(([agentId, agentEvent]) => (
                    <ActiveAgentBadge
                      key={agentId}
                      agentId={agentId}
                      agentType={agentEvent.agent_type}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Timeline */}
            <div className="flex-1 overflow-y-auto px-3 py-2 min-h-0">
              <AgentTimeline events={events} />
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
