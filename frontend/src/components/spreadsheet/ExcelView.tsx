"use client";

import { useEffect, useRef, useState } from "react";
import { useBoQStore } from "@/stores/boqStore";
import { useSelectionStore } from "@/stores/selectionStore";
import { fetchWorkbookData } from "@/lib/api";
import type { BoQItem } from "@/lib/types";

import { createUniver, LocaleType, mergeLocales } from "@univerjs/presets";
import { UniverSheetsCorePreset } from "@univerjs/preset-sheets-core";
import UniverPresetSheetsCoreEnUS from "@univerjs/preset-sheets-core/locales/en-US";
import { UniverSheetsDrawingPreset } from "@univerjs/preset-sheets-drawing";
import UniverPresetSheetsDrawingEnUS from "@univerjs/preset-sheets-drawing/locales/en-US";

import "@univerjs/preset-sheets-core/lib/index.css";
import "@univerjs/preset-sheets-drawing/lib/index.css";

/**
 * Try to detect quantity and unit_price columns from row data
 * by matching header names and value patterns (Croatian/English)
 */
function extractPriceDataFromRow(
  rowData: string[],
  headerRow?: string[],
): { quantity: number; unit_price: number } {
  const result = { quantity: 0, unit_price: 0 };

  if (!headerRow || headerRow.length === 0) return result;

  // Look for columns matching common naming patterns (Croatian/English)
  const quantityPatterns = ["kol", "količina", "qty", "quantity", "kolicina"];
  const pricePatterns = ["cijena", "jc", "jed", "price", "unit price", "jedinična", "cijena"];
  const totalPatterns = ["ukupno", "total", "uc", "ukupno"];

  for (let i = 0; i < Math.min(headerRow.length, rowData.length); i++) {
    const header = headerRow[i]?.toLowerCase().trim() ?? "";
    const value = rowData[i]?.trim() ?? "";

    // Skip empty values
    if (!value) continue;

    // Try to parse as number
    const numValue = parseFloat(value.replace(/[^\d.,]/g, "").replace(",", "."));
    if (isNaN(numValue) || numValue === 0) continue;

    // Match quantity column (prioritize first match)
    if (
      result.quantity === 0 &&
      quantityPatterns.some((p) => header.includes(p))
    ) {
      result.quantity = numValue;
    }

    // Match unit price column (but not total)
    if (
      result.unit_price === 0 &&
      pricePatterns.some((p) => header.includes(p)) &&
      !totalPatterns.some((t) => header.includes(t))
    ) {
      result.unit_price = numValue;
    }
  }

  return result;
}

/** Apply or remove text wrap on every cell across all sheets */
function applyWrapToAllSheets(univerAPI: ReturnType<typeof createUniver>["univerAPI"]) {
  try {
    const workbook = univerAPI.getActiveWorkbook();
    if (!workbook) return;
    const sheet = workbook.getActiveSheet();
    if (!sheet) return;
    const maxRow = sheet.getMaxRows();
    const maxCol = sheet.getMaxColumns();
    if (maxRow > 0 && maxCol > 0) {
      sheet.getRange(0, 0, maxRow, maxCol).setWrap(true);
    }
  } catch {
    // Univer API may not be fully ready yet — ignore
  }
}

