"use client";

import { useEffect } from "react";
import { useBoQStore } from "@/stores/boqStore";
import { useSelectionStore } from "@/stores/selectionStore";
import { useMatchStore } from "@/stores/matchStore";

/**
 * Global keyboard navigation for the turbo selection loop.
 * Disabled when focus is inside an input/textarea/contenteditable element.
 *
 * Shortcuts:
 *   Tab / ArrowDown   → select next item in spreadsheet
 *   Shift+Tab / ArrowUp → select previous item
 *   Enter             → apply top match suggestion price
 *   Escape            → clear all selections
 *   1-5               → apply price from match result at that position
 */
export function useKeyboardNav() {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Don't intercept when typing in inputs
      const tag = (e.target as HTMLElement)?.tagName;
      const editable = (e.target as HTMLElement)?.isContentEditable;
      if (tag === "INPUT" || tag === "TEXTAREA" || editable) return;

      const items = useBoQStore.getState().items;
      const selStore = useSelectionStore.getState();
      const activeSel = selStore.selections.find((s) => s.id === selStore.activeSelectionId);

      if (e.key === "Tab" || e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        const direction = (e.key === "Tab" && e.shiftKey) || e.key === "ArrowUp" ? -1 : 1;
        const currentIndex = activeSel ? activeSel.endIndex : -1;
        const nextIndex = Math.max(0, Math.min(items.length - 1, currentIndex + direction));

        if (nextIndex >= 0 && nextIndex < items.length) {
          selStore.addSelection(nextIndex, nextIndex, [items[nextIndex]]);
        }
        return;
      }

      if (e.key === "Escape") {
        e.preventDefault();
        selStore.clearAll();
        return;
      }

      // Enter → apply top match
      if (e.key === "Enter" && activeSel) {
        e.preventDefault();
        applyMatchAtIndex(activeSel.id, activeSel.items[0]?.id, 0);
        return;
      }

      // Number keys 1-5 → apply specific match
      if (activeSel && e.key >= "1" && e.key <= "5") {
        const matchIndex = parseInt(e.key) - 1;
        applyMatchAtIndex(activeSel.id, activeSel.items[0]?.id, matchIndex);
        return;
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);
}

function applyMatchAtIndex(selectionId: string, targetItemId: string | undefined, index: number) {
  if (!targetItemId) return;

  const matchState = useMatchStore.getState().resultsBySelection[selectionId];
  if (!matchState?.matches.length) return;

  const match = matchState.matches[index];
  if (!match || match.item.unit_price == null) return;

  useBoQStore.getState().updateWorkingItem(targetItemId, {
    unit_price: match.item.unit_price,
  });
}
