"use client";

import ColumnHeader from "@/components/layout/ColumnHeader";

export default function ChangesPanel() {
  return (
    <div className="glass-panel flex flex-col min-h-0 h-full">
      <ColumnHeader
        title="Changes"
        accent="cyan"
        badge="0"
      />
      <div className="flex-1 overflow-auto p-4">
        <div className="text-center text-text-muted text-sm py-8">
          No changes yet
        </div>
      </div>
    </div>
  );
}
