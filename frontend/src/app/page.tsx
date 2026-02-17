"use client";

import { useRef } from "react";
import { AnimatePresence } from "framer-motion";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useSelectionPipeline } from "@/hooks/useSelectionPipeline";
import { useKeyboardNav } from "@/hooks/useKeyboardNav";
import { useColumnResize } from "@/hooks/useColumnResize";

import TopBar from "@/components/layout/TopBar";
import ChatPanelList from "@/components/chat/ChatPanelList";
import MatchResultsPanel from "@/components/boq/MatchResultsPanel";
import BoqViewSwitcher from "@/components/boq/BoqViewSwitcher";
import AgentPanel from "@/components/agents/AgentPanel";
import AgentActivityButton from "@/components/agents/AgentActivityButton";
import PipelineBar from "@/components/layout/PipelineBar";
import ChangesPanel from "@/components/changes/ChangesPanel";
import FilePreviewModal from "@/components/boq/FilePreviewModal";
import { ErrorBoundary } from "@/components/layout/ErrorBoundary";

export default function HomePage() {
  const { isConnected } = useWebSocket();
  const mainRef = useRef<HTMLDivElement>(null);
  const { colWidths, onResizeStart } = useColumnResize(4, mainRef);

  useSelectionPipeline();
  useKeyboardNav();

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <TopBar isConnected={isConnected} />

      <div className="px-3 pt-2">
        <AnimatePresence>
          <PipelineBar />
        </AnimatePresence>
      </div>

      <main ref={mainRef} className="flex-1 flex p-3 min-h-0">
        {/* Col 1: Chat panels */}
        <div style={{ width: colWidths[0] }} className="shrink-0 min-w-0">
          <ErrorBoundary fallbackLabel="Chat">
            <ChatPanelList />
          </ErrorBoundary>
        </div>

        <ResizeHandle onMouseDown={onResizeStart(0)} />

        {/* Col 2: Match results */}
        <div style={{ width: colWidths[1] }} className="shrink-0 min-w-0 h-full">
          <ErrorBoundary fallbackLabel="Matches">
            <MatchResultsPanel />
          </ErrorBoundary>
        </div>

        <ResizeHandle onMouseDown={onResizeStart(1)} />

        {/* Col 3: BOQ view */}
        <div style={{ width: colWidths[2] }} className="shrink-0 min-w-0">
          <ErrorBoundary fallbackLabel="BoQ View">
            <BoqViewSwitcher />
          </ErrorBoundary>
        </div>

        <ResizeHandle onMouseDown={onResizeStart(2)} />

        {/* Col 4: Changes */}
        <div style={{ width: colWidths[3] }} className="shrink-0 min-w-0">
          <ErrorBoundary fallbackLabel="Changes">
            <ChangesPanel />
          </ErrorBoundary>
        </div>
      </main>

      <AgentActivityButton />
      <AgentPanel />
      <FilePreviewModal />
    </div>
  );
}

function ResizeHandle({ onMouseDown }: { onMouseDown: (e: React.MouseEvent) => void }) {
  return (
    <div
      className="w-3 shrink-0 cursor-col-resize group flex items-center justify-center"
      onMouseDown={onMouseDown}
    >
      <div className="w-0.5 h-8 rounded-full opacity-0 group-hover:opacity-100 bg-text-muted/40 transition-opacity" />
    </div>
  );
}
