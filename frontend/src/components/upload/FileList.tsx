"use client";

import { useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileSpreadsheet,
  FileText,
  Trash2,
  Inbox,
} from "lucide-react";
import { useBoQStore } from "@/stores/boqStore";
import type { BoQFile } from "@/lib/types";

// ── Helpers ──────────────────────────────────────────────────────────

function getFileIcon(fileType: string) {
  switch (fileType.toLowerCase()) {
    case "xlsx":
    case "xls":
      return FileSpreadsheet;
    case "csv":
      return FileText;
    default:
      return FileSpreadsheet;
  }
}

function formatRelativeDate(isoDate: string): string {
  const date = new Date(isoDate);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHr = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHr / 24);

  if (diffSec < 60) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
  if (diffDay < 30) return `${Math.floor(diffDay / 7)}w ago`;

  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

function truncateFilename(name: string, maxLength: number = 28): string {
  if (name.length <= maxLength) return name;

  const extIndex = name.lastIndexOf(".");
  if (extIndex === -1) return name.slice(0, maxLength - 3) + "...";

  const ext = name.slice(extIndex);
  const baseName = name.slice(0, extIndex);
  const availableLength = maxLength - ext.length - 3; // 3 for "..."

  if (availableLength <= 0) return name.slice(0, maxLength - 3) + "...";
  return baseName.slice(0, availableLength) + "..." + ext;
}

// ── Animation Variants ───────────────────────────────────────────────

const listVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, x: -12 },
  visible: {
    opacity: 1,
    x: 0,
    transition: {
      type: "spring" as const,
      stiffness: 400,
      damping: 30,
    },
  },
  exit: {
    opacity: 0,
    x: -12,
    height: 0,
    marginBottom: 0,
    paddingTop: 0,
    paddingBottom: 0,
    transition: { duration: 0.2 },
  },
};

// ── FileRow Component ────────────────────────────────────────────────

interface FileRowProps {
  file: BoQFile;
  isSelected: boolean;
  onSelect: (fileId: string) => void;
  onDelete: (fileId: string) => void;
}

function FileRow({ file, isSelected, onSelect, onDelete }: FileRowProps) {
  const Icon = getFileIcon(file.file_type);

  const handleDelete = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onDelete(file.id);
    },
    [file.id, onDelete]
  );

  return (
    <motion.div
      variants={itemVariants}
      layout
      onClick={() => onSelect(file.id)}
      className={`
        group flex items-center gap-2.5 px-3 py-2 rounded-md cursor-pointer
        text-sm transition-colors duration-150 relative
        ${
          isSelected
            ? "bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/20 glow-cyan"
            : "hover:bg-bg-hover text-text-secondary border border-transparent"
        }
      `}
    >
      {/* File type icon */}
      <Icon
        className={`w-4 h-4 shrink-0 ${
          isSelected ? "text-accent-cyan" : "text-text-muted"
        }`}
      />

      {/* File name and metadata */}
      <div className="flex-1 min-w-0">
        <p
          className={`text-sm truncate leading-tight ${
            isSelected ? "text-accent-cyan" : "text-text-primary"
          }`}
          title={file.file_name}
        >
          {truncateFilename(file.file_name)}
        </p>
        <p className="text-[10px] text-text-muted mt-0.5 leading-tight">
          {file.project_name}
          {file.project_name && " \u00b7 "}
          {formatRelativeDate(file.indexed_at)}
        </p>
      </div>

      {/* Item count badge */}
      <span
        className={`
          shrink-0 text-[10px] font-mono px-1.5 py-0.5 rounded
          ${
            isSelected
              ? "bg-accent-cyan/15 text-accent-cyan"
              : "bg-bg-tertiary text-text-muted"
          }
        `}
      >
        {file.item_count}
      </span>

      {/* Delete button - visible on hover */}
      <button
        onClick={handleDelete}
        className={`
          shrink-0 p-1 rounded transition-all duration-150
          opacity-0 group-hover:opacity-100
          hover:bg-status-danger/15 hover:text-status-danger
          ${isSelected ? "text-accent-cyan/50" : "text-text-muted"}
        `}
        title="Delete file"
      >
        <Trash2 className="w-3.5 h-3.5" />
      </button>
    </motion.div>
  );
}

// ── FileList Component ───────────────────────────────────────────────

export default function FileList() {
  const { files, selectedFileId, loadItems, deleteFile, loadFiles } =
    useBoQStore();

  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  const handleSelect = useCallback(
    (fileId: string) => {
      loadItems(fileId);
    },
    [loadItems]
  );

  const handleDelete = useCallback(
    (fileId: string) => {
      deleteFile(fileId);
    },
    [deleteFile]
  );

  // Empty state
  if (files.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="flex flex-col items-center justify-center py-8 gap-3"
      >
        <Inbox className="w-8 h-8 text-text-muted/50" />
        <div className="text-center">
          <p className="text-xs text-text-muted">No files uploaded yet</p>
          <p className="text-[10px] text-text-muted/60 mt-1">
            Upload XLSX, XLS, or CSV files to get started
          </p>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      variants={listVariants}
      initial="hidden"
      animate="visible"
      className="flex flex-col gap-1"
    >
      <AnimatePresence mode="popLayout">
        {files.map((file) => (
          <FileRow
            key={file.id}
            file={file}
            isSelected={selectedFileId === file.id}
            onSelect={handleSelect}
            onDelete={handleDelete}
          />
        ))}
      </AnimatePresence>
    </motion.div>
  );
}
