"use client";

import type { QuantityComparison } from "@/lib/types";

interface QuantityGaugeProps {
  comparison: QuantityComparison;
}

/**
 * Maps a QuantityComparison color string to the appropriate CSS variable.
 * The backend may send raw color names ("green", "amber", "red") or
 * hex values -- we normalise both to the theme's status palette.
 */
function resolveBarColor(color: string | undefined): string {
  const lower = (color ?? "").toLowerCase();
  if (lower === "green" || lower.includes("success")) {
    return "var(--color-status-success)";
  }
  if (lower === "amber" || lower === "yellow" || lower.includes("warning")) {
    return "var(--color-status-warning)";
  }
  if (lower === "red" || lower.includes("danger")) {
    return "var(--color-status-danger)";
  }
  // If the color is already a hex/rgb value, use it directly
  if (lower.startsWith("#") || lower.startsWith("rgb")) {
    return color ?? "var(--color-accent-cyan)";
  }
  // Fallback to accent cyan
  return "var(--color-accent-cyan)";
}

function resolveTextClass(color: string | undefined): string {
  const lower = (color ?? "").toLowerCase();
  if (lower === "green" || lower.includes("success")) return "text-status-success";
  if (lower === "amber" || lower === "yellow" || lower.includes("warning")) return "text-status-warning";
  if (lower === "red" || lower.includes("danger")) return "text-status-danger";
  return "text-accent-cyan";
}

export function QuantityGauge({ comparison }: QuantityGaugeProps) {
  if (!comparison.hasData) {
    return (
      <span className="text-[10px] text-text-muted font-mono">N/A</span>
    );
  }

  // Clamp the fill percentage between 0 and 100
  const fillPct = Math.min(100, Math.max(0, comparison.ratio != null ? comparison.ratio * 100 : 0));
  const barColor = resolveBarColor(comparison.color);
  const textClass = resolveTextClass(comparison.color);

  return (
    <div className="flex flex-col gap-0.5 min-w-[80px]">
      {/* Gauge bar + percentage */}
      <div className="flex items-center gap-1.5">
        <div className="flex-1 h-1.5 rounded-full bg-bg-tertiary overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-300 ease-out"
            style={{
              width: `${fillPct}%`,
              backgroundColor: barColor,
            }}
          />
        </div>
        <span className={`text-[10px] font-mono font-semibold shrink-0 ${textClass}`}>
          {comparison.percentDiff != null
            ? `${comparison.percentDiff > 0 ? "+" : ""}${comparison.percentDiff.toFixed(0)}%`
            : `${fillPct.toFixed(0)}%`}
        </span>
      </div>

      {/* Label */}
      <span className="text-[9px] text-text-muted leading-tight truncate">
        {comparison.label}
      </span>
    </div>
  );
}
