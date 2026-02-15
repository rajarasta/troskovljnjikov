import { useEffect, useRef, useCallback } from "react";
import { useBoQStore } from "@/stores/boqStore";

/**
 * Synchronizes row heights between Current BOQ and Working Copy.
 * When item counts match, forces each row pair to max(height_a, height_b).
 * When counts differ, resets to natural heights (scroll sync only).
 */
export function useRowAlignment(
  boqRef: React.RefObject<HTMLDivElement | null>,
  workingRef: React.RefObject<HTMLDivElement | null>,
) {
  const items = useBoQStore((s) => s.items);
  const workingItems = useBoQStore((s) => s.workingItems);
  const aligned = useRef(false);

  const alignRows = useCallback(() => {
    if (!boqRef.current || !workingRef.current) return;

    const boqRows = boqRef.current.querySelectorAll<HTMLTableRowElement>("tbody tr[data-row-index]");
    const workingRows = workingRef.current.querySelectorAll<HTMLTableRowElement>("tbody tr[data-row-index]");

    // Reset all heights first
    boqRows.forEach((r) => (r.style.height = ""));
    workingRows.forEach((r) => (r.style.height = ""));

    if (items.length !== workingItems.length) {
      aligned.current = false;
      return;
    }

    // Force equal heights
    const count = Math.min(boqRows.length, workingRows.length);
    for (let i = 0; i < count; i++) {
      const h = Math.max(boqRows[i].offsetHeight, workingRows[i].offsetHeight);
      boqRows[i].style.height = `${h}px`;
      workingRows[i].style.height = `${h}px`;
    }
    aligned.current = true;
  }, [boqRef, workingRef, items.length, workingItems.length]);

  // Re-align on item changes
  useEffect(() => {
    const timer = setTimeout(alignRows, 50);
    return () => clearTimeout(timer);
  }, [alignRows]);

  // Re-align on window resize
  useEffect(() => {
    window.addEventListener("resize", alignRows);
    return () => window.removeEventListener("resize", alignRows);
  }, [alignRows]);

  return { alignRows };
}
