"use client";

import { useCallback } from "react";
import { MessageSquare, X, Loader2 } from "lucide-react";
import { useChatPanelStore } from "@/stores/chatPanelStore";
import { useSelectionStore } from "@/stores/selectionStore";
import { useMatchStore } from "@/stores/matchStore";
import ColumnHeader from "@/components/layout/ColumnHeader";
import ChatPanelComponent from "./ChatPanel";

export default function ChatPanelList() {
  const panels = useChatPanelStore((s) => s.panels);
  const activePanelId = useChatPanelStore((s) => s.activePanelId);
  const clearAllChats = useChatPanelStore((s) => s.clearAll);
  const setActive = useChatPanelStore((s) => s.setActive);

  const handleClearAll = useCallback(() => {
    const selectionIds = useChatPanelStore.getState().panels.map((p) => p.selectionId);
    for (const selId of selectionIds) {
      useSelectionStore.getState().removeSelection(selId);
      useMatchStore.getState().clearSelection(selId);
    }
    clearAllChats();
  }, [clearAllChats]);

  const handleTabClick = useCallback((panelId: string, selectionId: string) => {
    setActive(panelId);
    useSelectionStore.getState().setActive(selectionId);
  }, [setActive]);

  const handleTabClose = useCallback((e: React.MouseEvent, selectionId: string) => {
    e.stopPropagation();
    useSelectionStore.getState().removeSelection(selectionId);
  }, []);

  return (
    <div className="glass-panel flex flex-col min-h-0 h-full overflow-hidden">
      <ColumnHeader
        title="Chat"
        accent="cyan"
        badge={panels.length > 0 ? `${panels.length}` : undefined}
        actions={
          panels.length > 0 ? (
            <button
              onClick={handleClearAll}
              className="px-2 py-0.5 text-[10px] font-mono rounded text-text-muted hover:text-accent-cyan hover:bg-accent-cyan/10 transition-colors"
            >
              Clear all
            </button>
          ) : undefined
        }
      />

      {panels.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-2 text-text-muted select-none">
          <MessageSquare className="w-8 h-8 opacity-40" />
          <p className="text-xs text-center">
            Select rows in Current BOQ to start a conversation
          </p>
        </div>
      ) : (
        <>
          {/* Tab strip */}
          <div className="shrink-0 flex items-center gap-0.5 px-1.5 py-1 border-b border-border-default/50 overflow-x-auto">
            {panels.map((panel) => {
              const isActive = panel.id === activePanelId;
              return (
                <button
                  key={panel.id}
                  onClick={() => handleTabClick(panel.id, panel.selectionId)}
                  className={`
                    flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium
                    transition-colors shrink-0 group
                    ${isActive
                      ? "bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30"
                      : "text-text-muted hover:text-text-secondary hover:bg-bg-hover/50 border border-transparent"
                    }
                  `}
                >
                  {panel.isAnalyzing ? (
                    <Loader2 className="w-2.5 h-2.5 animate-spin shrink-0" />
                  ) : (
                    <MessageSquare className="w-2.5 h-2.5 shrink-0" />
                  )}
                  <span className="truncate max-w-[80px]">{panel.label}</span>
                  <span
                    onClick={(e) => handleTabClose(e, panel.selectionId)}
                    className="ml-0.5 p-0.5 rounded hover:bg-bg-tertiary opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <X className="w-2.5 h-2.5" />
                  </span>
                </button>
              );
            })}
          </div>

          {/* Active chat content */}
          <div className="flex-1 min-h-0 overflow-hidden">
            {activePanelId && (
              <ChatPanelComponent panelId={activePanelId} embedded />
            )}
          </div>
        </>
      )}
    </div>
  );
}
