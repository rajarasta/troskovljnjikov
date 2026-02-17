"use client";

import { useState, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  Globe,
  FileText,
  Database,
  Calculator,
  MessageSquare,
  Search,
  ChevronRight,
  Loader2,
  ExternalLink,
  Check,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { useBoQStore } from "@/stores/boqStore";
import { useSearchStore } from "@/stores/searchStore";
import { useSelectionStore } from "@/stores/selectionStore";
import { triggerPriceSearch, triggerBatchPriceSearch } from "@/lib/api";
import type { WebQuote } from "@/lib/types";

// ── Animation variants ──────────────────────────────────────────────

const backdropVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.2 } },
  exit: { opacity: 0, transition: { duration: 0.15 } },
};

const modalVariants = {
  hidden: { opacity: 0, scale: 0.96, y: 12 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { type: "spring", damping: 28, stiffness: 320, delay: 0.05 },
  },
  exit: {
    opacity: 0,
    scale: 0.97,
    y: 8,
    transition: { duration: 0.15 },
  },
};

const staggerChildren = {
  visible: { transition: { staggerChildren: 0.06, delayChildren: 0.12 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.3, ease: "easeOut" } },
};

// ── Pipeline step config ────────────────────────────────────────────

const PIPELINE_STEPS = [
  {
    key: "describe",
    label: "Describe",
    sublabel: "BoQ item sent",
    icon: FileText,
    color: "text-accent-cyan",
    bg: "bg-accent-cyan/10",
    border: "border-accent-cyan/20",
  },
  {
    key: "search",
    label: "Search",
    sublabel: "Domains queried",
    icon: Globe,
    color: "text-accent-purple",
    bg: "bg-accent-purple/8",
    border: "border-accent-purple/15",
  },
  {
    key: "extract",
    label: "Extract",
    sublabel: "Prices parsed",
    icon: Database,
    color: "text-accent-amber",
    bg: "bg-accent-amber/10",
    border: "border-accent-amber/20",
  },
  {
    key: "normalize",
    label: "Normalize",
    sublabel: "PDV, units, €",
    icon: Calculator,
    color: "text-accent-emerald",
    bg: "bg-accent-emerald/10",
    border: "border-accent-emerald/20",
  },
  {
    key: "report",
    label: "Report",
    sublabel: "Chat + totals",
    icon: MessageSquare,
    color: "text-accent-cyan",
    bg: "bg-accent-cyan/10",
    border: "border-accent-cyan/20",
  },
] as const;

// ── Domain config ───────────────────────────────────────────────────

const DOMAINS = [
  { key: "bauhaus", label: "Bauhaus", domain: "bauhaus.hr", initial: "B" },
  { key: "gradja", label: "Gradja.hr", domain: "gradja.hr", initial: "G" },
  { key: "wuerth", label: "Würth", domain: "wuerth.com.hr", initial: "W" },
  { key: "era", label: "ERA Commerce", domain: "era-commerce.hr", initial: "E" },
] as const;

// ── Pipeline flow connector ─────────────────────────────────────────

function FlowConnector({ active }: { active: boolean }) {
  return (
    <div className="flex items-center mx-1 w-6">
      <div className="relative w-full h-[2px] bg-border-default rounded-full overflow-hidden">
        {active && (
          <motion.div
            className="absolute inset-y-0 left-0 bg-accent-purple/60 rounded-full"
            initial={{ width: 0 }}
            animate={{ width: "100%" }}
            transition={{ duration: 0.6, ease: "easeOut" }}
          />
        )}
        {/* Animated pulse traveling along the connector */}
        {active && (
          <motion.div
            className="absolute top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-accent-purple"
            animate={{ left: ["-4px", "calc(100% + 4px)"] }}
            transition={{ duration: 1.2, repeat: Infinity, ease: "linear", repeatDelay: 0.8 }}
          />
        )}
      </div>
    </div>
  );
}

// ── Pipeline step node ──────────────────────────────────────────────

