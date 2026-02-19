"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Check } from "lucide-react";
import { usePipelineStore } from "@/stores/pipelineStore";
import { useAutopilotStore } from "@/stores/autopilotStore";
import { useBoQStore } from "@/stores/boqStore";
import type { PipelineStage } from "@/lib/types";

const STAGES: { key: PipelineStage; label: string }[] = [
  { key: "upload", label: "Upload" },
  { key: "parse", label: "Parse" },
  { key: "index", label: "Index" },
  { key: "match", label: "Match" },
  { key: "suggest", label: "Suggest" },
  { key: "review", label: "Review" },
];

function getStageIndex(stage: PipelineStage | null): number {
  if (!stage) return -1;
  return STAGES.findIndex((s) => s.key === stage);
}

type StageStatus = "completed" | "active" | "future";

function getStageStatus(
  stageIdx: number,
  activeIdx: number,
  progress: number
): StageStatus {
  if (stageIdx < activeIdx) return "completed";
  if (stageIdx === activeIdx) {
    return progress >= 100 && stageIdx < STAGES.length - 1
      ? "completed"
      : "active";
  }
  return "future";
}

function getConnectorFill(
  fromIdx: number,
  activeIdx: number,
  progress: number
): number {
  if (fromIdx < activeIdx) return 1;
  if (fromIdx === activeIdx) return Math.min(progress / 100, 1);
  return 0;
}

function StageNode({
  label,
  status,
}: {
  label: string;
  status: StageStatus;
}) {
  return (
    <div className="flex items-center gap-1.5 shrink-0">
      <div className="relative flex items-center justify-center">
        {status === "completed" && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="w-5 h-5 rounded-full bg-status-success flex items-center justify-center"
          >
            <Check className="w-3 h-3 text-bg-primary" strokeWidth={3} />
          </motion.div>
        )}
        {status === "active" && (
          <motion.div
            initial={{ scale: 0.6, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="relative w-6 h-6 flex items-center justify-center"
          >
            <motion.div
              animate={{ opacity: [0.4, 0.8, 0.4] }}
              transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              className="absolute inset-0 rounded-full bg-accent-cyan/20"
            />
            <div className="w-3.5 h-3.5 rounded-full bg-accent-cyan glow-cyan" />
            <motion.div
              animate={{ scale: [1, 1.6, 1], opacity: [1, 0, 1] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
              className="absolute w-1.5 h-1.5 rounded-full bg-accent-cyan"
            />
          </motion.div>
        )}
        {status === "future" && (
          <div className="w-5 h-5 rounded-full border border-border-default bg-transparent" />
        )}
      </div>
      <span
        className={`text-[10px] uppercase tracking-wider font-medium transition-colors duration-200 ${
          status === "active"
            ? "text-accent-cyan"
            : status === "completed"
              ? "text-status-success"
              : "text-text-muted"
        }`}
      >
        {label}
      </span>
    </div>
  );
}

function Connector({ fill }: { fill: number }) {
  return (
    <div className="flex-1 h-[2px] min-w-[16px] max-w-[48px] bg-border-default rounded-full overflow-hidden mx-1">
      <motion.div
        className="h-full bg-accent-cyan rounded-full"
        initial={{ width: 0 }}
        animate={{ width: `${fill * 100}%` }}
        transition={{ duration: 0.4, ease: "easeOut" }}
      />
    </div>
  );
}

// ── Autopilot progress bar ───────────────────────────────────────────

function AutopilotBar() {
  const selectedFileId = useBoQStore((s) => s.selectedFileId);
  const status = useAutopilotStore((s) => selectedFileId ? s.status[selectedFileId] : undefined);
  const progress = useAutopilotStore((s) => selectedFileId ? s.progress[selectedFileId] : undefined);
  const stats = useAutopilotStore((s) => selectedFileId ? s.completionStats[selectedFileId] : undefined);

  if (!selectedFileId || (!status && !stats)) return null;

  // Show completion summary
  if (status === "done" && stats) {
    return (
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel px-4 py-2 flex items-center justify-center gap-4"
        style={{ height: 36 }}
      >
        <span className="text-[10px] font-medium text-status-success flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-status-success inline-block" />
          {stats.high_confidence} auto-priced
        </span>
        <span className="text-[10px] font-medium text-status-warning flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-status-warning inline-block" />
          {stats.medium_confidence} need review
        </span>
        <span className="text-[10px] font-medium text-status-danger flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-status-danger inline-block" />
          {stats.low_confidence} no match
        </span>
      </motion.div>
    );
  }

  // Show progress bar during processing
  if (status && status !== "idle" && status !== "error") {
    const current = progress?.current ?? 0;
    const total = progress?.total ?? 1;
    const pct = total > 0 ? Math.round((current / total) * 100) : 0;
    const statusLabel =
      status === "summarizing" ? "Generating summary..." :
      status === "matching" ? `Matching ${current}/${total} items...` :
      status === "pricing" ? "Computing prices..." : "Processing...";

    return (
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel glow-cyan px-4 py-2 flex items-center gap-3"
        style={{ height: 36 }}
      >
        <div className="flex-1 h-1.5 bg-border-default rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-accent-cyan rounded-full"
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
        <span className="text-[10px] text-text-muted whitespace-nowrap">{statusLabel}</span>
      </motion.div>
    );
  }

  return null;
}

// ── Main export ───────────────────────────────────────────────────────

export default function PipelineBar() {
  const { stage, progress, isRunning } = usePipelineStore();

  // Show classic pipeline stages if running
  if (isRunning && stage) {
    const activeIdx = getStageIndex(stage);
    return (
      <AnimatePresence>
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="glass-panel glow-cyan px-4 py-2 flex items-center justify-center gap-0"
          style={{ height: 40 }}
        >
          {STAGES.map((s, idx) => {
            const status = getStageStatus(idx, activeIdx, progress);
            return (
              <div key={s.key} className="flex items-center">
                <StageNode label={s.label} status={status} />
                {idx < STAGES.length - 1 && (
                  <Connector fill={getConnectorFill(idx, activeIdx, progress)} />
                )}
              </div>
            );
          })}
        </motion.div>
      </AnimatePresence>
    );
  }

  // Otherwise show autopilot progress/summary
  return <AutopilotBar />;
}
