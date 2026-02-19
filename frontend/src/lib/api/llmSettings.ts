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

export interface EndpointInfo {
  url: string;
  status: "online" | "offline" | "unknown";
  models: string[];
  is_active: boolean;
  last_checked: string | null;
}

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

// ---------------------------------------------------------------------------
// LLM Endpoint Management
// ---------------------------------------------------------------------------

export async function fetchEndpoints(): Promise<{ endpoints: EndpointInfo[] }> {
  return fetchAPI<{ endpoints: EndpointInfo[] }>("/api/llm-settings/endpoints");
}

export async function scanEndpoints(): Promise<{ endpoints: EndpointInfo[] }> {
  return fetchAPI<{ endpoints: EndpointInfo[] }>("/api/llm-settings/endpoints/scan", {
    method: "POST",
  });
}

export async function probeEndpoint(url: string): Promise<{ endpoint: EndpointInfo }> {
  return fetchAPI<{ endpoint: EndpointInfo }>("/api/llm-settings/endpoints/health", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export async function addEndpoint(url: string): Promise<{ endpoints: EndpointInfo[] }> {
  return fetchAPI<{ endpoints: EndpointInfo[] }>("/api/llm-settings/endpoints", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export async function removeEndpoint(url: string): Promise<{ endpoints: EndpointInfo[] }> {
  return fetchAPI<{ endpoints: EndpointInfo[] }>("/api/llm-settings/endpoints", {
    method: "DELETE",
    body: JSON.stringify({ url }),
  });
}

export async function setActiveEndpoint(url: string): Promise<{ active_url: string }> {
  return fetchAPI<{ active_url: string }>("/api/llm-settings/endpoints/active", {
    method: "PUT",
    body: JSON.stringify({ url }),
  });
}
