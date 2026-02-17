"use client";

import { Check } from "lucide-react";
import { formatNumber } from "@/lib/boqTableConfig";
import { useBoQStore } from "@/stores/boqStore";
import { useSelectionStore } from "@/stores/selectionStore";
import { useFilePreviewStore } from "@/stores/filePreviewStore";
import type { MatchResult, MatchGroup } from "@/lib/types";

const COLUMNS = [
  { key: "item_number", label: "R.br.", width: "42px", align: "left" as const },
  { key: "description", label: "Opis stavke", width: undefined, align: "left" as const },
  { key: "unit", label: "JM", width: "32px", align: "left" as const },
  { key: "quantity", label: "Kol.", width: "46px", align: "right" as const },
  { key: "unit_price", label: "JC [\u20ac]", width: "62px", align: "right" as const },
  { key: "total", label: "UC [\u20ac]", width: "62px", align: "right" as const },
  { key: "apply", label: "", width: "28px", align: "center" as const },
] as const;

const COL_COUNT = COLUMNS.length;

interface Props {
  matches: MatchResult[];
  wrapText: boolean;
  groups?: MatchGroup[] | null;
  isComposite?: boolean;
  parentDescription?: string | null;
  refQty?: number | null;
  refPrice?: number | null;
}

function mulLabel(ref: number | null | undefined, val: number): string | null {
  if (!ref || ref === 0 || !val) return null;
  const r = val / ref;
  if (Math.abs(r - 1) < 0.005) return null;
  return `${r.toFixed(1)}x`;
}

function mulColor(ref: number, val: number): string {
  const r = val / ref;
  if (r >= 0.9 && r <= 1.1) return "text-green-400";
  if (r >= 0.5 && r <= 2.0) return "text-amber-400";
  return "text-red-400";
}

function MatchRow({ match, wrapText, refQty, refPrice }: { match: MatchResult; wrapText: boolean; refQty?: number | null; refPrice?: number | null }) {
  const { item, similarity } = match;
  const pct = Math.round((similarity ?? 0) * 100);
  const qtyMul = mulLabel(refQty, item.quantity ?? 0);
  const priceMul = mulLabel(refPrice, item.unit_price ?? 0);

  return (
    <tr className="hover:bg-bg-hover transition-colors duration-100">
      {/* R.br. */}
      <td className="border border-border-default px-1 py-1 font-mono text-[10px] text-text-muted whitespace-nowrap align-top">
        {item.item_number ?? "\u2014"}
      </td>

      {/* Description */}
      <td
        className={`
          border border-border-default px-1.5 py-1 text-text-primary align-top
          ${wrapText ? "whitespace-pre-wrap break-words" : "whitespace-nowrap overflow-hidden text-ellipsis max-w-0"}
        `}
      >
        {item.description ?? ""}
        <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
          <span className="text-[9px] font-mono text-text-muted">
            {pct}%
          </span>
          {match.llm_confidence != null && (
            <span className="text-[9px] font-mono text-accent-amber" title={match.llm_reasoning ?? ""}>
              LLM:{match.llm_confidence}
            </span>
          )}
          {item.file_name && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                const fileName = item.file_name;
                if (fileName) {
                  console.log("👁️ Preview file:", item.file_id, fileName);
                  useFilePreviewStore.getState().setPreviewFile(item.file_id, fileName);
                }
              }}
              className="text-[9px] text-accent-purple hover:text-accent-purple/70 hover:underline truncate max-w-[120px] transition-colors cursor-pointer"
              title={`Click to preview ${item.file_name}`}
            >
              {item.file_name}
            </button>
          )}
          {(item.project_name || item.date) && (
            <span className="text-[9px] text-text-muted truncate">
              {item.project_name ?? ""}
              {item.project_name && item.date ? " \u00b7 " : ""}
              {item.date ?? ""}
            </span>
          )}
        </div>
      </td>

      {/* JM */}
      <td className="border border-border-default px-1 py-1 text-[10px] text-text-muted whitespace-nowrap align-top">
        {item.unit ?? "\u2014"}
      </td>

      {/* Kol. */}
      <td className="border border-border-default px-1 py-1 text-right font-mono text-[10px] text-text-primary whitespace-nowrap align-top">
        {formatNumber(item.quantity ?? 0)}
        {qtyMul && (
          <div className={`text-[8px] ${mulColor(refQty!, item.quantity ?? 0)}`}>{qtyMul}</div>
        )}
      </td>

      {/* JC */}
      <td className="border border-border-default px-1 py-1 text-right font-mono text-[10px] text-text-primary whitespace-nowrap align-top">
        {formatNumber(item.unit_price ?? 0)}
        {priceMul && (
          <div className={`text-[8px] ${mulColor(refPrice!, item.unit_price ?? 0)}`}>{priceMul}</div>
        )}
      </td>

      {/* UC */}
      <td className="border border-border-default px-1 py-1 text-right font-mono text-[10px] text-text-primary whitespace-nowrap align-top">
        {formatNumber(item.total ?? 0)}
      </td>

      {/* Apply */}
      <td className="border border-border-default px-0.5 py-1 text-center align-top">
        <button
          onClick={(e) => {
            e.stopPropagation();
            // Find the active selection's first item and apply the match price
            const activeSelId = useSelectionStore.getState().activeSelectionId;
            const activeSel = useSelectionStore.getState().selections.find((s) => s.id === activeSelId);
            const targetItem = activeSel?.items[0];
            if (targetItem && item.unit_price != null) {
              useBoQStore.getState().updateWorkingItem(targetItem.id, {
                unit_price: item.unit_price,
              });
            }
          }}
          className="p-0.5 rounded hover:bg-accent-emerald/20 text-text-muted hover:text-accent-emerald transition-colors"
          title="Apply this price"
        >
          <Check className="w-3 h-3" />
        </button>
      </td>
    </tr>
  );
}

