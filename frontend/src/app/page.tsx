"use client";

import { useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload,
  FileSpreadsheet,
  Search,
  Activity,
  ChevronRight,
  Trash2,
  Loader2,
} from "lucide-react";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useBoQStore } from "@/stores/boqStore";
import { useMatchStore } from "@/stores/matchStore";
import { useAgentStore } from "@/stores/agentStore";
import { usePipelineStore } from "@/stores/pipelineStore";
import type { PipelineStage } from "@/lib/types";

// ── Pipeline Bar ────────────────────────────────────────────────────

const PIPELINE_LABELS: Record<PipelineStage, string> = {
  upload: "Upload",
  parse: "Parse",
  index: "Index",
  match: "Match",
  suggest: "Suggest",
  review: "Review",
};

function PipelineBar() {
  const { stage, progress, isRunning } = usePipelineStore();

  if (!isRunning) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="glass-panel glow-cyan px-4 py-2 flex items-center gap-3"
    >
      <Loader2 className="w-4 h-4 text-accent-cyan animate-spin" />
      <div className="flex gap-1 flex-1">
        {(Object.keys(PIPELINE_LABELS) as PipelineStage[]).map((s) => {
          const isActive = s === stage;
          const stageKeys = Object.keys(PIPELINE_LABELS) as PipelineStage[];
          const isPast =
            stage !== null &&
            stageKeys.indexOf(s) < stageKeys.indexOf(stage);

          return (
            <div key={s} className="flex items-center gap-1">
              <div
                className={`
                  px-2 py-0.5 rounded text-xs font-medium transition-all duration-300
                  ${
                    isActive
                      ? "bg-accent-cyan/20 text-accent-cyan border border-accent-cyan/40"
                      : isPast
                        ? "bg-status-success/10 text-status-success"
                        : "text-text-muted"
                  }
                `}
              >
                {PIPELINE_LABELS[s]}
              </div>
              {s !== "review" && (
                <ChevronRight className="w-3 h-3 text-text-muted" />
              )}
            </div>
          );
        })}
      </div>
      <div className="w-24 h-1.5 rounded-full bg-bg-tertiary overflow-hidden">
        <motion.div
          className="h-full bg-accent-cyan rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.3 }}
        />
      </div>
      <span className="text-xs text-text-secondary font-mono">
        {progress}%
      </span>
    </motion.div>
  );
}

// ── Upload Zone ─────────────────────────────────────────────────────

function UploadZone() {
  const { uploadFile, isLoading } = useBoQStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file) uploadFile(file);
    },
    [uploadFile]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) uploadFile(file);
    },
    [uploadFile]
  );

  return (
    <div
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
      onClick={() => fileInputRef.current?.click()}
      className="glass-panel border-dashed border-2 border-border-default hover:border-accent-cyan/50
                 transition-colors duration-200 cursor-pointer p-4 text-center group"
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".xlsx,.xls,.csv"
        onChange={handleFileSelect}
        className="hidden"
      />
      {isLoading ? (
        <Loader2 className="w-8 h-8 mx-auto text-accent-cyan animate-spin" />
      ) : (
        <Upload className="w-8 h-8 mx-auto text-text-muted group-hover:text-accent-cyan transition-colors" />
      )}
      <p className="text-xs text-text-secondary mt-2">
        Drop XLSX / CSV or click to upload
      </p>
    </div>
  );
}

// ── File List ───────────────────────────────────────────────────────

function FileList() {
  const { files, selectedFileId, loadItems, deleteFile, loadFiles } =
    useBoQStore();

  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  return (
    <div className="flex flex-col gap-1">
      {files.length === 0 && (
        <p className="text-xs text-text-muted px-2 py-1">
          No files uploaded yet
        </p>
      )}
      {files.map((file) => (
        <motion.div
          key={file.id}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          className={`
            flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer text-sm
            transition-colors duration-150
            ${
              selectedFileId === file.id
                ? "bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/20"
                : "hover:bg-bg-hover text-text-secondary"
            }
          `}
          onClick={() => loadItems(file.id)}
        >
          <FileSpreadsheet className="w-4 h-4 shrink-0" />
          <span className="truncate flex-1">{file.file_name}</span>
          <span className="text-xs text-text-muted font-mono">
            {file.item_count}
          </span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              deleteFile(file.id);
            }}
            className="opacity-0 group-hover:opacity-100 hover:text-status-danger transition-opacity p-0.5"
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </motion.div>
      ))}
    </div>
  );
}

