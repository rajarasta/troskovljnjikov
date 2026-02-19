"use client";

<<<<<<< HEAD
import ColumnHeader from "@/components/layout/ColumnHeader";

export default function ChangesPanel() {
  return (
    <div className="glass-panel flex flex-col min-h-0 h-full">
      <ColumnHeader
        title="Changes"
        accent="cyan"
        badge="0"
      />
      <div className="flex-1 overflow-auto p-4">
        <div className="text-center text-text-muted text-sm py-8">
          No changes yet
        </div>
=======
import { useEffect } from "react";
import { useBoQStore } from "@/stores/boqStore";
import { useChangesStore, type BoQChange } from "@/stores/changesStore";
import ColumnHeader from "@/components/layout/ColumnHeader";
import { Undo2 } from "lucide-react";

const FIELD_LABELS: Record<BoQChange["field"], string> = {
  quantity: "Qty",
  unit_price: "Unit Price",
  total: "Total",
  description: "Description",
};

function formatNumber(n: number): string {
  return n.toLocaleString("hr-HR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function NumericChangeRow({ change }: { change: BoQChange & { oldValue: number; newValue: number } }) {
  const { revertChange } = useChangesStore();
  const delta = change.newValue - change.oldValue;
  const isIncrease = delta > 0;

  return (
    <div className="px-3 py-2 border-b border-border-default last:border-b-0 hover:bg-bg-hover/50 transition-colors group">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-[11px] font-mono text-text-muted">
            {change.itemNumber ?? `Row ${change.row}`}
            <span className="ml-1.5 text-[10px] px-1 py-0.5 rounded bg-accent-amber/10 text-accent-amber font-medium">
              {FIELD_LABELS[change.field]}
            </span>
          </div>
          <div className="text-xs text-text-secondary truncate mt-0.5">
            {change.description}
          </div>
        </div>
        <button
          onClick={() => revertChange(change.itemId, change.field)}
          className="shrink-0 opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-bg-tertiary transition-all"
          title="Revert"
        >
          <Undo2 className="w-3 h-3 text-text-muted" />
        </button>
      </div>
      <div className="flex items-center gap-2 mt-1 text-[11px] font-mono">
        <span className="text-text-muted line-through">{formatNumber(change.oldValue)}</span>
        <span className="text-text-muted">&rarr;</span>
        <span className="text-text-primary font-medium">{formatNumber(change.newValue)}</span>
        <span className={`ml-auto text-[10px] ${isIncrease ? "text-accent-amber" : "text-accent-emerald"}`}>
          {isIncrease ? "+" : ""}{formatNumber(delta)}
        </span>
      </div>
    </div>
  );
}

function DescriptionChangeRow({ change }: { change: BoQChange & { oldValue: string; newValue: string } }) {
  const { revertChange } = useChangesStore();

  return (
    <div className="px-3 py-2 border-b border-border-default last:border-b-0 hover:bg-bg-hover/50 transition-colors group">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-[11px] font-mono text-text-muted">
            {change.itemNumber ?? `Row ${change.row}`}
            <span className="ml-1.5 text-[10px] px-1 py-0.5 rounded bg-accent-purple/10 text-accent-purple font-medium">
              {FIELD_LABELS[change.field]}
            </span>
          </div>
        </div>
        <button
          onClick={() => revertChange(change.itemId, change.field)}
          className="shrink-0 opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-bg-tertiary transition-all"
          title="Revert"
        >
          <Undo2 className="w-3 h-3 text-text-muted" />
        </button>
      </div>
      <div className="mt-1 text-[11px] space-y-0.5">
        <div className="text-text-muted line-through truncate">{change.oldValue}</div>
        <div className="text-text-primary truncate">{change.newValue}</div>
      </div>
    </div>
  );
}

function ChangeRow({ change }: { change: BoQChange }) {
  if (change.field === "description") {
    return <DescriptionChangeRow change={change as BoQChange & { oldValue: string; newValue: string }} />;
  }
  return <NumericChangeRow change={change as BoQChange & { oldValue: number; newValue: number }} />;
}

export default function ChangesPanel() {
  const { items, workingItems } = useBoQStore();
  const { changes, recompute, revertAll } = useChangesStore();

  // Recompute changes whenever workingItems change
  useEffect(() => {
    recompute();
  }, [workingItems, recompute]);

  return (
    <div className="glass-panel flex flex-col min-h-0 h-full overflow-hidden">
      <ColumnHeader
        title="Changes"
        accent="amber"
        badge={changes.length > 0 ? `${changes.length}` : undefined}
        actions={
          changes.length > 0 ? (
            <button
              onClick={revertAll}
              className="px-2 py-0.5 text-[10px] font-mono rounded text-text-muted hover:text-accent-amber hover:bg-accent-amber/10 transition-colors"
            >
              Revert all
            </button>
          ) : undefined
        }
      />
      <div className="flex-1 overflow-y-auto min-h-0">
        {changes.length === 0 ? (
          <div className="flex items-center justify-center h-full p-4">
            <p className="text-xs text-text-muted text-center">
              No changes yet. Edit prices or quantities in the BOQ to see them here.
            </p>
          </div>
        ) : (
          changes.map((c) => (
            <ChangeRow key={`${c.itemId}-${c.field}`} change={c} />
          ))
        )}
>>>>>>> 775e691 (chore: finalize all worktree changes before making this the main branch)
      </div>
    </div>
  );
}
