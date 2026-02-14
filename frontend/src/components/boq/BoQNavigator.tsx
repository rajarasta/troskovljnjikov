"use client";

import { useState, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronRight } from "lucide-react";
import type { BoQItem } from "@/lib/types";

interface BoQNavigatorProps {
  items: BoQItem[];
  selectedId: string | null;
  onSelect: (item: BoQItem) => void;
}

interface TreeNode {
  item: BoQItem;
  children: TreeNode[];
}

function buildTree(items: BoQItem[]): TreeNode[] {
  const itemMap = new Map<string, BoQItem>();
  const childrenMap = new Map<string, BoQItem[]>();

  // Index all items by item_number
  for (const item of items) {
    itemMap.set(item.item_number, item);
  }

  // Group children by parent_item_number
  for (const item of items) {
    if (item.parent_item_number) {
      const siblings = childrenMap.get(item.parent_item_number) ?? [];
      siblings.push(item);
      childrenMap.set(item.parent_item_number, siblings);
    }
  }

  // Recursively build tree nodes
  function toNode(item: BoQItem): TreeNode {
    const childItems = childrenMap.get(item.item_number) ?? [];
    return {
      item,
      children: childItems.map(toNode),
    };
  }

  // Root nodes are items without a parent_item_number
  const roots = items.filter((i) => !i.parent_item_number);
  return roots.map(toNode);
}

function getChildrenTotal(node: TreeNode): number {
  if (node.children.length === 0) return node.item.total;
  return node.children.reduce((sum, child) => sum + getChildrenTotal(child), 0);
}

function formatCurrency(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toFixed(2);
}

function TreeItem({
  node,
  depth,
  selectedId,
  onSelect,
  expandedIds,
  onToggle,
}: {
  node: TreeNode;
  depth: number;
  selectedId: string | null;
  onSelect: (item: BoQItem) => void;
  expandedIds: Set<string>;
  onToggle: (id: string) => void;
}) {
  const hasChildren = node.children.length > 0;
  const isExpanded = expandedIds.has(node.item.id);
  const isSelected = node.item.id === selectedId;

  const handleClick = useCallback(() => {
    onSelect(node.item);
    if (hasChildren) {
      onToggle(node.item.id);
    }
  }, [node.item, hasChildren, onSelect, onToggle]);

  return (
    <div>
      {/* Item row */}
      <motion.button
        type="button"
        onClick={handleClick}
        whileTap={{ scale: 0.98 }}
        className={`
          w-full flex items-center gap-1.5 px-2 py-1.5 text-left rounded
          transition-colors duration-150 group cursor-pointer
          ${isSelected
            ? "bg-accent-cyan/10 border border-accent-cyan/30"
            : "border border-transparent hover:bg-bg-hover/60"
          }
        `}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {/* Expand/collapse chevron */}
        <span className="w-4 h-4 shrink-0 flex items-center justify-center">
          {hasChildren && (
            <motion.span
              animate={{ rotate: isExpanded ? 90 : 0 }}
              transition={{ duration: 0.15 }}
            >
              <ChevronRight className="w-3.5 h-3.5 text-text-muted" />
            </motion.span>
          )}
        </span>

        {/* Item number */}
        <span
          className={`shrink-0 text-[10px] font-mono font-medium ${
            isSelected ? "text-accent-cyan" : "text-text-muted"
          }`}
        >
          {node.item.item_number}
        </span>

        {/* Description */}
        <span
          className={`flex-1 text-xs whitespace-pre-wrap break-words ${
            isSelected
              ? "text-accent-cyan"
              : "text-text-primary group-hover:text-text-primary"
          }`}
        >
          {node.item.description}
        </span>

        {/* Total for parent items */}
        {hasChildren && (
          <span className="shrink-0 text-[10px] font-mono text-text-muted">
            {formatCurrency(getChildrenTotal(node))}
          </span>
        )}
      </motion.button>

      {/* Children */}
      <AnimatePresence initial={false}>
        {hasChildren && isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            {node.children.map((child) => (
              <TreeItem
                key={child.item.id}
                node={child}
                depth={depth + 1}
                selectedId={selectedId}
                onSelect={onSelect}
                expandedIds={expandedIds}
                onToggle={onToggle}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function BoQNavigator({
  items,
  selectedId,
  onSelect,
}: BoQNavigatorProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const tree = useMemo(() => buildTree(items), [items]);

  const handleToggle = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  if (items.length === 0) {
    return (
      <div className="flex items-center justify-center py-8 text-text-muted text-xs">
        No items loaded
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-0.5 py-1 overflow-y-auto">
      {tree.map((node) => (
        <TreeItem
          key={node.item.id}
          node={node}
          depth={0}
          selectedId={selectedId}
          onSelect={onSelect}
          expandedIds={expandedIds}
          onToggle={handleToggle}
        />
      ))}
    </div>
  );
}
