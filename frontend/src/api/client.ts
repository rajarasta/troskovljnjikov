import type { ParsedBoQ, LogicalUnit } from './types';

const BASE = '/api';

export async function uploadExcel(file: File): Promise<ParsedBoQ> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${BASE}/upload`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
  return res.json();
}

export async function listUnits(): Promise<LogicalUnit[]> {
  const res = await fetch(`${BASE}/units`);
  if (!res.ok) throw new Error(`Failed to list units: ${res.statusText}`);
  return res.json();
}

export async function getUnit(unitId: string): Promise<LogicalUnit> {
  const res = await fetch(`${BASE}/units/${unitId}`);
  if (!res.ok) throw new Error(`Failed to get unit: ${res.statusText}`);
  return res.json();
}

export async function importHistoric(file: File): Promise<{ imported_count: number }> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${BASE}/historic/import`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`Import failed: ${res.statusText}`);
  return res.json();
}

export async function saveOutput(
  unitId: string,
  lineUpdates: Array<{ item_number: string; unit_price: number; accepted: boolean }>
): Promise<void> {
  const res = await fetch(`${BASE}/output/${unitId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ line_updates: lineUpdates }),
  });
  if (!res.ok) throw new Error(`Save failed: ${res.statusText}`);
}
