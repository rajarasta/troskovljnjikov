"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Upload, FolderOpen, TreePine, Camera, FlaskConical } from "lucide-react";
import { useBoQStore } from "@/stores/boqStore";
import UploadZone from "@/components/upload/UploadZone";
import FileList from "@/components/upload/FileList";
import BoQNavigator from "@/components/boq/BoQNavigator";
import PhotoUpload from "@/components/photos/PhotoUpload";

type PopoverKey = "upload" | "files" | "navigator" | "photos" | null;

export default function TopBar({ isConnected }: { isConnected: boolean }) {
  const [openPopover, setOpenPopover] = useState<PopoverKey>(null);
  const { items, selectedRow, selectRow } = useBoQStore();
  const popoverRef = useRef<HTMLDivElement>(null);
  const [isAnalyzingPhoto, setIsAnalyzingPhoto] = useState(false);

  // Close popover on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
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
    <div className="relative flex items-center gap-2 px-4 py-2 border-b border-border-default bg-bg-secondary/50">
      {/* Buttons */}
      <button onClick={() => toggle("upload")} className={buttonClass("upload")}>
        <Upload className="w-3.5 h-3.5" /> Upload
      </button>
      <button onClick={() => toggle("files")} className={buttonClass("files")}>
        <FolderOpen className="w-3.5 h-3.5" /> Files
        <span className="text-[10px] text-text-muted">
          ({useBoQStore.getState().files.length})
        </span>
      </button>
      <button onClick={() => toggle("navigator")} className={buttonClass("navigator")}>
        <TreePine className="w-3.5 h-3.5" /> Navigator
      </button>
      <button onClick={() => toggle("photos")} className={buttonClass("photos")}>
        <Camera className="w-3.5 h-3.5" /> Photos
      </button>

      <div className="w-px h-4 bg-border-default" />
      <button
        onClick={() => useBoQStore.getState().loadMockData()}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs text-accent-amber hover:bg-accent-amber/10 border border-transparent hover:border-accent-amber/20 transition-all duration-150"
      >
        <FlaskConical className="w-3.5 h-3.5" /> Demo
      </button>

      {/* Spacer + connection status */}
      <div className="flex-1" />
      <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? "bg-status-success" : "bg-status-danger"}`} />
      <span className="text-[10px] text-text-muted font-mono uppercase tracking-wider">
        {isConnected ? "Connected" : "Disconnected"}
      </span>

      {/* Popover panel */}
      {openPopover && (
        <div
          ref={popoverRef}
          className="absolute top-full left-0 mt-1 z-50 w-80 max-h-96 overflow-y-auto glass-panel border border-border-default rounded-lg shadow-xl p-3"
        >
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
    </div>
  );
}
