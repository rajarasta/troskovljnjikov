"use client";

import { useEffect, useRef, useState } from "react";
import { useBoQStore } from "@/stores/boqStore";
import { useMatchStore } from "@/stores/matchStore";
import { fetchXlsxFile } from "@/lib/api";

import { createUniver, LocaleType, mergeLocales } from "@univerjs/presets";
import { UniverSheetsCorePreset } from "@univerjs/preset-sheets-core";
import UniverPresetSheetsCoreEnUS from "@univerjs/preset-sheets-core/locales/en-US";
import { UniverSheetsDrawingPreset } from "@univerjs/preset-sheets-drawing";
import UniverPresetSheetsDrawingEnUS from "@univerjs/preset-sheets-drawing/locales/en-US";
import { UniverSheetsAdvancedPreset } from "@univerjs/preset-sheets-advanced";
import UniverPresetSheetsAdvancedEnUS from "@univerjs/preset-sheets-advanced/locales/en-US";

import "@univerjs/preset-sheets-core/lib/index.css";
import "@univerjs/preset-sheets-drawing/lib/index.css";
import "@univerjs/preset-sheets-advanced/lib/index.css";

export default function ExcelView() {
  const selectedFileId = useBoQStore((s) => s.selectedFileId);
  const startLookup = useMatchStore((s) => s.startLookup);

  const containerRef = useRef<HTMLDivElement>(null);
  const univerRef = useRef<ReturnType<typeof createUniver> | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedFileId || !containerRef.current) return;

    let disposed = false;

    async function init() {
      setLoading(true);
      setError(null);

      try {
        // Clean up previous instance
        if (univerRef.current) {
          univerRef.current.univerAPI.dispose();
          univerRef.current = null;
        }

        // Clear container
        if (containerRef.current) {
          containerRef.current.innerHTML = "";
        }

        // Fetch the xlsx file
        const file = await fetchXlsxFile(selectedFileId!);
        if (disposed) return;

        // Create Univer instance
        const result = createUniver({
          locale: LocaleType.EN_US,
          locales: {
            [LocaleType.EN_US]: mergeLocales(
              UniverPresetSheetsCoreEnUS,
              UniverPresetSheetsDrawingEnUS,
              UniverPresetSheetsAdvancedEnUS
            ),
          },
          presets: [
            UniverSheetsCorePreset({
              container: containerRef.current!,
            }),
            UniverSheetsDrawingPreset(),
            UniverSheetsAdvancedPreset(),
          ],
        });

        if (disposed) {
          result.univerAPI.dispose();
          return;
        }

        univerRef.current = result;
        const { univerAPI } = result;

        // Import the xlsx file
        const snapshot = await univerAPI.importXLSXToSnapshotAsync(file);
        if (disposed) {
          univerAPI.dispose();
          return;
        }

        if (snapshot) {
          univerAPI.createWorkbook(snapshot);
        }

        // Set read-only mode
        const workbook = univerAPI.getActiveWorkbook();
        if (workbook) {
          workbook.setEditable(false);
        }

        // Listen for selection changes -> trigger RAG lookup (debounced)
        univerAPI.addEvent(univerAPI.Event.SelectionChanged, (params) => {
          const { worksheet, selections } = params;
          if (!selections || selections.length === 0 || !worksheet) return;

          if (debounceRef.current) clearTimeout(debounceRef.current);
          debounceRef.current = setTimeout(() => {
            const texts: string[] = [];
            for (const sel of selections) {
              for (let r = sel.startRow; r <= sel.endRow; r++) {
                for (let c = sel.startColumn; c <= sel.endColumn; c++) {
                  const cell = worksheet.getRange(r, c);
                  const value = cell?.getValue();
                  if (value != null && String(value).trim()) {
                    texts.push(String(value).trim());
                  }
                }
              }
            }
            if (texts.length > 0) {
              startLookup(texts.join(" "));
            }
          }, 500);
        });

        setLoading(false);
      } catch (err) {
        if (!disposed) {
          setError(
            err instanceof Error ? err.message : "Failed to load Excel file"
          );
          setLoading(false);
        }
      }
    }

    init();

    return () => {
      disposed = true;
      if (debounceRef.current) clearTimeout(debounceRef.current);
      if (univerRef.current) {
        univerRef.current.univerAPI.dispose();
        univerRef.current = null;
      }
    };
  }, [selectedFileId, startLookup]);

  if (!selectedFileId) {
    return (
      <div className="flex items-center justify-center h-full text-text-muted text-sm">
        Upload a file to view Excel preview
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col min-h-0">
      {loading && (
        <div className="flex items-center justify-center h-full text-text-muted text-sm">
          Loading Excel view...
        </div>
      )}
      {error && (
        <div className="flex items-center justify-center h-full text-red-400 text-sm">
          {error}
        </div>
      )}
      <div
        ref={containerRef}
        className="flex-1 min-h-0 max-w-[900px]"
        style={{ display: loading || error ? "none" : "block" }}
      />
    </div>
  );
}
