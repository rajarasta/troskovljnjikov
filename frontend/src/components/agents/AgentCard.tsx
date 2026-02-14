"use client";

import { motion } from "framer-motion";
import {
  FileText,
  GitCompare,
  DollarSign,
  Eye,
  Loader2,
  CheckCircle2,
  XCircle,
  Bot,
} from "lucide-react";
import type { AgentEvent } from "@/lib/types";

// ── Agent type -> icon & color mapping ──────────────────────────────

const AGENT_CONFIG: Record<
  string,
  { icon: React.ElementType; color: string; bgColor: string }
> = {
  parser: {
    icon: FileText,
    color: "text-accent-blue",
    bgColor: "bg-accent-blue/10",
  },
  matcher: {
    icon: GitCompare,
    color: "text-accent-purple",
    bgColor: "bg-accent-purple/10",
  },
  pricer: {
    icon: DollarSign,
    color: "text-accent-cyan",
    bgColor: "bg-accent-cyan/10",
  },
  vision: {
    icon: Eye,
    color: "text-status-success",
    bgColor: "bg-status-success/10",
  },
};

const ACTIVE_TYPES = new Set(["agent_spawn", "agent_progress"]);
const COMPLETE_TYPES = new Set(["agent_complete"]);
const ERROR_TYPES = new Set(["agent_error"]);

// ── Status indicator ────────────────────────────────────────────────

function StatusIndicator({ type }: { type: string }) {
  if (ACTIVE_TYPES.has(type)) {
    return <Loader2 className="w-3.5 h-3.5 text-accent-cyan animate-spin shrink-0" />;
  }
  if (COMPLETE_TYPES.has(type)) {
    return <CheckCircle2 className="w-3.5 h-3.5 text-status-success shrink-0" />;
  }
  if (ERROR_TYPES.has(type)) {
    return <XCircle className="w-3.5 h-3.5 text-status-danger shrink-0" />;
  }
  return <Bot className="w-3.5 h-3.5 text-text-muted shrink-0" />;
}

// ── Component ───────────────────────────────────────────────────────

interface AgentCardProps {
  event: AgentEvent;
}

export default function AgentCard({ event }: AgentCardProps) {
  const agentType = event.agent_type ?? "unknown";
  const config = AGENT_CONFIG[agentType] ?? {
    icon: Bot,
    color: "text-text-muted",
    bgColor: "bg-bg-tertiary",
  };
  const Icon = config.icon;

  const progressMessage =
    typeof event.payload?.message === "string"
      ? event.payload.message
      : typeof event.payload?.progress === "string"
        ? event.payload.progress
        : null;

  const formattedTime = new Date(event.timestamp).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="glass-panel flex items-center gap-2.5 px-3 py-2 min-h-[48px]"
    >
      {/* Agent type icon */}
      <div className={`p-1 rounded ${config.bgColor} shrink-0`}>
        <Icon className={`w-3.5 h-3.5 ${config.color}`} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className={`text-xs font-medium ${config.color} capitalize`}>
            {agentType}
          </span>
          {event.agent_id && (
            <span className="text-[10px] text-text-muted font-mono truncate">
              {event.agent_id}
            </span>
          )}
        </div>
        {progressMessage && (
          <p className="text-[11px] text-text-secondary truncate mt-0.5">
            {progressMessage}
          </p>
        )}
      </div>

      {/* Status + timestamp */}
      <div className="flex items-center gap-2 shrink-0">
        <StatusIndicator type={event.type} />
        <span className="text-[10px] text-text-muted font-mono whitespace-nowrap">
          {formattedTime}
        </span>
      </div>
    </motion.div>
  );
}
