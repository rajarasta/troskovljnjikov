"use client";

import { useCallback, useState } from "react";
import { useBoQStore } from "@/stores/boqStore";

export function EditableCell({
  value,
  itemId,
  field,
}: {
  value: number;
  itemId: string;
  field: "quantity" | "unit_price";
}) {
  const updateWorkingItem = useBoQStore((s) => s.updateWorkingItem);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const parsed = parseFloat(e.target.value);
      updateWorkingItem(itemId, { [field]: isNaN(parsed) ? 0 : parsed });
    },
    [itemId, field, updateWorkingItem],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
    setIsDragOver(true);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);
      try {
        const raw = e.dataTransfer.getData("application/x-boq-cell");
        if (!raw) return;
        const data = JSON.parse(raw) as { value: number; field: string };
        if (data.field === field) {
          const val = typeof data.value === "number" ? data.value : parseFloat(String(data.value)) || 0;
          updateWorkingItem(itemId, { [field]: val });
        }
      } catch {
        // ignore malformed data
      }
    },
    [itemId, field, updateWorkingItem],
  );

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
      className={`
        transition-all duration-100
        ${isDragOver ? "ring-2 ring-accent-purple/40 ring-inset rounded bg-accent-purple/5" : ""}
      `}
    >
      <input
        type="number"
        step="any"
        value={value}
        onChange={handleChange}
        className="
          w-full bg-transparent font-mono text-xs text-right text-text-primary
          outline-none border border-transparent rounded px-1 py-0.5
          hover:border-border-default focus:border-accent-purple focus:ring-1 focus:ring-accent-purple/30
          transition-all duration-150
          [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none
        "
      />
    </div>
  );
}
