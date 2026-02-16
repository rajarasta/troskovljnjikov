import { create } from "zustand";
import type { PipelineStage } from "@/lib/types";

interface PipelineState {
  // ── State ───────────────────────────────────────────────────────
  stage: PipelineStage | null;
  progress: number;
  isRunning: boolean;

  // ── Actions ─────────────────────────────────────────────────────
  setStage: (stage: PipelineStage, progress: number) => void;
  reset: () => void;
}

export const usePipelineStore = create<PipelineState>((set) => ({
  stage: null,
  progress: 0,
  isRunning: false,

  setStage: (stage: PipelineStage, progress: number) => {
    set({ stage, progress, isRunning: true });
  },

  reset: () => {
    set({ stage: null, progress: 0, isRunning: false });
  },
}));
