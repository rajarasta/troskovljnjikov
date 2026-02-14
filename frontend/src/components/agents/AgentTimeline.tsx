"use client";

import { motion, AnimatePresence } from "framer-motion";
import type { AgentEvent } from "@/lib/types";
import AgentCard from "./AgentCard";

// ── Stagger animation variants ──────────────────────────────────────

const containerVariants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.06,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: -8, scale: 0.97 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring", damping: 20, stiffness: 300 },
  },
  exit: { opacity: 0, scale: 0.95, transition: { duration: 0.15 } },
};

// ── Timeline dot color logic ────────────────────────────────────────

const ACTIVE_TYPES = new Set(["agent_spawn", "agent_progress"]);

function getLineColor(type: string): string {
  return ACTIVE_TYPES.has(type) ? "bg-accent-cyan" : "bg-border-default";
}

function getDotColor(type: string): string {
  return ACTIVE_TYPES.has(type)
    ? "bg-accent-cyan shadow-[0_0_6px_rgba(0,212,255,0.5)]"
    : "bg-text-muted";
}

// ── Component ───────────────────────────────────────────────────────

interface AgentTimelineProps {
  events: AgentEvent[];
}

export default function AgentTimeline({ events }: AgentTimelineProps) {
  // Most recent events at top
  const sortedEvents = [...events].reverse();

  if (sortedEvents.length === 0) {
    return (
      <p className="text-xs text-text-muted px-2 py-4 text-center">
        No agent activity yet
      </p>
    );
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="relative flex flex-col"
    >
      <AnimatePresence mode="popLayout">
        {sortedEvents.map((event, index) => {
          const isLast = index === sortedEvents.length - 1;

          return (
            <motion.div
              key={`${event.timestamp}-${event.agent_id ?? index}`}
              variants={itemVariants}
              layout
              exit="exit"
              className="relative flex gap-3"
            >
              {/* Timeline track: dot + line */}
              <div className="flex flex-col items-center shrink-0 w-4">
                {/* Dot */}
                <div
                  className={`w-2 h-2 rounded-full mt-5 shrink-0 ${getDotColor(event.type)}`}
                />
                {/* Connecting line */}
                {!isLast && (
                  <div
                    className={`w-px flex-1 min-h-[8px] ${getLineColor(event.type)}`}
                  />
                )}
              </div>

              {/* Card */}
              <div className="flex-1 pb-2 min-w-0">
                <AgentCard event={event} />
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </motion.div>
  );
}
