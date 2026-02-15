"use client";

import { useRef, useState } from "react";
import { AnimatePresence } from "framer-motion";
import { Activity } from "lucide-react";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useBoQStore } from "@/stores/boqStore";
import { useAgentStore } from "@/stores/agentStore";
import { useSelectionPipeline } from "@/hooks/useSelectionPipeline";

import TopBar from "@/components/layout/TopBar";
import ChatPanelList from "@/components/chat/ChatPanelList";
import RegexResultList from "@/components/boq/RegexResultList";
import SpreadsheetView from "@/components/spreadsheet/SpreadsheetView";
import SheetPreview from "@/components/spreadsheet/SheetPreview";
import RawSheetGrid from "@/components/spreadsheet/RawSheetGrid";
import ExcelView from "@/components/spreadsheet/ExcelView";
import AgentPanel from "@/components/agents/AgentPanel";
import PipelineBar from "@/components/layout/PipelineBar";
import ColumnHeader from "@/components/layout/ColumnHeader";

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
  const boqScrollRef = useRef<HTMLDivElement>(null);

  // ── Pipeline hooks ──────────────────────────────────────────────
  useSelectionPipeline();

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

      {/* Main three-column grid */}
      <main className="flex-1 grid grid-cols-[280px_1fr_2fr] gap-3 p-3 min-h-0">
        {/* Col 1: Chat panels */}
        <ChatPanelList />

        {/* Col 2: Regex / deterministic results */}
        <RegexResultList />

        {/* Col 3: Unified BOQ (view + edit) */}
        <div className="glass-panel flex flex-col min-h-0">
          <ColumnHeader
            title="BOQ"
            accent="cyan"
            badge={`${items.length} items`}
            actions={
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
              <ExcelView />
            </div>
          )}
        </div>
      </main>

      {/* Agent activity floating button + panel */}
      <AgentActivityButton />
      <AgentPanel />
    </div>
  );
}
