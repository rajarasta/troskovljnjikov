import type { ChatMessage } from "../types";
import { API_URL, fetchAPI } from "./client";

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

/** Send a chat message with streaming LLM response via WebSocket tokens. */
export async function sendChatMessageStreaming(
  itemId: string,
  message: string
): Promise<ChatMessage> {
  return fetchAPI<ChatMessage>(`/api/chat/${itemId}/stream`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

export async function sendChatMessageWithImage(
  itemId: string,
  message: string,
  image: File
): Promise<ChatMessage> {
  const formData = new FormData();
  formData.append("message", message);
  formData.append("image", image);

  const url = `${API_URL}/api/chat/${itemId}/image`;
  const res = await fetch(url, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errorBody = await res.text().catch(() => "Unknown error");
    throw new Error(`API error ${res.status}: ${errorBody}`);
  }

  return res.json() as Promise<ChatMessage>;
}

/** Request LLM analysis for a selection */
export async function analyzeSelection(
  selectionId: string,
  itemDescriptions: string[],
  matchContext: string,
  signal?: AbortSignal,
): Promise<ChatMessage> {
  return fetchAPI<ChatMessage>(`/api/chat/${selectionId}`, {
    method: "POST",
    body: JSON.stringify({
      message: `[AUTO-ANALYSIS]\nSelected items:\n${itemDescriptions.join("\n")}\n\nMatch context:\n${matchContext}`,
    }),
    signal,
  });
}
