import type { Preset } from "../types";
import { fetchAPI } from "./client";

export async function fetchPresets(): Promise<Preset[]> {
  return fetchAPI<Preset[]>("/api/presets");
}

export async function createPreset(data: {
  name: string;
  description?: string;
  groups: string[];
}): Promise<Preset> {
  return fetchAPI<Preset>("/api/presets", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deletePreset(presetId: string): Promise<void> {
  await fetchAPI<void>(`/api/presets/${presetId}`, { method: "DELETE" });
}
