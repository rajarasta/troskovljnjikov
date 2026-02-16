import type { BoQFile, BoQItem } from "../types";
import { API_URL, fetchAPI } from "./client";

interface UploadResponse {
  file_id: string;
  file_name: string;
  sheets: unknown[];
  item_count: number;
}

export async function uploadFile(file: File): Promise<{ fileId: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const url = `${API_URL}/api/upload`;
  const res = await fetch(url, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errorBody = await res.text().catch(() => "Upload failed");
    throw new Error(`Upload error ${res.status}: ${errorBody}`);
  }

  const data = (await res.json()) as UploadResponse;
  return { fileId: data.file_id };
}

export async function fetchFiles(): Promise<BoQFile[]> {
  return fetchAPI<BoQFile[]>("/api/files");
}

export async function fetchFileItems(fileId: string): Promise<BoQItem[]> {
  return fetchAPI<BoQItem[]>(`/api/files/${fileId}/items`);
}

export async function deleteFile(fileId: string): Promise<void> {
  await fetchAPI<void>(`/api/files/${fileId}`, { method: "DELETE" });
}

export async function fetchItems(
  fileId?: string,
  limit?: number,
  offset?: number
): Promise<BoQItem[]> {
  const params = new URLSearchParams();
  if (fileId) params.set("file_id", fileId);
  if (limit !== undefined) params.set("limit", String(limit));
  if (offset !== undefined) params.set("offset", String(offset));

  const query = params.toString();
  return fetchAPI<BoQItem[]>(`/api/items${query ? `?${query}` : ""}`);
}

/** Fetch IWorkbookData JSON for Univer rendering */
export async function fetchWorkbookData(fileId: string): Promise<Record<string, unknown>> {
  return fetchAPI<Record<string, unknown>>(`/api/files/${fileId}/workbook-data`);
}
