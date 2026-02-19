"use client";

import { useMemo } from "react";
import { useBoQStore } from "@/stores/boqStore";

// Column letter helper: 0→A, 1→B, ... 25→Z
function colLetter(index: number): string {
  return String.fromCharCode(65 + index);
}

export default function SheetPreview() {
  const files = useBoQStore((s) => s.files);
  const selectedFileId = useBoQStore((s) => s.selectedFileId);

  const { sheetName, rows, headerRowIndex } = useMemo(() => {
    if (!selectedFileId) return { sheetName: null, rows: [], headerRowIndex: null };
    const file = files.find((f) => f.id === selectedFileId);
    if (!file?.raw_preview) return { sheetName: null, rows: [], headerRowIndex: null };

    // Use first sheet's preview
    const entries = Object.entries(file.raw_preview);
    if (entries.length === 0) return { sheetName: null, rows: [], headerRowIndex: null };

    const [name, data] = entries[0];
    const hrIdx = file.header_rows?.[name] ?? null;
    return { sheetName: name, rows: data, headerRowIndex: hrIdx };
  }, [files, selectedFileId]);

  if (!sheetName || rows.length === 0) return null;

  // Determine column count from widest row (trim trailing empty cells)
  const colCount = rows.reduce((max, row) => {
    let last = row.length - 1;
    while (last >= 0 && !row[last]) last--;
    return Math.max(max, last + 1);
  }, 0);

  if (colCount === 0) return null;

  // Get header labels from detected header row
  const colHeaders = headerRowIndex != null && headerRowIndex >= 0 && rows[headerRowIndex]
    ? rows[headerRowIndex]
    : null;

  return (
    <div className="border border-border-default rounded overflow-hidden">
      {/* Sheet tab */}
      <div className="flex items-center gap-1 px-2 py-1 bg-bg-tertiary border-b border-border-default">
        <span className="text-[10px] text-text-muted font-mono uppercase tracking-wider">
          Raw preview
        </span>
        <span className="text-[10px] text-accent-cyan font-mono ml-auto">
          {sheetName}
        </span>
      </div>

      {/* Grid */}
      <div className="overflow-x-auto">
        <table className="text-[11px] border-collapse w-full font-mono">
          {/* Column headers: blank corner + A, B, C ... */}
          <thead>
            <tr className="bg-bg-tertiary">
              <th className="w-8 min-w-[32px] px-1 py-0.5 text-center text-text-muted border-r border-b border-border-default" />
              {Array.from({ length: colCount }, (_, i) => {
                const headerText = colHeaders?.[i]?.trim() || colLetter(i);
                return (
                  <th
                    key={i}
                    className="px-2 py-0.5 text-center text-text-muted font-medium border-r border-b border-border-default last:border-r-0 truncate max-w-[180px]"
                    title={headerText}
                  >
                    {headerText}
                  </th>
                );
              })}
            </tr>
          </thead>

          <tbody>
            {rows.map((row, rIdx) => (
              <tr key={rIdx} className="hover:bg-bg-hover/40">
                {/* Row number */}
                <td className="px-1 py-0.5 text-center text-text-muted bg-bg-tertiary border-r border-b border-border-default font-medium">
                  {rIdx + 1}
                </td>

                {/* Data cells */}
                {Array.from({ length: colCount }, (_, cIdx) => {
                  const val = row[cIdx] ?? "";
                  return (
                    <td
                      key={cIdx}
                      className="px-2 py-0.5 text-text-primary border-r border-b border-border-default last:border-r-0 whitespace-nowrap max-w-[180px] truncate"
                      title={val}
                    >
                      {val}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
