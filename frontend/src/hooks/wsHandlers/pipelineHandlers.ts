import { usePipelineStore } from "@/stores/pipelineStore";
import type { AgentEvent, PipelineStage } from "@/lib/types";

const PIPELINE_STAGES: PipelineStage[] = [
  "upload", "parse", "index", "match", "suggest", "review",
];

export const pipelineHandlers: Record<string, (event: AgentEvent) => void> = {
  pipeline_stage: (event) => {
    const stage = event.payload?.stage as PipelineStage | undefined;
    const progress = (event.payload?.progress as number) ?? 0;
    if (stage && PIPELINE_STAGES.includes(stage)) {
      usePipelineStore.getState().setStage(stage, progress);
    }
  },

  pipeline_complete: () => {
    usePipelineStore.getState().reset();
  },

  pipeline_error: () => {
    usePipelineStore.getState().reset();
  },
};
