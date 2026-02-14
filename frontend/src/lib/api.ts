import type { BoQFile, BoQItem, MatchResponse, ChatMessage } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Generic fetch wrapper ───────────────────────────────────────────

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_URL}${path}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const errorBody = await res.text().catch(() => "Unknown error");
    throw new Error(`API error ${res.status}: ${errorBody}`);
  }

  return res.json() as Promise<T>;
}

// ── File operations ─────────────────────────────────────────────────

export async function uploadFile(file: File): Promise<BoQFile> {
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

  return res.json() as Promise<BoQFile>;
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

// ── Item operations ─────────────────────────────────────────────────

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

// ── Match operations ────────────────────────────────────────────────

export async function matchItems(
  description: string,
  quantity?: number,
  threshold?: number
): Promise<MatchResponse> {
  return fetchAPI<MatchResponse>("/api/match", {
    method: "POST",
    body: JSON.stringify({
      description,
      ...(quantity !== undefined && { quantity }),
      ...(threshold !== undefined && { threshold }),
    }),
  });
}

// ── Chat operations ─────────────────────────────────────────────────

export async function fetchChatHistory(
  itemId: string
): Promise<ChatMessage[]> {
  return fetchAPI<ChatMessage[]>(`/api/chat/${itemId}`);
}

export async function sendChatMessage(
  itemId: string,
  message: string
): Promise<ChatMessage> {
  return fetchAPI<ChatMessage>(`/api/chat/${itemId}`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}
