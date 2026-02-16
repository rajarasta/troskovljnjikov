import { API_URL } from "./client";

export function getExportUrl(fileId: string, format: "xlsx" | "pdf"): string {
  return `${API_URL}/api/export/${fileId}/${format}`;
}

export function getCanonicalExportUrl(
  fileId: string,
  presetId: string,
  include: string[] = [],
  exclude: string[] = [],
): string {
  const params = new URLSearchParams({ preset_id: presetId });
  if (include.length) params.set("include", include.join(","));
  if (exclude.length) params.set("exclude", exclude.join(","));
  return `${API_URL}/api/export/${fileId}/xlsx?${params}`;
}
