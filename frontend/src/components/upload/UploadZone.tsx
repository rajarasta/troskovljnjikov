"use client";

import { useState, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, Loader2, FileUp, AlertCircle } from "lucide-react";
import { useBoQStore } from "@/stores/boqStore";

const ACCEPTED_TYPES = new Set([
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", // .xlsx
  "application/vnd.ms-excel", // .xls
  "text/csv", // .csv
]);

const ACCEPTED_EXTENSIONS = new Set([".xlsx", ".xls", ".csv"]);

function isAcceptedFile(file: File): boolean {
  if (ACCEPTED_TYPES.has(file.type)) return true;
  const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  return ACCEPTED_EXTENSIONS.has(ext);
}

export default function UploadZone() {
  const { uploadFile, isLoading, error } = useBoQStore();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadQueue, setUploadQueue] = useState<number>(0);
  const dragCountRef = useRef(0);

  const processFiles = useCallback(
    async (fileList: FileList | File[]) => {
      const files = Array.from(fileList).filter(isAcceptedFile);
      if (files.length === 0) return;

      setUploadQueue(files.length);
      for (let i = 0; i < files.length; i++) {
        setUploadQueue(files.length - i);
        await uploadFile(files[i]);
      }
      setUploadQueue(0);
    },
    [uploadFile]
  );

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCountRef.current += 1;
    if (dragCountRef.current === 1) {
      setIsDragOver(true);
    }
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCountRef.current -= 1;
    if (dragCountRef.current === 0) {
      setIsDragOver(false);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      dragCountRef.current = 0;
      setIsDragOver(false);

      if (e.dataTransfer.files.length > 0) {
        processFiles(e.dataTransfer.files);
      }
    },
    [processFiles]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        processFiles(e.target.files);
      }
      // Reset input so selecting the same file again triggers onChange
      e.target.value = "";
    },
    [processFiles]
  );

  const handleClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    if (!isLoading) {
      fileInputRef.current?.click();
    }
  }, [isLoading]);

  const isUploading = isLoading || uploadQueue > 0;

  return (
    <div className="relative">
      <motion.div
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={handleClick}
        animate={{
          borderColor: isDragOver
            ? "rgba(0, 212, 255, 0.7)"
            : "rgba(42, 42, 64, 1)",
          boxShadow: isDragOver
            ? "0 0 30px rgba(0, 212, 255, 0.25), inset 0 0 30px rgba(0, 212, 255, 0.05)"
            : "0 0 0px rgba(0, 212, 255, 0)",
        }}
        transition={{ duration: 0.2 }}
        className={`
          glass-panel border-dashed border-2 rounded-lg
          transition-colors duration-200 cursor-pointer
          p-6 text-center group relative overflow-hidden
          ${isUploading ? "pointer-events-none" : ""}
        `}
      >
        {/* Animated background gradient on drag over */}
        <AnimatePresence>
          {isDragOver && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="absolute inset-0 bg-gradient-to-b from-accent-cyan/5 to-transparent pointer-events-none"
            />
          )}
        </AnimatePresence>

        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,.xls,.csv"
          multiple
          onChange={handleFileSelect}
          className="hidden"
        />

        <div className="relative z-10 flex flex-col items-center gap-3">
          <AnimatePresence mode="wait">
            {isUploading ? (
              <motion.div
                key="uploading"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                transition={{ duration: 0.2 }}
              >
                <Loader2 className="w-10 h-10 text-accent-cyan animate-spin" />
              </motion.div>
            ) : isDragOver ? (
              <motion.div
                key="dragover"
                initial={{ opacity: 0, scale: 0.8, y: 5 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.8, y: 5 }}
                transition={{ type: "spring", stiffness: 400, damping: 25 }}
              >
                <FileUp className="w-10 h-10 text-accent-cyan" />
              </motion.div>
            ) : (
              <motion.div
                key="idle"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                transition={{ duration: 0.2 }}
              >
                <Upload className="w-10 h-10 text-text-muted group-hover:text-accent-cyan transition-colors duration-200" />
              </motion.div>
            )}
          </AnimatePresence>

          <AnimatePresence mode="wait">
            {isUploading ? (
              <motion.div
                key="uploading-text"
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                className="flex flex-col items-center gap-1"
              >
                <p className="text-sm text-accent-cyan font-medium">
                  Uploading...
                </p>
                {uploadQueue > 1 && (
                  <p className="text-xs text-text-muted font-mono">
                    {uploadQueue} file{uploadQueue > 1 ? "s" : ""} remaining
                  </p>
                )}
              </motion.div>
            ) : isDragOver ? (
              <motion.p
                key="dragover-text"
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                className="text-sm text-accent-cyan font-medium"
              >
                Release to upload
              </motion.p>
            ) : (
              <motion.div
                key="idle-text"
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                className="flex flex-col items-center gap-1"
              >
                <p className="text-sm text-text-secondary group-hover:text-text-primary transition-colors">
                  Drop files or click to upload
                </p>
                <p className="text-xs text-text-muted">
                  XLSX, XLS, CSV supported
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>

      {/* Error display */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -8, height: 0 }}
            animate={{ opacity: 1, y: 0, height: "auto" }}
            exit={{ opacity: 0, y: -8, height: 0 }}
            className="mt-2 flex items-center gap-2 px-3 py-2 rounded-md
                       bg-status-danger/10 border border-status-danger/20 text-status-danger"
          >
            <AlertCircle className="w-3.5 h-3.5 shrink-0" />
            <p className="text-xs truncate">{error}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
