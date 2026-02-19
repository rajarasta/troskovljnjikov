"use client";

import type { ReactNode } from "react";

interface ColumnHeaderProps {
  title: string;
  accent?: "cyan" | "purple" | "amber";
  badge?: string;
  icon?: ReactNode;
  actions?: ReactNode;
}

const accentStyles = {
  cyan: {
    text: "text-accent-cyan",
    border: "border-accent-cyan/30",
    badgeBg: "bg-accent-cyan/10",
    badgeText: "text-accent-cyan",
    badgeBorder: "border-accent-cyan/20",
  },
  purple: {
    text: "text-accent-purple",
    border: "border-accent-purple/30",
    badgeBg: "bg-accent-purple/10",
    badgeText: "text-accent-purple",
    badgeBorder: "border-accent-purple/20",
  },
  amber: {
    text: "text-accent-amber",
    border: "border-accent-amber/30",
    badgeBg: "bg-accent-amber/10",
    badgeText: "text-accent-amber",
    badgeBorder: "border-accent-amber/20",
  },
} as const;

export default function ColumnHeader({
  title,
  accent = "cyan",
  badge,
  icon,
  actions,
}: ColumnHeaderProps) {
  const styles = accentStyles[accent];

  return (
    <div
      className={`flex items-center justify-between px-3 py-2 border-b border-border-default`}
    >
      {/* Left: icon + title */}
      <div className="flex items-center gap-2 min-w-0">
        {icon && (
          <span className={`shrink-0 ${styles.text}`}>{icon}</span>
        )}
        <h2
          className={`text-xs font-semibold uppercase tracking-wider ${styles.text} truncate`}
        >
          {title}
        </h2>
      </div>

      {/* Right: badge + actions */}
      <div className="flex items-center gap-2 shrink-0">
        {badge != null && (
          <span
            className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px]
                         font-mono font-medium border
                         ${styles.badgeBg} ${styles.badgeText} ${styles.badgeBorder}`}
          >
            {badge}
          </span>
        )}
        {actions && (
          <div className="flex items-center gap-1">{actions}</div>
        )}
      </div>
    </div>
  );
}
