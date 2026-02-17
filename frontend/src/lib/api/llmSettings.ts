import { fetchAPI } from "./client";

export interface AgentSettings {
  label: string;
  category: string;
  enabled: boolean;
  temperature: number;
  knowledge_prompt: string;
  instruction_prompt: string;
  is_default: boolean;
}

export type AllAgentSettings = Record<string, AgentSettings>;

export async function fetchLlmSettings(): Promise<AllAgentSettings> {
  return fetchAPI<AllAgentSettings>("/api/llm-settings");
}

export async function updateLlmSettings(
  agentId: string,
  data: {
    temperature?: number;
    knowledge_prompt?: string;
    instruction_prompt?: string;
    enabled?: boolean;
  },
): Promise<AgentSettings> {
  return fetchAPI<AgentSettings>(`/api/llm-settings/${agentId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function resetLlmSettings(agentId: string): Promise<AgentSettings> {
  return fetchAPI<AgentSettings>(`/api/llm-settings/${agentId}/reset`, {
    method: "POST",
  });
}

// ---------------------------------------------------------------------------
// Global model selection
// ---------------------------------------------------------------------------

export interface AvailableModelsResponse {
  models: string[];
  current: string;
}

export async function fetchAvailableModels(): Promise<AvailableModelsResponse> {
  return fetchAPI<AvailableModelsResponse>("/api/llm-settings/global/models");
}

export async function setCurrentModel(modelName: string): Promise<{ model: string }> {
  return fetchAPI<{ model: string }>("/api/llm-settings/global/model", {
    method: "PUT",
    body: JSON.stringify({ model_name: modelName }),
  });
}
