"use client";

import { useCallback, useRef } from "react";
import { AnimatePresence } from "framer-motion";
import { Activity } from "lucide-react";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useBoQStore } from "@/stores/boqStore";
import { useAgentStore } from "@/stores/agentStore";
import { useSelectionPipeline } from "@/hooks/useSelectionPipeline";
import { useRowAlignment } from "@/hooks/useRowAlignment";

import TopBar from "@/components/layout/TopBar";
import ChatPanelList from "@/components/chat/ChatPanelList";
import RegexResultList from "@/components/boq/RegexResultList";
import SpreadsheetView from "@/components/spreadsheet/SpreadsheetView";
import EditableSheet from "@/components/spreadsheet/EditableSheet";
import SheetPreview from "@/components/spreadsheet/SheetPreview";
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

  // ── Scroll synchronization between Current BOQ and Working Copy ──
  const boqScrollRef = useRef<HTMLDivElement>(null);
  const workingScrollRef = useRef<HTMLDivElement>(null);
  const isSyncing = useRef(false);

  const handleBoqScroll = useCallback(() => {
    if (isSyncing.current) return;
    isSyncing.current = true;
    if (boqScrollRef.current && workingScrollRef.current) {
      workingScrollRef.current.scrollTop = boqScrollRef.current.scrollTop;
    }
    requestAnimationFrame(() => { isSyncing.current = false; });
  }, []);

  const handleWorkingScroll = useCallback(() => {
    if (isSyncing.current) return;
    isSyncing.current = true;
    if (boqScrollRef.current && workingScrollRef.current) {
      boqScrollRef.current.scrollTop = workingScrollRef.current.scrollTop;
    }
    requestAnimationFrame(() => { isSyncing.current = false; });
  }, []);

  // ── Pipeline hooks ──────────────────────────────────────────────
  useSelectionPipeline();
  useRowAlignment(boqScrollRef, workingScrollRef);

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

      {/* Main four-column grid */}
      <main className="flex-1 grid grid-cols-[280px_280px_1fr_1fr] gap-3 p-3 min-h-0">
        {/* Col 1: Chat panels */}
        <ChatPanelList />

        {/* Col 2: Regex / deterministic results */}
        <RegexResultList />

        {/* Col 3: Current BOQ */}
        <div className="glass-panel flex flex-col min-h-0">
          <ColumnHeader title="Current BOQ" accent="cyan" badge={`${items.length} items`} />
          <div className="shrink-0 p-2">
            <SheetPreview />
          </div>
          <div className="flex-1 min-h-0" onScroll={handleBoqScroll}>
            <SpreadsheetView ref={boqScrollRef} />
          </div>
        </div>

        {/* Col 4: Edited (Working Copy) */}
        <div className="glass-panel flex flex-col min-h-0">
          <ColumnHeader title="Edited" accent="purple" badge="editable" />
          <div className="flex-1 min-h-0" onScroll={handleWorkingScroll}>
            <EditableSheet ref={workingScrollRef} />
          </div>
        </div>
      </main>

      {/* Agent activity floating button + panel */}
      <AgentActivityButton />
      <AgentPanel />
    </div>
  );
}