export default function ExcelView({ wrapAll = true }: { wrapAll?: boolean }) {
  const selectedFileId = useBoQStore((s) => s.selectedFileId);
  const files = useBoQStore((s) => s.files);
  const addSelection = useSelectionStore((s) => s.addSelection);
  const removeSelection = useSelectionStore((s) => s.removeSelection);

  // Find current file to access raw_preview and header_rows
  const currentFile = files.find((f) => f.id === selectedFileId);

  const containerRef = useRef<HTMLDivElement>(null);
  const univerRef = useRef<ReturnType<typeof createUniver> | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const excelSelectionIdRef = useRef<string | null>(null);
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

        // Fetch IWorkbookData from our backend
        const workbookData = await fetchWorkbookData(selectedFileId!);
        if (disposed) return;

        // Create Univer instance
        const result = createUniver({
          locale: LocaleType.EN_US,
          locales: {
            [LocaleType.EN_US]: mergeLocales(
              UniverPresetSheetsCoreEnUS,
              UniverPresetSheetsDrawingEnUS
            ),
          },
          presets: [
            UniverSheetsCorePreset({
              container: containerRef.current!,
            }),
            UniverSheetsDrawingPreset(),
          ],
        });

        if (disposed) {
          result.univerAPI.dispose();
          return;
        }

        univerRef.current = result;
        const { univerAPI } = result;

        // Create workbook directly from our data
        univerAPI.createWorkbook(workbookData);

        // Apply text wrap to all cells if enabled
        if (wrapAll) {
          applyWrapToAllSheets(univerAPI);
        }

        // Listen for selection changes -> trigger pipeline via selectionStore (debounced)
        univerAPI.addEvent(univerAPI.Event.SelectionChanged, (params: unknown) => {
          const { worksheet, selections } = params as {
            worksheet: { getRange: (r: number, c: number) => { getValue: () => unknown } | null };
            selections: Array<{ startRow: number; endRow: number; startColumn: number; endColumn: number }>;
          };
          if (!selections || selections.length === 0 || !worksheet) return;

          if (debounceRef.current) clearTimeout(debounceRef.current);
          debounceRef.current = setTimeout(() => {
            const cellData: Array<{ row: number; col: number; text: string }> = [];
            for (const sel of selections) {
              for (let r = sel.startRow; r <= sel.endRow; r++) {
                for (let c = sel.startColumn; c <= sel.endColumn; c++) {
                  const cell = worksheet.getRange(r, c);
                  const value = cell?.getValue();
                  if (value != null && String(value).trim()) {
                    cellData.push({ row: r, col: c, text: String(value).trim() });
                  }
                }
              }
            }

            if (cellData.length === 0) return;

            // Remove previous Excel-originated selection
            if (excelSelectionIdRef.current) {
              removeSelection(excelSelectionIdRef.current);
              excelSelectionIdRef.current = null;
            }

            // Get header row and raw preview for price extraction
            const sheetName = worksheet?.constructor?.name; // Try to get sheet name
            const headerRowIndex = currentFile?.header_rows ? Object.values(currentFile.header_rows)[0] : 0;
            const rawPreview = currentFile?.raw_preview ? Object.values(currentFile.raw_preview)[0] : null;
            const headerRow = rawPreview && headerRowIndex !== undefined ? rawPreview[headerRowIndex] : undefined;

            // Group cells by row to extract price data per row
            const rowMap = new Map<number, { cells: typeof cellData; priceData: ReturnType<typeof extractPriceDataFromRow> }>();
            for (const cell of cellData) {
              if (!rowMap.has(cell.row)) {
                const rowCells: typeof cellData = [];
                // Collect all cells in this row from raw preview
                if (rawPreview && cell.row < rawPreview.length) {
                  const rowData = rawPreview[cell.row];
                  const priceData = extractPriceDataFromRow(rowData, headerRow);
                  rowMap.set(cell.row, { cells: [cell], priceData });
                } else {
                  rowMap.set(cell.row, { cells: [cell], priceData: { quantity: 0, unit_price: 0 } });
                }
              } else {
                rowMap.get(cell.row)!.cells.push(cell);
              }
            }

            // Build synthetic BoQItems from grouped row data
            const syntheticItems: BoQItem[] = Array.from(rowMap.entries()).flatMap(
              ([rowNum, { cells, priceData }]) =>
                cells.map((cell) => ({
                  id: `excel-cell-${cell.row}-${cell.col}-${Date.now()}`,
                  file_id: selectedFileId!,
                  sheet_name: null,
                  row: cell.row,
                  item_number: null,
                  description: cell.text,
                  full_description: null,
                  parent_item_number: null,
                  unit: null,
                  quantity: priceData.quantity,
                  unit_price: priceData.unit_price,
                  total: priceData.quantity * priceData.unit_price,
                  project_name: null,
                  date: null,
                  material_price: null,
                  labor_price: null,
                  material_total: null,
                  labor_total: null,
                  notes: null,
                  drawing_path: null,
                  llm_response: null,
                  file_name: null,
                }))
            );

            // Debug: log synthetic items with their descriptions
            console.log("📊 ExcelView cellData:", cellData);
            console.log("📊 ExcelView syntheticItems created:", syntheticItems.map(item => ({ id: item.id, description: item.description })));

            const minRow = Math.min(...cellData.map((c) => c.row));
            const maxRow = Math.max(...cellData.map((c) => c.row));

            // Create selection -- triggers useSelectionPipeline
            const selectionId = addSelection(minRow, maxRow, syntheticItems);
            excelSelectionIdRef.current = selectionId;
            console.log("📊 ExcelView added selection:", { selectionId, itemCount: syntheticItems.length });
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
      if (excelSelectionIdRef.current) {
        removeSelection(excelSelectionIdRef.current);
        excelSelectionIdRef.current = null;
      }
      if (univerRef.current) {
        univerRef.current.univerAPI.dispose();
        univerRef.current = null;
      }
    };
  }, [selectedFileId, addSelection, removeSelection]);

  // Toggle wrap on existing workbook when prop changes
  useEffect(() => {
    if (!univerRef.current) return;
    const { univerAPI } = univerRef.current;
    try {
      const workbook = univerAPI.getActiveWorkbook();
      if (!workbook) return;
      const sheet = workbook.getActiveSheet();
      if (!sheet) return;
      const maxRow = sheet.getMaxRows();
      const maxCol = sheet.getMaxColumns();
      if (maxRow > 0 && maxCol > 0) {
        sheet.getRange(0, 0, maxRow, maxCol).setWrap(!!wrapAll);
      }
    } catch {
      // ignore
    }
  }, [wrapAll]);

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
