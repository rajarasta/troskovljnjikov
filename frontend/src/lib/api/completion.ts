import { fetchAPI } from "./client";

interface CompletionContext {
  item_number: string | null;
  description: string;
}

export async function suggestCompletion(
  prefix: string,
  context: CompletionContext[],
  signal?: AbortSignal,
): Promise<{ suggestion: string }> {
  return fetchAPI<{ suggestion: string }>("/api/suggest/complete", {
    method: "POST",
    body: JSON.stringify({ prefix, context }),
    signal,
  });
}
