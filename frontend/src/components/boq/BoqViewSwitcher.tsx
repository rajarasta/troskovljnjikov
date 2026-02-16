"use client";

import { useRef, useState } from "react";
import { WrapText } from "lucide-react";
import { useBoQStore } from "@/stores/boqStore";
import dynamic from "next/dynamic";

import SpreadsheetView from "@/components/spreadsheet/SpreadsheetView";
import SheetPreview from "@/components/spreadsheet/SheetPreview";
import RawSheetGrid from "@/components/spreadsheet/RawSheetGrid";
import ColumnHeader from "@/components/layout/ColumnHeader";

const ExcelView = dynamic(() => import("@/components/spreadsheet/ExcelView"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full text-text-muted text-sm">
      Loading Excel view...
    </div>
  ),
});

export default function BoqViewSwitcher() {
  const { items } = useBoQStore();
  const [boqViewMode, setBoqViewMode] = useState<"parsed" | "raw" | "excel">("parsed");
  const [excelWrap, setExcelWrap] = useState(true);
  const boqScrollRef = useRef<HTMLDivElement>(null);

  return (
    <div className="glass-panel flex flex-col min-h-0 h-full">
      <ColumnHeader
        title="BOQ"
        accent="cyan"
        badge={`${items.length} items`}
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
                  {mode.charAt(0).toUpperCase() + mode.slice(1)}
                </button>
              ))}
            </div>
            <button
              onClick={() => setExcelWrap((v) => !v)}
              title={excelWrap ? "Disable text wrap" : "Enable text wrap"}
              className={`p-1 rounded transition-colors ${
                excelWrap
                  ? "bg-accent-cyan/15 text-accent-cyan"
                  : "text-text-muted hover:text-text-secondary hover:bg-bg-hover"
              }`}
            >
              <WrapText className="w-3.5 h-3.5" />
            </button>
          </div>
        }
      />
      {boqViewMode === "parsed" ? (
        <>
          <div className="shrink-0 p-2">
            <SheetPreview />
          </div>
          <div className="flex-1 min-h-0">
            <SpreadsheetView ref={boqScrollRef} />
          </div>
        </>
      ) : boqViewMode === "raw" ? (
        <div className="flex-1 min-h-0">
          <RawSheetGrid />
        </div>
      ) : (
        <div className="flex-1 min-h-0">
          <ExcelView wrapAll={excelWrap} />
        </div>
      )}
    </div>
  );
}
