import { fetchAPI, API_URL } from "./client";

export interface DomainInfo {
  id: string;
  domain: string;
  display_name: string;
  search_url_template: string | null;
  fetch_mode: string;
  vat_included: boolean;
  shipping_policy: string;
  currency: string;
  locale: string;
  enabled: boolean;
  is_default: boolean;
}

export interface DomainCreatePayload {
  domain: string;
  display_name: string;
  search_url_template?: string;
  fetch_mode?: string;
  vat_included?: boolean;
  shipping_policy?: string;
  currency?: string;
  locale?: string;
  enabled?: boolean;
}

export async function fetchDomains(): Promise<DomainInfo[]> {
  return fetchAPI<DomainInfo[]>("/api/domains");
}

export async function createDomain(data: DomainCreatePayload): Promise<DomainInfo> {
  return fetchAPI<DomainInfo>("/api/domains", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateDomain(
  id: string,
  data: Partial<DomainCreatePayload>,
): Promise<DomainInfo> {
  return fetchAPI<DomainInfo>(`/api/domains/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteDomain(id: string): Promise<void> {
  // DELETE returns 204 No Content — can't use fetchAPI which calls res.json()
  const res = await fetch(`${API_URL}/api/domains/${id}`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const errorBody = await res.text().catch(() => "Unknown error");
    throw new Error(`API error ${res.status}: ${errorBody}`);
  }
}
