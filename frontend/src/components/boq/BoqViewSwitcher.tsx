"use client";

import { useRef, useState } from "react";
import { WrapText, Plus, Minus, AArrowUp, AArrowDown } from "lucide-react";
import { useBoQStore } from "@/stores/boqStore";

import SpreadsheetView from "@/components/spreadsheet/SpreadsheetView";
import SheetPreview from "@/components/spreadsheet/SheetPreview";
import RawSheetGrid from "@/components/spreadsheet/RawSheetGrid";
import ExcelView from "@/components/spreadsheet/ExcelView";
import ColumnHeader from "@/components/layout/ColumnHeader";

const MODE_LABELS: Record<string, string> = {
  parsed: "Obrađeno",
  raw: "Sirovo",
  excel: "Excel",
};

export default function BoqViewSwitcher() {
  const { items, selectedFileId, files, isLoading } = useBoQStore();
  const [boqViewMode, setBoqViewMode] = useState<"parsed" | "raw" | "excel">("parsed");
  const [excelWrap, setExcelWrap] = useState(false);
  const [excelZoom, setExcelZoom] = useState(100);
  const [excelFontSize, setExcelFontSize] = useState(13);
  const boqScrollRef = useRef<HTMLDivElement>(null);

  const selectedFile = files.find((f) => f.id === selectedFileId);
  const title = selectedFile ? `BOQ • ${selectedFile.file_name}` : "BOQ";

  return (
    <div className="glass-panel flex flex-col min-h-0 h-full">
      <ColumnHeader
        title={title}
        accent="cyan"
        badge={`${items.length} stavki`}
        actions={
          <div className="flex items-center gap-1.5">
            <div className="flex items-center rounded bg-bg-tertiary p-0.5">
              {(["parsed", "raw", "excel"] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setBoqViewMode(mode)}
                  className={`px-2 py-0.5 text-[10px] font-mono rounded transition-colors ${
                    boqViewMode === mode
                      ? "bg-accent-cyan/15 text-accent-cyan"
                      : "text-text-muted hover:text-text-secondary"
                  }`}
                >
                  {MODE_LABELS[mode]}
                </button>
              ))}
            </div>
            {boqViewMode === "excel" && (
              <>
                <button
                  onClick={() => setExcelZoom((z) => Math.max(50, z - 10))}
                  title="Umanji prikaz"
                  className="p-1 rounded text-text-muted hover:text-text-secondary hover:bg-bg-hover transition-colors"
                >
                  <Minus className="w-3.5 h-3.5" />
                </button>
                <span className="text-[10px] font-mono text-text-muted w-8 text-center tabular-nums">
                  {excelZoom}%
                </span>
                <button
                  onClick={() => setExcelZoom((z) => Math.min(200, z + 10))}
                  title="Uvećaj prikaz"
                  className="p-1 rounded text-text-muted hover:text-text-secondary hover:bg-bg-hover transition-colors"
                >
                  <Plus className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setExcelWrap((v) => !v)}
                  title={excelWrap ? "Onemogući omotavanje teksta" : "Omogući omotavanje teksta"}
                  className={`p-1 rounded transition-colors ${
                    excelWrap
                      ? "bg-accent-cyan/15 text-accent-cyan"
                      : "text-text-muted hover:text-text-secondary hover:bg-bg-hover"
                  }`}
                >
                  <WrapText className="w-3.5 h-3.5" />
                </button>
                <div className="w-px h-3.5 bg-border-default mx-0.5" />
                <button
                  onClick={() => setExcelFontSize((s) => Math.max(8, s - 1))}
                  title="Smanji veličinu fonta"
                  className="p-1 rounded text-text-muted hover:text-text-secondary hover:bg-bg-hover transition-colors"
                >
                  <AArrowDown className="w-3.5 h-3.5" />
                </button>
                <span className="text-[10px] font-mono text-text-muted w-5 text-center tabular-nums">
                  {excelFontSize}
                </span>
                <button
                  onClick={() => setExcelFontSize((s) => Math.min(24, s + 1))}
                  title="Povećaj veličinu fonta"
                  className="p-1 rounded text-text-muted hover:text-text-secondary hover:bg-bg-hover transition-colors"
                >
                  <AArrowUp className="w-3.5 h-3.5" />
                </button>
              </>
            )}
          </div>
        }
      />
      {isLoading && items.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-text-muted text-sm">
          Učitavanje stavki...
        </div>
      ) : (
        <>
          {boqViewMode === "parsed" && (
            <>
              <div className="shrink-0 p-2">
                <SheetPreview />
              </div>
              <div className="flex-1 min-h-0">
                <SpreadsheetView ref={boqScrollRef} />
              </div>
            </>
          )}
          {boqViewMode === "raw" && (
            <div className="flex-1 min-h-0">
              <RawSheetGrid />
            </div>
          )}
          {boqViewMode === "excel" && (
            <div className="flex-1 min-h-0">
              <ExcelView wrapAll={excelWrap} zoom={excelZoom} baseFontSize={excelFontSize} />
            </div>
          )}
        </>
      )}
    </div>
  );
}