// ── Match Results Placeholder ───────────────────────────────────────

function MatchResults() {
  const { matches, stats, isSearching } = useMatchStore();

  if (isSearching) {
    return (
      <div className="flex items-center gap-2 p-3 text-sm text-text-secondary">
        <Loader2 className="w-4 h-4 animate-spin text-accent-purple" />
        Searching matches...
      </div>
    );
  }

  if (matches.length === 0) {
    return (
      <div className="p-3 text-xs text-text-muted">
        Select a row to find matching items across projects
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1 max-h-64 overflow-y-auto">
      {stats && (
        <div className="px-2 py-1 text-xs text-text-muted font-mono border-b border-border-default">
          {stats.count} matches | avg {stats.avgPrice.toFixed(2)}
        </div>
      )}
      {matches.map((match, i) => (
        <div
          key={`${match.item.id}-${i}`}
          className="px-2 py-1.5 hover:bg-bg-hover rounded text-xs transition-colors"
        >
          <div className="flex justify-between">
            <span className="text-text-primary truncate flex-1">
              {match.item.description}
            </span>
            <span className="text-accent-cyan font-mono ml-2">
              {(match.similarity * 100).toFixed(0)}%
            </span>
          </div>
          <div className="text-text-muted mt-0.5">
            {match.item.project_name} | {match.item.unit_price.toFixed(2)}{" "}
            {match.item.unit}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Agent Activity Button ───────────────────────────────────────────

function AgentActivityButton() {
  const { events, isPanelOpen, togglePanel, activeAgents } = useAgentStore();
  const activeCount = activeAgents.size;

  return (
    <>
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={togglePanel}
        className={`
          fixed bottom-4 right-4 z-50 flex items-center gap-2 px-4 py-2 rounded-full
          glass-panel border transition-all duration-200
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
      </motion.button>

      <AnimatePresence>
        {isPanelOpen && (
          <motion.div
            initial={{ opacity: 0, x: 300 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 300 }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed top-0 right-0 bottom-0 w-80 z-40 glass-panel border-l border-border-default
                       overflow-y-auto p-4 flex flex-col gap-2"
          >
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-accent-purple">
                Agent Activity
              </h3>
              <span className="text-xs text-text-muted font-mono">
                {events.length} events
              </span>
            </div>
            {events.length === 0 ? (
              <p className="text-xs text-text-muted">
                No agent activity yet
              </p>
            ) : (
              events
                .slice(-50)
                .reverse()
                .map((event, i) => (
                  <div
                    key={`${event.timestamp}-${i}`}
                    className="text-xs border-b border-border-default pb-1"
                  >
                    <div className="flex justify-between">
                      <span className="text-accent-cyan font-mono">
                        {event.agent_type || event.type}
                      </span>
                      <span className="text-text-muted">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    {event.agent_id && (
                      <span className="text-text-muted">
                        {event.agent_id}
                      </span>
                    )}
                  </div>
                ))
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

// ── Main Page ───────────────────────────────────────────────────────

export default function HomePage() {
  const { isConnected } = useWebSocket();
  const { items, selectedRow, selectRow } = useBoQStore();

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

      {/* Main three-column grid */}
      <main className="flex-1 grid grid-cols-[320px_1fr_1fr] gap-3 p-3 min-h-0">
        {/* ── Left Column: Upload + Files + Matches ────────────── */}
        <div className="flex flex-col gap-3 min-h-0 overflow-y-auto">
          <UploadZone />

          <div className="glass-panel p-3 flex flex-col gap-2">
            <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider flex items-center gap-1.5">
              <FileSpreadsheet className="w-3.5 h-3.5 text-accent-cyan" />
              Uploaded Files
            </h2>
            <FileList />
          </div>

          <div className="glass-panel p-3 flex flex-col gap-2 flex-1 min-h-0">
            <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider flex items-center gap-1.5">
              <Search className="w-3.5 h-3.5 text-accent-purple" />
              Match Results
            </h2>
            <MatchResults />
          </div>
        </div>

        {/* ── Center Column: Current BOQ ───────────────────────── */}
        <div className="glass-panel flex flex-col min-h-0">
          <div className="px-4 py-3 border-b border-border-default flex items-center justify-between">
            <h2 className="text-sm font-semibold text-accent-cyan uppercase tracking-wider">
              Current BOQ
            </h2>
            <span className="text-xs text-text-muted font-mono">
              {items.length} items
            </span>
          </div>
          <div className="flex-1 overflow-auto p-1">
            {items.length === 0 ? (
              <div className="flex items-center justify-center h-full text-text-muted text-sm">
                Upload a file to view its contents
              </div>
            ) : (
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-text-muted border-b border-border-default">
                    <th className="px-2 py-1.5 font-medium">#</th>
                    <th className="px-2 py-1.5 font-medium">Description</th>
                    <th className="px-2 py-1.5 font-medium text-right">Qty</th>
                    <th className="px-2 py-1.5 font-medium">Unit</th>
                    <th className="px-2 py-1.5 font-medium text-right">
                      Unit Price
                    </th>
                    <th className="px-2 py-1.5 font-medium text-right">
                      Total
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr
                      key={item.id}
                      onClick={() => selectRow(item)}
                      className={`
                        cursor-pointer transition-colors duration-100 border-b border-border-default/50
                        ${
                          selectedRow?.id === item.id
                            ? "bg-accent-cyan/10 text-accent-cyan"
                            : "hover:bg-bg-hover"
                        }
                      `}
                    >
                      <td className="px-2 py-1 font-mono text-text-muted">
                        {item.item_number}
                      </td>
                      <td className="px-2 py-1 max-w-[200px] truncate">
                        {item.description}
                      </td>
                      <td className="px-2 py-1 text-right font-mono">
                        {item.quantity}
                      </td>
                      <td className="px-2 py-1 text-text-muted">{item.unit}</td>
                      <td className="px-2 py-1 text-right font-mono">
                        {item.unit_price.toFixed(2)}
                      </td>
                      <td className="px-2 py-1 text-right font-mono">
                        {item.total.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* ── Right Column: Working Copy ───────────────────────── */}
        <div className="glass-panel flex flex-col min-h-0">
          <div className="px-4 py-3 border-b border-border-default flex items-center justify-between">
            <h2 className="text-sm font-semibold text-accent-purple uppercase tracking-wider">
              Working Copy
            </h2>
            <span className="text-xs text-text-muted font-mono">editable</span>
          </div>
          <div className="flex-1 overflow-auto p-4">
            <div className="flex items-center justify-center h-full text-text-muted text-sm">
              {selectedRow ? (
                <div className="w-full space-y-3">
                  <div className="glass-panel p-3">
                    <label className="text-[10px] text-text-muted uppercase tracking-wider block mb-1">
                      Item Number
                    </label>
                    <div className="font-mono text-sm text-text-primary">
                      {selectedRow.item_number}
                    </div>
                  </div>
                  <div className="glass-panel p-3">
                    <label className="text-[10px] text-text-muted uppercase tracking-wider block mb-1">
                      Description
                    </label>
                    <div className="text-sm text-text-primary">
                      {selectedRow.description}
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <div className="glass-panel p-3">
                      <label className="text-[10px] text-text-muted uppercase tracking-wider block mb-1">
                        Quantity
                      </label>
                      <div className="font-mono text-sm text-text-primary">
                        {selectedRow.quantity}
                      </div>
                    </div>
                    <div className="glass-panel p-3">
                      <label className="text-[10px] text-text-muted uppercase tracking-wider block mb-1">
                        Unit
                      </label>
                      <div className="font-mono text-sm text-text-primary">
                        {selectedRow.unit}
                      </div>
                    </div>
                    <div className="glass-panel p-3">
                      <label className="text-[10px] text-text-muted uppercase tracking-wider block mb-1">
                        Unit Price
                      </label>
                      <div className="font-mono text-sm text-accent-cyan">
                        {selectedRow.unit_price.toFixed(2)}
                      </div>
                    </div>
                  </div>
                  <div className="glass-panel p-3">
                    <label className="text-[10px] text-text-muted uppercase tracking-wider block mb-1">
                      Total
                    </label>
                    <div className="font-mono text-lg text-accent-cyan">
                      {selectedRow.total.toFixed(2)}
                    </div>
                  </div>
                </div>
              ) : (
                "Select a row from Current BOQ to edit"
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Agent activity floating button */}
      <AgentActivityButton />
    </div>
  );
}
