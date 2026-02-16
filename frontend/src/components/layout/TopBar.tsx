"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Upload, FolderOpen, TreePine, Camera, FlaskConical, ChevronDown, Columns3, Cpu } from "lucide-react";
import { useBoQStore } from "@/stores/boqStore";
import { usePresetStore } from "@/stores/presetStore";
import * as api from "@/lib/api";
import UploadZone from "@/components/upload/UploadZone";
import FileList from "@/components/upload/FileList";
import BoQNavigator from "@/components/boq/BoQNavigator";
import PhotoUpload from "@/components/photos/PhotoUpload";
import LlmControlBoard from "@/components/layout/LlmControlBoard";

const ALL_OPTIONAL_COLUMNS = [
  { key: "material_price", label: "Cijena mat." },
  { key: "labor_price", label: "Cijena rada" },
  { key: "notes", label: "Bilješke" },
  { key: "drawing", label: "Crtež" },
  { key: "llm_response", label: "LLM" },
  { key: "status", label: "Status" },
  { key: "full_description", label: "Puni opis" },
  { key: "item_type", label: "Tip" },
];

type PopoverKey = "upload" | "files" | "navigator" | "photos" | "preset" | "llm" | null;

export default function TopBar({ isConnected }: { isConnected: boolean }) {
  const [openPopover, setOpenPopover] = useState<PopoverKey>(null);
  const { items, selectedRow, selectRow } = useBoQStore();
  const filesCount = useBoQStore((s) => s.files.length);
  const selectedFileId = useBoQStore((s) => s.selectedFileId);
  const barRef = useRef<HTMLDivElement>(null);
  const [isAnalyzingPhoto, setIsAnalyzingPhoto] = useState(false);

  const {
    presets,
    activePresetId,
    loadPresets,
    selectPreset,
    toggleColumn,
    getActiveColumns,
  } = usePresetStore();

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

  // Close popover on click outside the entire top bar (buttons + popover)
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (barRef.current && !barRef.current.contains(e.target as Node)) {
        setOpenPopover(null);
      }
    }
    if (openPopover) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [openPopover]);

  const toggle = (key: PopoverKey) =>
    setOpenPopover((prev) => (prev === key ? null : key));

  const handleAnalyzePhoto = useCallback((file: File) => {
    setIsAnalyzingPhoto(true);
    // TODO: call backend vision agent API
    const _url = URL.createObjectURL(file);
    setTimeout(() => {
      setIsAnalyzingPhoto(false);
    }, 2000);
  }, []);

  const buttonClass = (key: PopoverKey) => `
    flex items-center gap-1.5 px-3 py-1.5 rounded text-xs transition-all duration-150
    ${openPopover === key
      ? "bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/20"
      : "text-text-muted hover:text-text-secondary hover:bg-bg-hover border border-transparent"
    }
  `;

  return (
    <div ref={barRef} className="relative flex items-center gap-2 px-4 py-2 border-b border-border-default bg-bg-secondary/50">
      {/* Buttons */}
      <button onClick={() => toggle("upload")} className={buttonClass("upload")}>
        <Upload className="w-3.5 h-3.5" /> Upload
      </button>
      <button onClick={() => toggle("files")} className={buttonClass("files")}>
        <FolderOpen className="w-3.5 h-3.5" /> Files
        <span className="text-[10px] text-text-muted">
          ({filesCount})
        </span>
      </button>
      <button onClick={() => toggle("navigator")} className={buttonClass("navigator")}>
        <TreePine className="w-3.5 h-3.5" /> Navigator
      </button>
      <button onClick={() => toggle("photos")} className={buttonClass("photos")}>
        <Camera className="w-3.5 h-3.5" /> Photos
      </button>
      <button onClick={() => toggle("llm")} className={buttonClass("llm")}>
        <Cpu className="w-3.5 h-3.5" /> LLM
      </button>

      <div className="w-px h-4 bg-border-default" />
      <button
        onClick={() => useBoQStore.getState().loadMockData()}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs text-accent-amber hover:bg-accent-amber/10 border border-transparent hover:border-accent-amber/20 transition-all duration-150"
      >
        <FlaskConical className="w-3.5 h-3.5" /> Demo
      </button>

      <div className="w-px h-4 bg-border-default" />

      {/* Preset dropdown */}
      <button onClick={() => toggle("preset")} className={buttonClass("preset")}>
        <Columns3 className="w-3.5 h-3.5" />
        {presets.find((p) => p.id === activePresetId)?.name ?? "Preset"}
        <ChevronDown className="w-3 h-3 opacity-50" />
      </button>

      {/* Column toggle chips */}
      <span className="text-[10px] text-text-muted uppercase tracking-wider">Stupci:</span>
      <div className="flex items-center gap-1 overflow-x-auto">
        {ALL_OPTIONAL_COLUMNS.map((col) => {
          const isActive = activeColumns.includes(col.key);
          return (
            <button
              key={col.key}
              onClick={() => toggleColumn(col.key)}
              className={`px-2 py-0.5 rounded-full text-[10px] whitespace-nowrap transition-colors ${
                isActive
                  ? "bg-accent-cyan/20 text-accent-cyan border border-accent-cyan/30"
                  : "bg-bg-tertiary text-text-muted hover:text-text-secondary border border-transparent"
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
        className="shrink-0 px-3 py-1 text-xs rounded transition-colors bg-status-success/20 text-status-success hover:bg-status-success/30 disabled:bg-bg-tertiary disabled:text-text-muted border border-transparent hover:border-status-success/30"
      >
        Export XLSX
      </button>

      {/* Spacer + connection status */}
      <div className="flex-1" />
      <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? "bg-status-success" : "bg-status-danger"}`} />
      <span className="text-[10px] text-text-muted font-mono uppercase tracking-wider">
        {isConnected ? "Connected" : "Disconnected"}
      </span>

      {/* Popover panel */}
      {openPopover && openPopover !== "preset" && openPopover !== "llm" && (
        <div className="absolute top-full left-0 mt-1 z-50 w-80 max-h-96 overflow-y-auto glass-panel border border-border-default rounded-lg shadow-xl p-3">
          {openPopover === "upload" && <UploadZone />}
          {openPopover === "files" && <FileList />}
          {openPopover === "navigator" && (
            <BoQNavigator
              items={items}
              selectedId={selectedRow?.id ?? null}
              onSelect={(item) => { selectRow(item); setOpenPopover(null); }}
            />
          )}
          {openPopover === "photos" && (
            <PhotoUpload
              onAnalyze={handleAnalyzePhoto}
              isAnalyzing={isAnalyzingPhoto}
            />
          )}
        </div>
      )}

      {/* LLM control board popover */}
      {openPopover === "llm" && (
        <div className="absolute top-full left-0 mt-1 z-50 w-96 glass-panel border border-border-default rounded-lg shadow-xl p-3">
          <LlmControlBoard />
        </div>
      )}

      {/* Preset popover */}
      {openPopover === "preset" && (
        <div className="absolute top-full mt-1 z-50 w-48 glass-panel border border-border-default rounded-lg shadow-xl py-1" style={{ left: "auto", right: "auto" }}>
          <div className="px-3 py-1.5 text-[10px] text-text-muted uppercase tracking-wider">Odaberi preset</div>
          {presets.map((p) => (
            <button
              key={p.id}
              onClick={() => { selectPreset(p.id); setOpenPopover(null); }}
              className={`w-full text-left px-3 py-1.5 text-xs transition-colors ${
                p.id === activePresetId
                  ? "bg-accent-cyan/10 text-accent-cyan"
                  : "text-text-secondary hover:bg-bg-hover"
              }`}
            >
              {p.name}
              {p.description && (
                <span className="block text-[10px] text-text-muted">{p.description}</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
