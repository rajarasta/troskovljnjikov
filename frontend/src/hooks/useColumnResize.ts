import { useEffect, useRef, useState } from "react";
import type { RefObject } from "react";

/**
 * Hook for managing resizable column widths with drag handles.
 *
 * @param columnCount - Number of columns
 * @param containerRef - Ref to the main container for measuring available width
 * @param sideWidth - Default width for side columns (first and last)
 * @param minWidth - Minimum width per column during resize
 */
export function useColumnResize(
  columnCount: number,
  containerRef: RefObject<HTMLDivElement | null>,
  sideWidth = 280,
  minWidth = 150,
) {
  const [colWidths, setColWidths] = useState<number[]>(() =>
    Array(columnCount).fill(sideWidth),
  );
  const dragRef = useRef<{ idx: number; startX: number; startW: number[] } | null>(null);

  // Initialize column widths from actual container size
  useEffect(() => {
    if (!containerRef.current) return;
    const handleCount = columnCount - 1;
    const available = containerRef.current.clientWidth - 24 - handleCount * 12; // padding + handles
    const mid = Math.max(200, (available - sideWidth * 2) / (columnCount - 2));
    const widths = Array(columnCount).fill(mid);
    widths[0] = sideWidth;
    widths[columnCount - 1] = sideWidth;
    setColWidths(widths);
  }, [columnCount, containerRef, sideWidth]);

  const onResizeStart = (handleIndex: number) => (e: React.MouseEvent) => {
    e.preventDefault();
    dragRef.current = { idx: handleIndex, startX: e.clientX, startW: [...colWidths] };
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    const onMove = (ev: MouseEvent) => {
      if (!dragRef.current) return;
      const { idx, startX, startW } = dragRef.current;
      const delta = ev.clientX - startX;
      const newL = startW[idx] + delta;
      const newR = startW[idx + 1] - delta;
      if (newL >= minWidth && newR >= minWidth) {
        const next = [...startW];
        next[idx] = newL;
        next[idx + 1] = newR;
        setColWidths(next);
      }
    };

    const onUp = () => {
      dragRef.current = null;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };

    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  };

  return { colWidths, onResizeStart };
}
