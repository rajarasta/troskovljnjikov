import { create } from "zustand";
import type { Preset } from "@/lib/types";
import * as api from "@/lib/api";

const GROUP_COLUMNS: Record<string, string[]> = {
  core: ["item_number", "description", "unit", "quantity", "unit_price", "total"],
  mat_rad: ["material_price", "labor_price", "material_total", "labor_total"],
  multi_qty: [],
  annotation: ["notes", "drawing", "llm_response"],
  status: ["status", "updated_at"],
  meta: ["full_description", "parent_item_number", "item_type"],
};

interface PresetState {
  presets: Preset[];
  activePresetId: string;
  columnOverrides: { include: Set<string>; exclude: Set<string> };
  isLoading: boolean;

  loadPresets: () => Promise<void>;
  selectPreset: (id: string) => void;
  toggleColumn: (columnKey: string) => void;
  resetToPreset: () => void;
  saveAsNewPreset: (name: string) => Promise<void>;
  getActiveColumns: () => string[];
}

export const usePresetStore = create<PresetState>((set, get) => ({
  presets: [],
  activePresetId: "simple",
  columnOverrides: { include: new Set(), exclude: new Set() },
  isLoading: false,

  loadPresets: async () => {
    set({ isLoading: true });
    try {
      const presets = await api.fetchPresets();
      set({ presets, isLoading: false });
    } catch {
      set({ isLoading: false });
    }
  },

  selectPreset: (id: string) => {
    set({
      activePresetId: id,
      columnOverrides: { include: new Set(), exclude: new Set() },
    });
  },

  toggleColumn: (columnKey: string) => {
    const { columnOverrides, activePresetId, presets } = get();
    const preset = presets.find((p) => p.id === activePresetId);
    if (!preset) return;

    const presetColumns = new Set(
      preset.groups.flatMap((g) => GROUP_COLUMNS[g] ?? []),
    );
    const newInclude = new Set(columnOverrides.include);
    const newExclude = new Set(columnOverrides.exclude);

    if (presetColumns.has(columnKey)) {
      if (newExclude.has(columnKey)) {
        newExclude.delete(columnKey);
      } else {
        newExclude.add(columnKey);
      }
    } else {
      if (newInclude.has(columnKey)) {
        newInclude.delete(columnKey);
      } else {
        newInclude.add(columnKey);
      }
    }

    set({ columnOverrides: { include: newInclude, exclude: newExclude } });
  },

  resetToPreset: () => {
    set({ columnOverrides: { include: new Set(), exclude: new Set() } });
  },

  saveAsNewPreset: async (name: string) => {
    const activeColumns = get().getActiveColumns();
    const groups = Object.entries(GROUP_COLUMNS)
      .filter(([, cols]) => cols.length > 0 && cols.every((c) => activeColumns.includes(c)))
      .map(([group]) => group);

    const preset = await api.createPreset({ name, groups });
    set((s) => ({
      presets: [...s.presets, preset],
      activePresetId: preset.id,
      columnOverrides: { include: new Set(), exclude: new Set() },
    }));
  },

  getActiveColumns: () => {
    const { activePresetId, presets, columnOverrides } = get();
    const preset = presets.find((p) => p.id === activePresetId);
    if (!preset) return GROUP_COLUMNS.core;

    const presetColumns = new Set(
      preset.groups.flatMap((g) => GROUP_COLUMNS[g] ?? []),
    );

    for (const col of columnOverrides.include) presetColumns.add(col);
    for (const col of columnOverrides.exclude) presetColumns.delete(col);

    for (const col of GROUP_COLUMNS.core) presetColumns.add(col);

    return [...presetColumns];
  },
}));
