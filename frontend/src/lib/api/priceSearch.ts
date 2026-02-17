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
  return fetchAPI(`/api/price-search/${encodeURIComponent(itemId)}`, {
    method: "POST",
    body: JSON.stringify(options ?? {}),
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
  return fetchAPI("/api/price-search/batch", {
    method: "POST",
    body: JSON.stringify({ item_ids: itemIds, ...options }),
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