export default function MatchResultsTable({
  matches,
  wrapText,
  groups,
  isComposite,
  parentDescription,
  refQty,
  refPrice,
}: Props) {
  return (
    <div>
      <table className="w-full text-xs border-collapse">
        <colgroup>
          {COLUMNS.map((col) => (
            <col
              key={col.key}
              style={col.width ? { width: col.width, minWidth: col.width } : undefined}
              className={col.width ? undefined : "w-full"}
            />
          ))}
        </colgroup>

        <thead className="sticky top-0 z-10">
          <tr>
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                className={`
                  border border-border-default bg-bg-secondary px-1.5 py-1.5
                  text-[10px] font-semibold uppercase tracking-wider text-text-muted
                  ${col.align === "right" ? "text-right" : "text-left"}
                `}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {isComposite && groups ? (
            <>
              {/* Parent description header */}
              {parentDescription && (
                <tr>
                  <td
                    colSpan={COL_COUNT}
                    className="border border-accent-purple/30 bg-accent-purple/10 px-2 py-1.5 text-[11px] font-semibold text-text-primary"
                  >
                    {parentDescription}
                  </td>
                </tr>
              )}

              {/* Level 1: Unit-level matches (whole matching units from history) */}
              {matches.length > 0 && (
                <>
                  <tr>
                    <td
                      colSpan={COL_COUNT}
                      className="border border-accent-emerald/30 bg-accent-emerald/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-accent-emerald"
                    >
                      Unit Matches ({matches.length})
                    </td>
                  </tr>
                  {matches.map((match) => (
                    <MatchRow key={match.item.id} match={match} wrapText={wrapText} refQty={refQty} refPrice={refPrice} />
                  ))}
                </>
              )}

              {/* Level 2: Per-sub-item matches */}
              {groups.length > 0 && (
                <>
                  <tr>
                    <td
                      colSpan={COL_COUNT}
                      className="border border-accent-purple/30 bg-accent-purple/5 px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-accent-purple"
                    >
                      Sub-Item Matches
                    </td>
                  </tr>
                  {groups.map((group) => (
                    <GroupRows key={group.sub_item.id} group={group} wrapText={wrapText} refQty={refQty} refPrice={refPrice} />
                  ))}
                </>
              )}
            </>
          ) : (
            matches.map((match) => (
              <MatchRow key={match.item.id} match={match} wrapText={wrapText} refQty={refQty} refPrice={refPrice} />
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

function GroupRows({ group, wrapText, refQty, refPrice }: { group: MatchGroup; wrapText: boolean; refQty?: number | null; refPrice?: number | null }) {
  const sub = group.sub_item;

  return (
    <>
      {/* Sub-item header row */}
      <tr>
        <td className="border border-accent-purple/20 bg-accent-purple/5 px-1 py-1 font-mono text-[10px] font-semibold text-accent-purple whitespace-nowrap">
          {sub.item_number ?? ""}
        </td>
        <td className="border border-accent-purple/20 bg-accent-purple/5 px-1.5 py-1 text-[11px] font-medium text-text-primary">
          {sub.description}
        </td>
        <td className="border border-accent-purple/20 bg-accent-purple/5 px-1 py-1 text-[10px] text-text-muted">
          {sub.unit ?? ""}
        </td>
        <td className="border border-accent-purple/20 bg-accent-purple/5 px-1 py-1 text-right font-mono text-[10px] text-text-muted">
          {formatNumber(sub.quantity ?? 0)}
        </td>
        <td
          colSpan={2}
          className="border border-accent-purple/20 bg-accent-purple/5 px-1 py-1 text-right text-[9px] text-text-muted"
        >
          {group.matches.length} {group.matches.length === 1 ? "match" : "matches"}
        </td>
      </tr>

      {/* Match rows for this sub-item */}
      {group.matches.map((match) => (
        <MatchRow key={match.item.id} match={match} wrapText={wrapText} refQty={refQty} refPrice={refPrice} />
      ))}

      {/* Empty state for sub-item with no matches */}
      {group.matches.length === 0 && (
        <tr>
          <td
            colSpan={COL_COUNT}
            className="border border-border-default px-2 py-2 text-center text-[10px] text-text-muted italic"
          >
            No matches found
          </td>
        </tr>
      )}
    </>
  );
}