function StepNode({
  step,
  index,
  isActive,
  isComplete,
}: {
  step: (typeof PIPELINE_STEPS)[number];
  index: number;
  isActive: boolean;
  isComplete: boolean;
}) {
  const Icon = step.icon;

  return (
    <motion.div
      variants={fadeUp}
      className="flex flex-col items-center gap-1.5 relative"
    >
      {/* Node circle */}
      <div
        className={`
          relative w-10 h-10 rounded-xl flex items-center justify-center
          border transition-all duration-300
          ${isComplete
            ? "bg-accent-emerald/12 border-accent-emerald/25"
            : isActive
              ? `${step.bg} ${step.border} shadow-sm`
              : "bg-bg-tertiary/50 border-border-default"
          }
        `}
      >
        {isComplete ? (
          <Check className="w-4 h-4 text-accent-emerald" strokeWidth={2.5} />
        ) : (
          <Icon
            className={`w-4 h-4 transition-colors duration-200 ${
              isActive ? step.color : "text-text-muted"
            }`}
          />
        )}

        {/* Active pulse ring */}
        {isActive && !isComplete && (
          <motion.div
            className={`absolute inset-0 rounded-xl ${step.border}`}
            style={{ borderWidth: 1 }}
            animate={{ scale: [1, 1.2, 1], opacity: [0.6, 0, 0.6] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          />
        )}

        {/* Step number */}
        <span
          className={`
            absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full text-[8px] font-bold
            flex items-center justify-center
            ${isComplete
              ? "bg-accent-emerald text-white"
              : isActive
                ? "bg-accent-purple text-white"
                : "bg-bg-tertiary text-text-muted border border-border-default"
            }
          `}
        >
          {index + 1}
        </span>
      </div>

      {/* Label */}
      <span
        className={`text-[10px] font-semibold uppercase tracking-wider transition-colors duration-200 ${
          isComplete
            ? "text-accent-emerald"
            : isActive
              ? step.color
              : "text-text-muted"
        }`}
      >
        {step.label}
      </span>
      <span className="text-[9px] text-text-muted -mt-1">{step.sublabel}</span>
    </motion.div>
  );
}

// ── Domain chip ─────────────────────────────────────────────────────

function DomainChip({
  domain,
  enabled,
  onToggle,
}: {
  domain: (typeof DOMAINS)[number];
  enabled: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      onClick={onToggle}
      className={`
        group flex items-center gap-2.5 px-3 py-2 rounded-lg border transition-all duration-200
        ${enabled
          ? "bg-white border-border-default hover:border-accent-cyan/30 shadow-sm"
          : "bg-bg-tertiary/40 border-transparent hover:border-border-default opacity-60"
        }
      `}
    >
      {/* Monogram */}
      <div
        className={`
          w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold
          transition-all duration-200
          ${enabled
            ? "bg-accent-purple/10 text-accent-purple"
            : "bg-bg-tertiary text-text-muted"
          }
        `}
      >
        {domain.initial}
      </div>

      <div className="flex flex-col items-start">
        <span
          className={`text-[11px] font-medium leading-tight transition-colors ${
            enabled ? "text-text-primary" : "text-text-muted"
          }`}
        >
          {domain.label}
        </span>
        <span className="text-[9px] text-text-muted leading-tight font-mono">
          {domain.domain}
        </span>
      </div>

      {/* Toggle indicator */}
      <div
        className={`
          ml-auto w-7 h-4 rounded-full relative transition-colors duration-200 shrink-0
          ${enabled ? "bg-accent-emerald/25" : "bg-bg-tertiary"}
        `}
      >
        <motion.div
          className={`
            absolute top-0.5 w-3 h-3 rounded-full transition-colors duration-200
            ${enabled ? "bg-accent-emerald" : "bg-text-muted/40"}
          `}
          animate={{ left: enabled ? 14 : 2 }}
          transition={{ type: "spring", stiffness: 500, damping: 30 }}
        />
      </div>
    </button>
  );
}

// ── Toggle switch ───────────────────────────────────────────────────

function OptionToggle({
  label,
  sublabel,
  checked,
  onChange,
}: {
  label: string;
  sublabel: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className="flex items-center gap-3 group"
    >
      <div
        className={`
          w-8 h-[18px] rounded-full relative transition-colors duration-200 shrink-0
          ${checked ? "bg-accent-emerald/25" : "bg-bg-tertiary"}
        `}
      >
        <motion.div
          className={`
            absolute top-[3px] w-3 h-3 rounded-full transition-colors duration-200
            ${checked ? "bg-accent-emerald" : "bg-text-muted/40"}
          `}
          animate={{ left: checked ? 14 : 3 }}
          transition={{ type: "spring", stiffness: 500, damping: 30 }}
        />
      </div>
      <div className="text-left">
        <span className="text-[11px] font-medium text-text-primary block leading-tight">
          {label}
        </span>
        <span className="text-[9px] text-text-muted block leading-tight">
          {sublabel}
        </span>
      </div>
    </button>
  );
}

// ── Live quote card (shown during/after search) ─────────────────────

function QuoteCard({ quote }: { quote: WebQuote }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-white border border-border-default"
    >
      <div className="w-6 h-6 rounded bg-accent-emerald/10 flex items-center justify-center shrink-0">
        <Check className="w-3 h-3 text-accent-emerald" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[11px] font-medium text-text-primary truncate">
          {quote.product_name || "Product"}
        </p>
        <p className="text-[9px] text-text-muted truncate">{quote.vendor}</p>
      </div>
      <div className="text-right shrink-0">
        <p className="text-[11px] font-bold text-accent-purple">
          {quote.unit_price.toFixed(2)} {quote.currency}
        </p>
        <p className="text-[9px] text-text-muted">
          {quote.vat_included ? "PDV uklj." : "bez PDV"}
        </p>
      </div>
    </motion.div>
  );
}

// ── Main modal ──────────────────────────────────────────────────────

interface PriceSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function PriceSearchModal({ isOpen, onClose }: PriceSearchModalProps) {
  // Domain toggles
  const [enabledDomains, setEnabledDomains] = useState<Record<string, boolean>>({
    bauhaus: true,
    gradja: true,
    wuerth: true,
    era: true,
  });

  // Options
  const [includeVat, setIncludeVat] = useState(true);
  const [includeShipping, setIncludeShipping] = useState(true);

  // Get selection context
  const selectedRow = useBoQStore((s) => s.selectedRow);
  const items = useBoQStore((s) => s.items);
  const selections = useSelectionStore((s) => s.selections);

  // Search state
  const searchStatuses = useSearchStore((s) => s.status);
  const searchQuotes = useSearchStore((s) => s.quotes);

  // Determine what we're searching
  const selectedItems = useMemo(() => {
    if (selections.length > 0) {
      // Multi-selection from spreadsheet - use items directly from selections
      // This preserves synthetic item data (like descriptions for Excel cells)
      return selections.flatMap((s) => s.items);
    }
    if (selectedRow) return [selectedRow];
    return [];
  }, [selections, selectedRow]);

  const isSingleItem = selectedItems.length === 1;
  const isMultiItem = selectedItems.length > 1;
  const hasSelection = selectedItems.length > 0;

  // Check if any search is running
  const isSearching = selectedItems.some(
    (item) => searchStatuses[item.id] === "searching"
  );
  const isDone = hasSelection && selectedItems.every(
    (item) => searchStatuses[item.id] === "done"
  );

  // Get active search step for pipeline visualization
  const activeStep = isSearching ? 1 : isDone ? 5 : 0;

  // Collect all quotes for display
  const allQuotes = useMemo(() => {
    const quotes: WebQuote[] = [];
    for (const item of selectedItems) {
      const itemQuotes = searchQuotes[item.id];
      if (itemQuotes) quotes.push(...itemQuotes);
    }
    return quotes;
  }, [selectedItems, searchQuotes]);

  const handleToggleDomain = useCallback((key: string) => {
    setEnabledDomains((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const handleLaunch = useCallback(async () => {
    if (!hasSelection) return;

    if (isSingleItem) {
      const item = selectedItems[0];
      console.log("🔍 Single item search:", { id: item.id, description: item.description, full_description: item.full_description });
      await triggerPriceSearch(item.id, {
        description: item.full_description || item.description || undefined,
        include_vat: includeVat,
        include_shipping: includeShipping,
      });
    } else {
      // For batch: build descriptions map for synthetic items
      const descriptions: Record<string, string> = {};
      selectedItems.forEach((item) => {
        if (item.id.startsWith("excel-cell-")) {
          descriptions[item.id] = item.full_description || item.description || "";
        }
      });

      console.log("🔍 Batch search:", { items: selectedItems.length, descriptions, selectedItems });

      await triggerBatchPriceSearch(
        selectedItems.map((i) => i.id),
        {
          descriptions: Object.keys(descriptions).length > 0 ? descriptions : undefined,
          include_vat: includeVat,
          include_shipping: includeShipping,
        }
      );
    }
  }, [hasSelection, isSingleItem, selectedItems, includeVat, includeShipping]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            key="search-modal-backdrop"
            variants={backdropVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            onClick={onClose}
            className="fixed inset-0 z-50 bg-black/30 backdrop-blur-[3px]"
          />

          {/* Modal card */}
          <motion.div
            key="search-modal"
            variants={modalVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="fixed inset-0 z-50 flex items-center justify-center pointer-events-none p-6"
          >
            <motion.div
              variants={staggerChildren}
              initial="hidden"
              animate="visible"
              className="
                pointer-events-auto w-full max-w-[560px]
                glass-panel rounded-2xl shadow-xl
                border border-border-default overflow-hidden
              "
            >
              {/* ── Header ─────────────────────────────────────────── */}
              <motion.div
                variants={fadeUp}
                className="relative px-6 pt-5 pb-4 border-b border-border-default"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-accent-purple/10 border border-accent-purple/15 flex items-center justify-center">
                      <Globe className="w-4.5 h-4.5 text-accent-purple" />
                    </div>
                    <div>
                      <h2 className="text-sm font-bold text-text-primary tracking-tight">
                        Web Price Search
                      </h2>
                      <p className="text-[10px] text-text-muted mt-0.5">
                        Agent searches approved supplier sites for current prices
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={onClose}
                    className="p-1.5 rounded-lg hover:bg-bg-hover text-text-muted hover:text-text-primary transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </motion.div>

              {/* ── Pipeline flow ───────────────────────────────────── */}
              <motion.div
                variants={fadeUp}
                className="px-6 py-4 border-b border-border-default bg-bg-secondary/30"
              >
                <div className="flex items-center justify-between text-[9px] text-text-muted uppercase tracking-widest mb-3 px-1">
                  <span>Agent Pipeline</span>
                  {isSearching && (
                    <motion.span
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex items-center gap-1 text-accent-purple normal-case tracking-normal"
                    >
                      <Loader2 className="w-2.5 h-2.5 animate-spin" />
                      Running
                    </motion.span>
                  )}
                  {isDone && (
                    <motion.span
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex items-center gap-1 text-accent-emerald normal-case tracking-normal"
                    >
                      <Check className="w-2.5 h-2.5" />
                      Complete
                    </motion.span>
                  )}
                </div>

                <div className="flex items-start justify-center">
                  {PIPELINE_STEPS.map((step, i) => (
                    <div key={step.key} className="flex items-center">
                      <StepNode
                        step={step}
                        index={i}
                        isActive={isSearching && i <= activeStep}
                        isComplete={isDone || (isSearching && i < activeStep)}
                      />
                      {i < PIPELINE_STEPS.length - 1 && (
                        <FlowConnector active={isSearching && i < activeStep || isDone} />
                      )}
                    </div>
                  ))}
                </div>
              </motion.div>

              {/* ── Domains ─────────────────────────────────────────── */}
              <motion.div variants={fadeUp} className="px-6 py-4 border-b border-border-default">
                <div className="flex items-center gap-2 mb-3">
                  <ShieldCheck className="w-3.5 h-3.5 text-accent-emerald" />
                  <span className="text-[10px] text-text-muted uppercase tracking-widest">
                    Approved Sources
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  {DOMAINS.map((d) => (
                    <DomainChip
                      key={d.key}
                      domain={d}
                      enabled={enabledDomains[d.key]}
                      onToggle={() => handleToggleDomain(d.key)}
                    />
                  ))}
                </div>
              </motion.div>

              {/* ── Options + Launch ────────────────────────────────── */}
              <motion.div variants={fadeUp} className="px-6 py-4">
                {/* Options row */}
                <div className="flex items-center gap-6 mb-4">
                  <OptionToggle
                    label="Include PDV"
                    sublabel="25% Croatian VAT"
                    checked={includeVat}
                    onChange={setIncludeVat}
                  />
                  <OptionToggle
                    label="Include Shipping"
                    sublabel="Delivery estimate"
                    checked={includeShipping}
                    onChange={setIncludeShipping}
                  />
                </div>

                {/* Live quotes (shown when searching or done) */}
                {allQuotes.length > 0 && (
                  <div className="mb-4 space-y-1.5 max-h-32 overflow-y-auto">
                    <span className="text-[9px] text-text-muted uppercase tracking-widest block mb-2">
                      Quotes Found ({allQuotes.length})
                    </span>
                    {allQuotes.slice(0, 4).map((q, i) => (
                      <QuoteCard key={`${q.url}-${i}`} quote={q} />
                    ))}
                    {allQuotes.length > 4 && (
                      <p className="text-[9px] text-text-muted text-center pt-1">
                        +{allQuotes.length - 4} more
                      </p>
                    )}
                  </div>
                )}

                {/* Launch button */}
                <button
                  onClick={handleLaunch}
                  disabled={!hasSelection || isSearching}
                  className={`
                    w-full flex items-center justify-center gap-2.5 px-4 py-3 rounded-xl
                    text-[12px] font-semibold tracking-wide transition-all duration-200
                    disabled:opacity-40 disabled:cursor-not-allowed
                    ${isSearching
                      ? "bg-accent-purple/10 text-accent-purple border border-accent-purple/20"
                      : isDone
                        ? "bg-accent-emerald/10 text-accent-emerald border border-accent-emerald/20 hover:bg-accent-emerald/15"
                        : hasSelection
                          ? "bg-accent-purple/10 text-accent-purple border border-accent-purple/20 hover:bg-accent-purple/15 hover:border-accent-purple/30 active:scale-[0.99]"
                          : "bg-bg-tertiary text-text-muted border border-transparent"
                    }
                  `}
                >
                  {isSearching ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Searching...
                    </>
                  ) : isDone ? (
                    <>
                      <Check className="w-4 h-4" />
                      Search Complete — {allQuotes.length} quote{allQuotes.length !== 1 ? "s" : ""} found
                    </>
                  ) : !hasSelection ? (
                    <>
                      <Search className="w-4 h-4" />
                      Select items in spreadsheet first
                    </>
                  ) : isSingleItem ? (
                    <>
                      <Zap className="w-4 h-4" />
                      Search Price
                      <span className="max-w-[200px] truncate text-[11px] font-normal opacity-70">
                        — {selectedItems[0].description?.slice(0, 40)}
                      </span>
                    </>
                  ) : (
                    <>
                      <Zap className="w-4 h-4" />
                      Batch Search {selectedItems.length} Items
                    </>
                  )}
                </button>

                {/* Subtle footer */}
                <p className="text-[9px] text-text-muted text-center mt-3 leading-relaxed">
                  Results stream into the Chat panel. Prices are extracted deterministically —
                  <br />
                  the agent navigates, your code computes.
                </p>
              </motion.div>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
