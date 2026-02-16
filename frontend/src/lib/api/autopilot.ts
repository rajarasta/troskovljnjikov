import type { MatchResponse } from "../types";
import { fetchAPI } from "./client";

/** Fetch resolved match results from autopilot cache (skips ChromaDB query) */
export async function fetchCachedMatches(
  fileId: string,
  itemId: string,
  quantity?: number,
): Promise<MatchResponse> {
  const params = new URLSearchParams();
  if (quantity !== undefined) params.set("quantity", String(quantity));
  const query = params.toString();
  return fetchAPI<MatchResponse>(
    `/api/autopilot/${fileId}/matches-resolved/${encodeURIComponent(itemId)}${query ? `?${query}` : ""}`,
  );
}
