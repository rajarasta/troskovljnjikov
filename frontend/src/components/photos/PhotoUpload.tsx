"use client";

import { useState, useCallback, useRef, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Camera, Loader2, Sparkles, X, ImagePlus } from "lucide-react";

interface PhotoUploadProps {
  onAnalyze: (file: File) => void;
  isAnalyzing?: boolean;
}

const ACCEPTED_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
]);

const ACCEPTED_EXTENSIONS = new Set([".jpg", ".jpeg", ".png", ".webp"]);

function isAcceptedImage(file: File): boolean {
  if (ACCEPTED_TYPES.has(file.type)) return true;
  const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  return ACCEPTED_EXTENSIONS.has(ext);
}

export default function PhotoUpload({
  onAnalyze,
  isAnalyzing = false,
}: PhotoUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragCountRef = useRef(0);

  const previewUrl = useMemo(() => {
    if (!file) return null;
    return URL.createObjectURL(file);
  }, [file]);

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

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCountRef.current = 0;
    setIsDragOver(false);

    const dropped = Array.from(e.dataTransfer.files).find(isAcceptedImage);
    if (dropped) {
      setFile(dropped);
    }
  }, []);

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = e.target.files?.[0];
      if (selected && isAcceptedImage(selected)) {
        setFile(selected);
      }
      e.target.value = "";
    },
    []
  );

  const handleClickZone = useCallback(() => {
    if (!isAnalyzing) {
      fileInputRef.current?.click();
    }
  }, [isAnalyzing]);

  const handleClear = useCallback(() => {
    setFile(null);
  }, []);

  const handleAnalyze = useCallback(() => {
    if (file && !isAnalyzing) {
      onAnalyze(file);
    }
  }, [file, isAnalyzing, onAnalyze]);

  return (
    <div className="flex flex-col gap-3">
      <input
        ref={fileInputRef}
        type="file"
        accept=".jpg,.jpeg,.png,.webp"
        onChange={handleFileSelect}
        className="hidden"
      />

      <AnimatePresence mode="wait">
        {!file ? (
          /* ── Drop Zone ──────────────────────────────────── */
          <motion.div
            key="dropzone"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onClick={handleClickZone}
            className={`
              glass-panel glow-purple border-dashed border-2 rounded-lg
              cursor-pointer p-8 flex flex-col items-center justify-center gap-3
              transition-colors duration-200 relative overflow-hidden
              ${isDragOver ? "border-accent-purple/60" : "border-border-default"}
            `}
          >
            {/* Drag-over gradient overlay */}
            <AnimatePresence>
              {isDragOver && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="absolute inset-0 bg-gradient-to-b from-accent-purple/10 to-transparent pointer-events-none"
                />
              )}
            </AnimatePresence>

            <div className="relative z-10 flex flex-col items-center gap-3">
              <motion.div
                animate={isDragOver ? { scale: 1.1, y: -2 } : { scale: 1, y: 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
              >
                <Camera
                  className={`w-10 h-10 transition-colors duration-200 ${
                    isDragOver ? "text-accent-purple" : "text-text-muted"
                  }`}
                />
              </motion.div>

              <div className="flex flex-col items-center gap-1 text-center">
                <p
                  className={`text-sm font-medium transition-colors duration-200 ${
                    isDragOver ? "text-accent-purple" : "text-text-secondary"
                  }`}
                >
                  {isDragOver ? "Release to upload" : "Drop photo or click to browse"}
                </p>
                <p className="text-[10px] text-text-muted uppercase tracking-wider">
                  JPG, PNG, WEBP
                </p>
              </div>
            </div>
          </motion.div>
        ) : (
          /* ── Preview + Actions ──────────────────────────── */
          <motion.div
            key="preview"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="glass-panel glow-purple rounded-lg overflow-hidden"
          >
            {/* Thumbnail */}
            <div className="relative aspect-video bg-bg-tertiary">
              {previewUrl && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={previewUrl}
                  alt="Upload preview"
                  className="w-full h-full object-cover"
                />
              )}

              {/* Clear button */}
              {!isAnalyzing && (
                <button
                  type="button"
                  onClick={handleClear}
                  className="absolute top-2 right-2 w-6 h-6 rounded-full
                             bg-bg-primary/80 backdrop-blur-sm border border-border-default
                             flex items-center justify-center
                             hover:bg-status-danger/20 hover:border-status-danger/40
                             transition-colors duration-150 cursor-pointer"
                >
                  <X className="w-3.5 h-3.5 text-text-secondary" />
                </button>
              )}

              {/* File name overlay */}
              <div className="absolute bottom-0 inset-x-0 px-3 py-1.5 bg-gradient-to-t from-bg-primary/90 to-transparent">
                <div className="flex items-center gap-1.5">
                  <ImagePlus className="w-3 h-3 text-accent-purple shrink-0" />
                  <span className="text-[10px] font-mono text-text-secondary truncate">
                    {file.name}
                  </span>
                </div>
              </div>
            </div>

            {/* Analyze button */}
            <div className="px-3 py-2.5">
              <motion.button
                type="button"
                onClick={handleAnalyze}
                disabled={isAnalyzing}
                whileHover={isAnalyzing ? {} : { scale: 1.01 }}
                whileTap={isAnalyzing ? {} : { scale: 0.98 }}
                className={`
                  w-full flex items-center justify-center gap-2 px-4 py-2 rounded-md
                  text-xs font-semibold uppercase tracking-wider
                  transition-all duration-200 cursor-pointer
                  ${isAnalyzing
                    ? "bg-accent-purple/20 text-accent-purple/60 cursor-not-allowed"
                    : "bg-accent-purple text-white hover:bg-accent-purple/90 glow-purple"
                  }
                `}
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    Analyze with AI
                  </>
                )}
              </motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
