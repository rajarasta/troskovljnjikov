"use client";

import { motion } from "framer-motion";
import { Loader2, Eye, Tags, TrendingUp, ShieldCheck } from "lucide-react";

interface PhotoAnalysisData {
  description: string;
  matchedItems: string[];
  progress: number;
  confidence: number;
}

interface PhotoAnalysisProps {
  imageUrl: string;
  analysis: PhotoAnalysisData | null;
  isLoading?: boolean;
}

function ProgressGauge({ value, label }: { value: number; label: string }) {
  const clampedValue = Math.max(0, Math.min(100, value));
  const circumference = 2 * Math.PI * 36;
  const strokeDashoffset = circumference * (1 - clampedValue / 100);

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="relative w-20 h-20">
        {/* Background circle */}
        <svg className="w-full h-full -rotate-90" viewBox="0 0 80 80">
          <circle
            cx="40"
            cy="40"
            r="36"
            fill="none"
            stroke="currentColor"
            strokeWidth="4"
            className="text-border-default"
          />
          <motion.circle
            cx="40"
            cy="40"
            r="36"
            fill="none"
            stroke="currentColor"
            strokeWidth="4"
            strokeLinecap="round"
            className="text-accent-purple"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset }}
            transition={{ duration: 0.8, ease: "easeOut" }}
          />
        </svg>
        {/* Center value */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-sm font-mono font-semibold text-text-primary">
            {clampedValue}%
          </span>
        </div>
      </div>
      <span className="text-[10px] uppercase tracking-wider text-text-muted">
        {label}
      </span>
    </div>
  );
}

function SectionCard({
  icon,
  title,
  children,
  delay = 0,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay }}
      className="glass-panel rounded-lg p-3"
    >
      <div className="flex items-center gap-1.5 mb-2">
        <span className="text-accent-purple">{icon}</span>
        <span className="text-[10px] uppercase tracking-wider font-semibold text-accent-purple">
          {title}
        </span>
      </div>
      {children}
    </motion.div>
  );
}

export default function PhotoAnalysis({
  imageUrl,
  analysis,
  isLoading = false,
}: PhotoAnalysisProps) {
  return (
    <div className="flex flex-col gap-3">
      {/* ── Image Thumbnail ───────────────────────────────── */}
      <div className="glass-panel glow-purple rounded-lg overflow-hidden">
        <div className="relative aspect-video bg-bg-tertiary">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={imageUrl}
            alt="Analyzed photo"
            className="w-full h-full object-cover"
          />

          {/* Loading overlay */}
          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="absolute inset-0 bg-bg-primary/70 backdrop-blur-sm
                         flex flex-col items-center justify-center gap-2"
            >
              <Loader2 className="w-8 h-8 text-accent-purple animate-spin" />
              <span className="text-xs font-medium text-accent-purple tracking-wider uppercase">
                Analyzing...
              </span>
            </motion.div>
          )}
        </div>
      </div>

      {/* ── Analysis Results ──────────────────────────────── */}
      {analysis && !isLoading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
          className="flex flex-col gap-2.5"
        >
          {/* Description */}
          <SectionCard
            icon={<Eye className="w-3.5 h-3.5" />}
            title="Description"
            delay={0}
          >
            <p className="text-xs text-text-secondary leading-relaxed">
              {analysis.description}
            </p>
          </SectionCard>

          {/* Matched BOQ Items */}
          <SectionCard
            icon={<Tags className="w-3.5 h-3.5" />}
            title="Matched Items"
            delay={0.05}
          >
            {analysis.matchedItems.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {analysis.matchedItems.map((itemId) => (
                  <span
                    key={itemId}
                    className="inline-flex items-center px-2 py-0.5 rounded
                               text-[10px] font-mono font-medium
                               bg-accent-purple/10 text-accent-purple
                               border border-accent-purple/20"
                  >
                    {itemId}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-text-muted italic">
                No matching items found
              </p>
            )}
          </SectionCard>

          {/* Gauges: Progress & Confidence */}
          <SectionCard
            icon={<TrendingUp className="w-3.5 h-3.5" />}
            title="Metrics"
            delay={0.1}
          >
            <div className="flex items-center justify-around py-2">
              <ProgressGauge
                value={analysis.progress}
                label="Progress"
              />
              <ProgressGauge
                value={Math.round(analysis.confidence * 100)}
                label="Confidence"
              />
            </div>
          </SectionCard>

          {/* Confidence indicator bar */}
          <SectionCard
            icon={<ShieldCheck className="w-3.5 h-3.5" />}
            title="Confidence Score"
            delay={0.15}
          >
            <div className="flex items-center gap-3">
              <div className="flex-1 h-1.5 bg-border-default rounded-full overflow-hidden">
                <motion.div
                  className={`h-full rounded-full ${
                    analysis.confidence >= 0.8
                      ? "bg-status-success"
                      : analysis.confidence >= 0.5
                        ? "bg-status-warning"
                        : "bg-status-danger"
                  }`}
                  initial={{ width: 0 }}
                  animate={{ width: `${analysis.confidence * 100}%` }}
                  transition={{ duration: 0.6, ease: "easeOut", delay: 0.2 }}
                />
              </div>
              <span className="text-xs font-mono text-text-primary shrink-0">
                {(analysis.confidence * 100).toFixed(0)}%
              </span>
            </div>
          </SectionCard>
        </motion.div>
      )}

      {/* ── Empty state when no analysis and not loading ── */}
      {!analysis && !isLoading && (
        <div className="glass-panel rounded-lg p-6 flex items-center justify-center">
          <p className="text-xs text-text-muted italic">
            Upload a photo and run analysis to see results
          </p>
        </div>
      )}
    </div>
  );
}
