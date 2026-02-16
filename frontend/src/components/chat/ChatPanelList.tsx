"use client";

import { useEffect, useRef } from "react";
import { MessageSquare } from "lucide-react";
import { useChatPanelStore } from "@/stores/chatPanelStore";
import ColumnHeader from "@/components/layout/ColumnHeader";
import ChatPanelComponent from "./ChatPanel";

export default function ChatPanelList() {
  const panels = useChatPanelStore((s) => s.panels);
  const activePanelId = useChatPanelStore((s) => s.activePanelId);
  const activeRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to active panel
  useEffect(() => {
    if (activePanelId && activeRef.current) {
      activeRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [activePanelId]);

  return (
    <div className="glass-panel flex flex-col min-h-0">
      <ColumnHeader
        title="Chat"
        accent="cyan"
        badge={panels.length > 0 ? `${panels.length}` : undefined}
      />
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {panels.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-text-muted select-none">
            <MessageSquare className="w-8 h-8 opacity-40" />
            <p className="text-xs text-center">
              Select rows in Current BOQ to start a conversation
            </p>
          </div>
        ) : (
          panels.map((panel) => (
            <div
              key={panel.id}
              ref={panel.id === activePanelId ? activeRef : undefined}
            >
              <ChatPanelComponent panelId={panel.id} />
            </div>
          ))
        )}
      </div>
    </div>
  );
}
