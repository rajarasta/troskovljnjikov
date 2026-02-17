import { fetchAPI } from "./client";
import type { SearchResultData } from "@/lib/types";

export async function triggerPriceSearch(
  itemId: string,
  options?: {
    quantity?: number;
    include_vat?: boolean;
    include_shipping?: boolean;
    description?: string; // For synthetic spreadsheet cells
  }
): Promise<{ status: string; item_id: string }> {
  const payload = options ?? {};
  console.log("🔍📤 SINGLE SEARCH PAYLOAD:", { itemId, payload });
  return fetchAPI(`/api/price-search/${encodeURIComponent(itemId)}`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function triggerBatchPriceSearch(
  itemIds: string[],
  options?: {
    descriptions?: Record<string, string>; // For synthetic spreadsheet cells
    include_vat?: boolean;
    include_shipping?: boolean;
  }
): Promise<{ status: string; item_count: number }> {
  const payload = { item_ids: itemIds, ...options };
  console.log("🔍📤 BATCH SEARCH PAYLOAD:", payload);
  return fetchAPI("/api/price-search/batch", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchSearchResult(
  itemId: string
): Promise<{ status: string; result?: SearchResultData }> {
  return fetchAPI(`/api/price-search/${encodeURIComponent(itemId)}/result`);
}

export async function fetchSearchStatus(
  itemId: string
): Promise<{ status: string }> {
  return fetchAPI(`/api/price-search/${encodeURIComponent(itemId)}/status`);
}
