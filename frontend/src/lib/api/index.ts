/** Barrel re-export — `import * as api from "@/lib/api"` still works. */

export { API_URL } from "./client";
export { uploadFile, fetchFiles, fetchFileItems, deleteFile, fetchItems, fetchWorkbookData } from "./files";
export { matchItems, matchSelection } from "./match";
export { fetchChatHistory, sendChatMessage, sendChatMessageStreaming, sendChatMessageWithImage, analyzeSelection } from "./chat";
export { getExportUrl, getCanonicalExportUrl } from "./exports";
export { fetchPresets, createPreset, deletePreset } from "./presets";
export { startPipeline } from "./pipeline";
export { fetchCachedMatches } from "./autopilot";
export { suggestCompletion } from "./completion";
export { fetchLlmSettings, updateLlmSettings, resetLlmSettings } from "./llmSettings";
export type { AgentSettings, AllAgentSettings } from "./llmSettings";
