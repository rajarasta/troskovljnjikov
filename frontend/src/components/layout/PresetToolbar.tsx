"use client";

import { useEffect } from "react";
import { usePresetStore } from "@/stores/presetStore";
import { useBoQStore } from "@/stores/boqStore";
import * as api from "@/lib/api";

const ALL_OPTIONAL_COLUMNS = [
  { key: "material_price", label: "Cijena mat." },
  { key: "labor_price", label: "Cijena rada" },
  { key: "notes", label: "Bilje\u0161ke" },
  { key: "drawing", label: "Crte\u017e" },
  { key: "llm_response", label: "LLM" },
  { key: "status", label: "Status" },
  { key: "full_description", label: "Puni opis" },
  { key: "item_type", label: "Tip" },
];

export function PresetToolbar() {
  const {
    presets,
    activePresetId,
    loadPresets,
    selectPreset,
    toggleColumn,
    getActiveColumns,
  } = usePresetStore();
  const selectedFileId = useBoQStore((s) => s.selectedFileId);

  useEffect(() => {
    loadPresets();
  }, [loadPresets]);

  const activeColumns = getActiveColumns();

  const handleExport = () => {
    if (!selectedFileId) return;
    const { columnOverrides } = usePresetStore.getState();
    const url = api.getCanonicalExportUrl(
      selectedFileId,
      activePresetId,
      [...columnOverrides.include],
      [...columnOverrides.exclude],
    );
    window.open(url, "_blank");
  };

  return (
    <div className="flex items-center gap-3 px-3 py-2 bg-zinc-900 border-b border-zinc-800 text-sm">
      <label className="text-zinc-400 shrink-0">Preset:</label>
      <select
        value={activePresetId}
        onChange={(e) => selectPreset(e.target.value)}
        className="bg-zinc-800 text-zinc-100 border border-zinc-700 rounded px-2 py-1 text-sm"
      >
        {presets.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>

      <div className="flex items-center gap-1 overflow-x-auto">
        {ALL_OPTIONAL_COLUMNS.map((col) => {
          const isActive = activeColumns.includes(col.key);
          return (
            <button
              key={col.key}
              onClick={() => toggleColumn(col.key)}
              className={`px-2 py-0.5 rounded-full text-xs whitespace-nowrap transition-colors ${
                isActive
                  ? "bg-blue-600 text-white"
                  : "bg-zinc-800 text-zinc-500 hover:text-zinc-300"
              }`}
            >
              {isActive ? "" : "+"}{col.label}
            </button>
          );
        })}
      </div>

      <button
        onClick={handleExport}
        disabled={!selectedFileId}
        className="ml-auto shrink-0 px-3 py-1 bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded text-sm transition-colors"
      >
        Export XLSX
      </button>
    </div>
  );
}
