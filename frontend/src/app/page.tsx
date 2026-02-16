"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence } from "framer-motion";
import { Activity, WrapText } from "lucide-react";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useBoQStore } from "@/stores/boqStore";
import { useAgentStore } from "@/stores/agentStore";
import { useSelectionPipeline } from "@/hooks/useSelectionPipeline";

import TopBar from "@/components/layout/TopBar";
import ChatPanelList from "@/components/chat/ChatPanelList";
import MatchResultsPanel from "@/components/boq/MatchResultsPanel";
import SpreadsheetView from "@/components/spreadsheet/SpreadsheetView";
import SheetPreview from "@/components/spreadsheet/SheetPreview";
import RawSheetGrid from "@/components/spreadsheet/RawSheetGrid";
import dynamic from "next/dynamic";

const ExcelView = dynamic(() => import("@/components/spreadsheet/ExcelView"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full text-text-muted text-sm">
      Loading Excel view...
    </div>
  ),
});
import AgentPanel from "@/components/agents/AgentPanel";
import PipelineBar from "@/components/layout/PipelineBar";
import { PresetToolbar } from "@/components/layout/PresetToolbar";
import ColumnHeader from "@/components/layout/ColumnHeader";
import ChangesPanel from "@/components/changes/ChangesPanel";

// ── Agent Activity Button (inline) ──────────────────────────────────

function AgentActivityButton() {
  const { events, isPanelOpen, togglePanel, activeAgents } = useAgentStore();
  const activeCount = activeAgents.size;

  return (
    <button
      onClick={togglePanel}
      className={`
        fixed bottom-4 right-4 z-50 flex items-center gap-2 px-4 py-2 rounded-full
        glass-panel border transition-all duration-200 hover:scale-105 active:scale-95
        ${activeCount > 0 ? "glow-purple border-accent-purple/40" : "border-border-default"}
      `}
    >
      <Activity
        className={`w-4 h-4 ${activeCount > 0 ? "text-accent-purple" : "text-text-muted"}`}
      />
      <span className="text-xs text-text-secondary">
        {activeCount > 0 ? `${activeCount} active` : "Agents"}
      </span>
      {activeCount > 0 && (
        <span className="w-2 h-2 rounded-full bg-accent-purple animate-pulse" />
      )}
      {events.length > 0 && (
        <span className="text-[10px] text-text-muted font-mono">
          {events.length}
        </span>
      )}
    </button>
  );
}

// ── Main Page ───────────────────────────────────────────────────────

