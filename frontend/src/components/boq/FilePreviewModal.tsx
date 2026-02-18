"use client";

import { useEffect, useState } from "react";
import { X, Loader2, WrapText } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useFilePreviewStore } from "@/stores/filePreviewStore";
import { fetchFileItems } from "@/lib/api";
import type { BoQItem } from "@/lib/types";
import { formatNumber } from "@/lib/boqTableConfig";

export default function FilePreviewModal() {
  const { previewFileId, previewFileName, closePreview } = useFilePreviewStore();
  const [items, setItems] = useState<BoQItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wrapText, setWrapText] = useState(true);

  useEffect(() => {
    if (!previewFileId) return;

    setLoading(true);
    setError(null);
    setItems([]);

    fetchFileItems(previewFileId)
      .then((data) => setItems(data))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load file"))
      .finally(() => setLoading(false));
  }, [previewFileId]);

  return (
    <AnimatePresence>
      {previewFileId && (
        <>
          {/* Backdrop */}
          <motion.div
            key="preview-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={closePreview}
            className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm"
          />

          {/* Modal */}
          <motion.div
            key="preview-modal"
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="fixed inset-y-4 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 flex flex-col rounded-lg border border-border-default bg-bg-primary shadow-2xl overflow-hidden max-w-4xl w-[calc(100%-2rem)]"
          >
            {/* Header */}
            <div className="shrink-0 flex items-center justify-between px-1 py-3 border-b border-border-default bg-bg-secondary/50">
              <div>
                <h2 className="text-sm font-semibold text-text-primary">File Preview</h2>
                <p className="text-xs text-text-muted mt-0.5">{previewFileName}</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setWrapText((w) => !w)}
                  title={wrapText ? "Compact (no wrap)" : "Wrap text"}
                  className={`p-1 rounded transition-colors ${
                    wrapText
                      ? "bg-accent-purple/15 text-accent-purple"
                      : "text-text-muted hover:text-text-secondary"
                  }`}
                >
                  <WrapText className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={closePreview}
                  className="p-1.5 rounded hover:bg-bg-hover text-text-muted hover:text-text-primary transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto min-h-0">
              {loading && (
                <div className="flex items-center justify-center h-full gap-2 text-text-muted">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">Loading file...</span>
                </div>
              )}

              {error && (
                <div className="flex items-center justify-center h-full text-status-danger text-sm">
                  Error: {error}
                </div>
              )}

              {!loading && !error && items.length > 0 && (
                <table className="w-full text-xs border-collapse">
                  <thead className="sticky top-0 z-10 bg-bg-secondary">
                    <tr>
                      <th className="border border-border-default px-1 py-1.5 text-left font-semibold text-text-muted text-[10px] uppercase tracking-wider">
                        R.br.
                      </th>
                      <th className="border border-border-default px-1 py-1.5 text-left font-semibold text-text-muted text-[10px] uppercase tracking-wider">
                        Opis stavke
                      </th>
                      <th className="border border-border-default px-1 py-1.5 text-center font-semibold text-text-muted text-[10px] uppercase tracking-wider w-12">
                        JM
                      </th>
                      <th className="border border-border-default px-1 py-1.5 text-right font-semibold text-text-muted text-[10px] uppercase tracking-wider w-16">
                        Kol.
                      </th>
                      <th className="border border-border-default px-1 py-1.5 text-right font-semibold text-text-muted text-[10px] uppercase tracking-wider w-16">
                        JC [€]
                      </th>
                      <th className="border border-border-default px-1 py-1.5 text-right font-semibold text-text-muted text-[10px] uppercase tracking-wider w-16">
                        UC [€]
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((item) => (
                      <tr key={item.id} className="hover:bg-bg-hover transition-colors">
                        <td className="border border-border-default px-1 py-1 font-mono text-[9px] text-text-muted whitespace-nowrap">
                          {item.item_number ?? "—"}
                        </td>
                        <td
                          className={`border border-border-default px-1 py-1 text-[9px] text-text-primary ${
                            wrapText ? "whitespace-pre-wrap break-words max-w-sm" : "max-w-xs truncate"
                          }`}
                        >
                          {item.description}
                        </td>
                        <td className="border border-border-default px-1 py-1 text-center text-[9px] text-text-muted whitespace-nowrap">
                          {item.unit ?? "—"}
                        </td>
                        <td className="border border-border-default px-1 py-1 text-right font-mono text-[9px] text-text-primary whitespace-nowrap">
                          {formatNumber(item.quantity)}
                        </td>
                        <td className="border border-border-default px-1 py-1 text-right font-mono text-[9px] text-text-primary whitespace-nowrap">
                          {formatNumber(item.unit_price)}
                        </td>
                        <td className="border border-border-default px-1 py-1 text-right font-mono text-[9px] text-text-primary whitespace-nowrap">
                          {formatNumber(item.total)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              {!loading && !error && items.length === 0 && (
                <div className="flex items-center justify-center h-full text-text-muted text-sm">
                  No items in this file
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
