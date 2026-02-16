import type { MatchResponse, SelectionMatchRequest } from "../types";
import { fetchAPI } from "./client";

export async function matchItems(
  description: string,
  quantity?: number,
  threshold?: number,
  fileId?: string,
  startRow?: number,
  endRow?: number,
): Promise<MatchResponse> {
  return fetchAPI<MatchResponse>("/api/match", {
    method: "POST",
    body: JSON.stringify({
      description,
      ...(quantity !== undefined && { quantity }),
      ...(threshold !== undefined && { threshold }),
      ...(fileId !== undefined && { file_id: fileId }),
      ...(startRow !== undefined && { start_row: startRow }),
      ...(endRow !== undefined && { end_row: endRow }),
    }),
  });
}

/** Match multiple items from a selection at once */
export async function matchSelection(
  request: SelectionMatchRequest,
): Promise<MatchResponse> {
  return fetchAPI<MatchResponse>("/api/match", {
    method: "POST",
    body: JSON.stringify({
      description: request.descriptions.join("\n"),
      quantity: request.quantities[0] ?? 0,
      threshold: request.threshold ?? 0.3,
      max_results: request.max_results ?? 20,
    }),
  });
}