export default function HomePage() {
  const { isConnected } = useWebSocket();
  const { items } = useBoQStore();
  const [boqViewMode, setBoqViewMode] = useState<"parsed" | "raw" | "excel">("parsed");
  const [excelWrap, setExcelWrap] = useState(true);
  const boqScrollRef = useRef<HTMLDivElement>(null);
  const mainRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{ idx: number; startX: number; startW: number[] } | null>(null);
  const [colWidths, setColWidths] = useState([280, 400, 400, 280]);

  // ── Pipeline hooks ──────────────────────────────────────────────
  useSelectionPipeline();

  // Initialize column widths from actual container size
  useEffect(() => {
    if (!mainRef.current) return;
    const available = mainRef.current.clientWidth - 24 - 36; // padding(2×12) + handles(3×12)
    const side = 280;
    const mid = Math.max(200, (available - side * 2) / 2);
    setColWidths([side, mid, mid, side]);
  }, []);

  const onResizeStart = (handleIndex: number) => (e: React.MouseEvent) => {
    e.preventDefault();
    dragRef.current = { idx: handleIndex, startX: e.clientX, startW: [...colWidths] };
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    const onMove = (ev: MouseEvent) => {
      if (!dragRef.current) return;
      const { idx, startX, startW } = dragRef.current;
      const delta = ev.clientX - startX;
      const newL = startW[idx] + delta;
      const newR = startW[idx + 1] - delta;
      if (newL >= 150 && newR >= 150) {
        const next = [...startW];
        next[idx] = newL;
        next[idx + 1] = newR;
        setColWidths(next);
      }
    };

    const onUp = () => {
      dragRef.current = null;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };

    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  };

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* Top bar (replaces sidebar) */}
      <TopBar isConnected={isConnected} />

      {/* Pipeline bar */}
      <div className="px-3 pt-2">
        <AnimatePresence>
          <PipelineBar />
        </AnimatePresence>
      </div>

      {/* Preset toolbar (column visibility + export) */}
      <PresetToolbar />

      {/* Main four-column layout with resizable handles */}
      <main ref={mainRef} className="flex-1 flex p-3 min-h-0">
        {/* Col 1: Chat panels */}
        <div style={{ width: colWidths[0] }} className="shrink-0 min-w-0">
          <ChatPanelList />
        </div>

        {/* Handle 1–2 */}
        <div
          className="w-3 shrink-0 cursor-col-resize group flex items-center justify-center"
          onMouseDown={onResizeStart(0)}
        >
          <div className="w-0.5 h-8 rounded-full opacity-0 group-hover:opacity-100 bg-text-muted/40 transition-opacity" />
        </div>

        {/* Col 2: Match results */}
        <div style={{ width: colWidths[1] }} className="shrink-0 min-w-0 h-full">
          <MatchResultsPanel />
        </div>

        {/* Handle 2–3 */}
        <div
          className="w-3 shrink-0 cursor-col-resize group flex items-center justify-center"
          onMouseDown={onResizeStart(1)}
        >
          <div className="w-0.5 h-8 rounded-full opacity-0 group-hover:opacity-100 bg-text-muted/40 transition-opacity" />
        </div>

        {/* Col 3: Unified BOQ (view + edit) */}
        <div style={{ width: colWidths[2] }} className="shrink-0 min-w-0">
          <div className="glass-panel flex flex-col min-h-0 h-full">
            <ColumnHeader
              title="BOQ"
              accent="cyan"
              badge={`${items.length} items`}
              actions={
                <div className="flex items-center gap-1.5">
                  <div className="flex items-center rounded bg-bg-tertiary p-0.5">
                    <button
                      onClick={() => setBoqViewMode("parsed")}
                      className={`px-2 py-0.5 text-[10px] font-mono rounded transition-colors ${
                        boqViewMode === "parsed"
                          ? "bg-accent-cyan/15 text-accent-cyan"
                          : "text-text-muted hover:text-text-secondary"
                      }`}
                    >
                      Parsed
                    </button>
                    <button
                      onClick={() => setBoqViewMode("raw")}
                      className={`px-2 py-0.5 text-[10px] font-mono rounded transition-colors ${
                        boqViewMode === "raw"
                          ? "bg-accent-cyan/15 text-accent-cyan"
                          : "text-text-muted hover:text-text-secondary"
                      }`}
                    >
                      Raw
                    </button>
                    <button
                      onClick={() => setBoqViewMode("excel")}
                      className={`px-2 py-0.5 text-[10px] font-mono rounded transition-colors ${
                        boqViewMode === "excel"
                          ? "bg-accent-cyan/15 text-accent-cyan"
                          : "text-text-muted hover:text-text-secondary"
                      }`}
                    >
                      Excel
                    </button>
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
        </div>

        {/* Handle 3–4 */}
        <div
          className="w-3 shrink-0 cursor-col-resize group flex items-center justify-center"
          onMouseDown={onResizeStart(2)}
        >
          <div className="w-0.5 h-8 rounded-full opacity-0 group-hover:opacity-100 bg-text-muted/40 transition-opacity" />
        </div>

        {/* Col 4: Changes */}
        <div style={{ width: colWidths[3] }} className="shrink-0 min-w-0">
          <ChangesPanel />
        </div>
      </main>

      {/* Agent activity floating button + panel */}
      <AgentActivityButton />
      <AgentPanel />
    </div>
  );
}
