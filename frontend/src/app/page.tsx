"use client";

import { useState, useCallback, useRef } from "react";
import { AnimatePresence } from "framer-motion";
import { Activity, Camera, TreePine } from "lucide-react";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useBoQStore } from "@/stores/boqStore";
import { useAgentStore } from "@/stores/agentStore";

import UploadZone from "@/components/upload/UploadZone";
import FileList from "@/components/upload/FileList";
import SpreadsheetView from "@/components/spreadsheet/SpreadsheetView";
import EditableSheet from "@/components/spreadsheet/EditableSheet";
import SheetPreview from "@/components/spreadsheet/SheetPreview";
import { MatchList } from "@/components/boq/MatchList";
import BoQNavigator from "@/components/boq/BoQNavigator";
import AgentPanel from "@/components/agents/AgentPanel";
import ChatDrawer from "@/components/chat/ChatDrawer";
import PipelineBar from "@/components/layout/PipelineBar";
import ColumnHeader from "@/components/layout/ColumnHeader";
import PhotoUpload from "@/components/photos/PhotoUpload";
import PhotoAnalysis from "@/components/photos/PhotoAnalysis";

// ── Left Column Tabs ────────────────────────────────────────────────

type LeftTab = "files" | "navigator" | "photos";

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
  const { items, selectedRow, selectRow } = useBoQStore();
  const [leftTab, setLeftTab] = useState<LeftTab>("files");
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [photoAnalysis, setPhotoAnalysis] = useState<{
    imageUrl: string;
    analysis: null | {
      description: string;
      matchedItems: string[];
      progress: number;
      confidence: number;
    };
    isLoading: boolean;
  } | null>(null);

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

  const handleAnalyzePhoto = useCallback((file: File) => {
    const url = URL.createObjectURL(file);
    setPhotoAnalysis({ imageUrl: url, analysis: null, isLoading: true });
    // TODO: call backend vision agent API
    setTimeout(() => {
      setPhotoAnalysis({
        imageUrl: url,
        analysis: {
          description: "Photo analysis will be available when connected to the vision agent.",
          matchedItems: [],
          progress: 0,
          confidence: 0,
        },
        isLoading: false,
      });
    }, 2000);
  }, []);

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* Pipeline bar */}
      <div className="px-3 pt-3">
        <AnimatePresence>
          <PipelineBar />
        </AnimatePresence>
      </div>

      {/* Connection status indicator */}
      <div className="px-4 pt-2 flex items-center gap-2">
        <span
          className={`w-1.5 h-1.5 rounded-full ${isConnected ? "bg-status-success" : "bg-status-danger"}`}
        />
        <span className="text-[10px] text-text-muted font-mono uppercase tracking-wider">
          {isConnected ? "Connected" : "Disconnected"}
        </span>
      </div>

      {/* Main four-column grid */}
      <main className="flex-1 grid grid-cols-4 gap-3 p-3 min-h-0">
        {/* ── Col 1: Upload + Files + Navigator ────────────────── */}
        <div className="flex flex-col gap-3 min-h-0">
          <UploadZone />

          {/* Tab switcher */}
          <div className="flex gap-1 px-1">
            {[
              { id: "files" as LeftTab, label: "Files" },
              { id: "navigator" as LeftTab, label: "Navigator", icon: <TreePine className="w-3 h-3" /> },
              { id: "photos" as LeftTab, label: "Photos", icon: <Camera className="w-3 h-3" /> },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setLeftTab(tab.id)}
                className={`
                  flex items-center gap-1 px-2 py-1 rounded text-xs transition-all duration-150
                  ${leftTab === tab.id
                    ? "bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/20"
                    : "text-text-muted hover:text-text-secondary hover:bg-bg-hover"
                  }
                `}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          {leftTab === "files" && (
            <div className="glass-panel p-3 flex flex-col gap-2 flex-1 min-h-0 overflow-y-auto">
              <ColumnHeader
                title="Uploaded Files"
                accent="cyan"
                badge={`${useBoQStore.getState().files.length}`}
              />
              <FileList />
            </div>
          )}

          {leftTab === "navigator" && (
            <div className="glass-panel p-3 flex-1 min-h-0 overflow-y-auto">
              <ColumnHeader title="BOQ Navigator" accent="cyan" />
              <BoQNavigator
                items={items}
                selectedId={selectedRow?.id ?? null}
                onSelect={(item) => selectRow(item)}
              />
            </div>
          )}

          {leftTab === "photos" && (
            <div className="flex flex-col gap-3 flex-1 min-h-0 overflow-y-auto">
              <div className="glass-panel p-3">
                <ColumnHeader title="Photo Analysis" accent="purple" />
                <div className="mt-2">
                  <PhotoUpload
                    onAnalyze={handleAnalyzePhoto}
                    isAnalyzing={photoAnalysis?.isLoading}
                  />
                </div>
              </div>
              {photoAnalysis && (
                <div className="glass-panel p-3">
                  <PhotoAnalysis
                    imageUrl={photoAnalysis.imageUrl}
                    analysis={photoAnalysis.analysis}
                    isLoading={photoAnalysis.isLoading}
                  />
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── Col 2: Match Details ─────────────────────────────── */}
        <div className="glass-panel flex flex-col min-h-0">
          <ColumnHeader title="Match Details" accent="purple" />
          <div className="flex-1 overflow-y-auto p-2">
            <MatchList />
          </div>
        </div>

        {/* ── Col 3: Current BOQ ───────────────────────────────── */}
        <div className="glass-panel flex flex-col min-h-0">
          <ColumnHeader
            title="Current BOQ"
            accent="cyan"
            badge={`${items.length} items`}
          />
          {/* Raw sheet preview (first 5 rows) */}
          <div className="shrink-0 p-2">
            <SheetPreview />
          </div>
          <div className="flex-1 min-h-0" onScroll={handleBoqScroll}>
            <SpreadsheetView ref={boqScrollRef} />
          </div>
        </div>

        {/* ── Col 4: Working Copy ──────────────────────────────── */}
        <div className="glass-panel flex flex-col min-h-0">
          <ColumnHeader
            title="Working Copy"
            accent="purple"
            badge="editable"
            actions={
              selectedRow ? (
                <button
                  onClick={() => setIsChatOpen(true)}
                  className="text-[10px] text-accent-purple hover:text-accent-cyan transition-colors px-2 py-0.5 rounded border border-border-default hover:border-accent-cyan/30"
                >
                  Chat
                </button>
              ) : undefined
            }
          />
          <div className="flex-1 min-h-0" onScroll={handleWorkingScroll}>
            <EditableSheet ref={workingScrollRef} />
          </div>
        </div>
      </main>

      {/* Agent activity floating button + panel */}
      <AgentActivityButton />
      <AgentPanel />

      {/* Chat drawer */}
      <ChatDrawer
        itemId={selectedRow?.id ?? null}
        item={selectedRow}
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
      />
    </div>
  );
}
