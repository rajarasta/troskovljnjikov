"use client";

type Status = "pending" | "accepted" | "refused" | "negotiated" | "expired";
type BadgeSize = "sm" | "md";

interface StatusBadgeProps {
  status: Status;
  size?: BadgeSize;
}

const STATUS_STYLES: Record<Status, { dot: string; text: string; bg: string }> = {
  pending: {
    dot: "bg-text-muted",
    text: "text-text-muted",
    bg: "bg-text-muted/10",
  },
  accepted: {
    dot: "bg-status-success",
    text: "text-status-success",
    bg: "bg-status-success/10",
  },
  refused: {
    dot: "bg-status-danger",
    text: "text-status-danger",
    bg: "bg-status-danger/10",
  },
  negotiated: {
    dot: "bg-status-warning",
    text: "text-status-warning",
    bg: "bg-status-warning/10",
  },
  expired: {
    dot: "bg-text-muted/60",
    text: "text-text-muted/60",
    bg: "bg-text-muted/5",
  },
};

const SIZE_STYLES: Record<BadgeSize, { pill: string; dot: string; font: string }> = {
  sm: {
    pill: "px-1.5 py-0.5",
    dot: "w-1 h-1",
    font: "text-[9px]",
  },
  md: {
    pill: "px-2 py-0.5",
    dot: "w-1.5 h-1.5",
    font: "text-[10px]",
  },
};

export function StatusBadge({ status, size = "md" }: StatusBadgeProps) {
  const style = STATUS_STYLES[status];
  const sizeStyle = SIZE_STYLES[size];

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-semibold
                   uppercase tracking-wider leading-none
                   ${style.bg} ${style.text} ${sizeStyle.pill} ${sizeStyle.font}`}
    >
      <span className={`rounded-full shrink-0 ${style.dot} ${sizeStyle.dot}`} />
      {status}
    </span>
  );
}
