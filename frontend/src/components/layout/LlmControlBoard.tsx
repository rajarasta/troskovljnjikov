"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { RotateCcw, ChevronDown, ChevronRight } from "lucide-react";
import { useLlmSettingsStore } from "@/stores/llmSettingsStore";

const CATEGORIES = [
  { key: "chat", label: "Chat" },
  { key: "completion", label: "Completion" },
  { key: "autopilot", label: "Autopilot" },
  { key: "agents", label: "Agents" },
] as const;

export default function LlmControlBoard() {
  const { agents, isLoaded, fetchAll, updateAgent, resetAgent } = useLlmSettingsStore();
  const activeAgentIds = useLlmSettingsStore((s) => s.activeAgentIds);
  const { availableModels, currentModel, modelsLoading, modelsError, fetchModels, setModel } =
    useLlmSettingsStore();

  useEffect(() => {
    if (!isLoaded) fetchAll();
    fetchModels();
  }, [isLoaded, fetchAll, fetchModels]);

  if (!isLoaded) {
    return <div className="text-xs text-text-muted p-2">Loading LLM settings...</div>;
  }

  const agentEntries = Object.entries(agents);

  return (
    <div className="space-y-1 max-h-[70vh] overflow-y-auto">
      {/* Global model selector */}
      <div className="border border-border-default rounded-md overflow-hidden mb-1">
        <div className="px-2 py-1.5 bg-bg-tertiary">
          <span className="text-xs font-medium text-text-secondary">Global Model</span>
        </div>
        <div className="px-2 py-2">
          {modelsLoading ? (
            <span className="text-[10px] text-text-muted">Loading models...</span>
          ) : modelsError ? (
            <div className="text-[10px] text-text-muted">
              <span className="text-accent-amber">Cannot reach model server</span>
              {currentModel && <span className="ml-1">({currentModel})</span>}
            </div>
          ) : (
            <select
              value={currentModel}
              onChange={(e) => setModel(e.target.value)}
              className="w-full text-xs bg-bg-primary border border-border-default rounded px-2 py-1 text-text-secondary focus:outline-none focus:border-accent-cyan/50"
            >
              {availableModels.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          )}
        </div>
      </div>

      <div className="text-xs text-text-muted mb-2">Per-agent temperature, prompts & enabled toggle</div>
      {CATEGORIES.map(({ key, label }) => {
        const categoryAgents = agentEntries.filter(([, s]) => s.category === key);
        if (categoryAgents.length === 0) return null;
        return (
          <CategorySection
            key={key}
            label={label}
            agents={categoryAgents}
            activeAgentIds={activeAgentIds}
            onUpdate={updateAgent}
            onReset={resetAgent}
          />
        );
      })}
    </div>
  );
}

function CategorySection({
  label,
  agents,
  activeAgentIds,
  onUpdate,
  onReset,
}: {
  label: string;
  agents: [string, {
    label: string; enabled: boolean; temperature: number;
    knowledge_prompt: string; instruction_prompt: string; is_default: boolean;
  }][];
  activeAgentIds: Set<string>;
  onUpdate: (id: string, u: {
    temperature?: number; knowledge_prompt?: string;
    instruction_prompt?: string; enabled?: boolean;
  }) => Promise<void>;
  onReset: (id: string) => Promise<void>;
}) {
  const [open, setOpen] = useState(true);

  return (
    <div className="border border-border-default rounded-md overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-1.5 px-2 py-1.5 text-xs font-medium text-text-secondary bg-bg-tertiary hover:bg-bg-hover transition-colors"
      >
        {open ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        {label}
        <span className="text-text-muted font-normal">({agents.length})</span>
      </button>
      {open && (
        <div className="divide-y divide-border-default">
          {agents.map(([id, settings]) => (
            <AgentRow
              key={id}
              agentId={id}
              settings={settings}
              isActive={activeAgentIds.has(id)}
              onUpdate={onUpdate}
              onReset={onReset}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function AgentRow({
  agentId,
  settings,
  isActive,
  onUpdate,
  onReset,
}: {
  agentId: string;
  settings: {
    label: string; enabled: boolean; temperature: number;
    knowledge_prompt: string; instruction_prompt: string; is_default: boolean;
  };
  isActive: boolean;
  onUpdate: (id: string, u: {
    temperature?: number; knowledge_prompt?: string;
    instruction_prompt?: string; enabled?: boolean;
  }) => Promise<void>;
  onReset: (id: string) => Promise<void>;
}) {
  const [knowledgeOpen, setKnowledgeOpen] = useState(false);
  const [instructionOpen, setInstructionOpen] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const debouncedUpdate = useCallback(
    (updates: {
      temperature?: number; knowledge_prompt?: string;
      instruction_prompt?: string; enabled?: boolean;
    }) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => onUpdate(agentId, updates), 500);
    },
    [agentId, onUpdate],
  );

  const handleTempChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    debouncedUpdate({ temperature: parseFloat(e.target.value) });
  };

  const handleToggle = () => {
    onUpdate(agentId, { enabled: !settings.enabled });
  };

  const knowledgePreview = settings.knowledge_prompt.split("\n")[0].slice(0, 50);
  const instructionPreview = settings.instruction_prompt.split("\n")[0].slice(0, 50);

  return (
    <div className={`px-2 py-2 space-y-1.5 transition-opacity ${settings.enabled ? "" : "opacity-50"}`}>
      {/* Header row: toggle + label + activity dot + reset */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {/* Enabled toggle */}
          <button
            onClick={handleToggle}
            className={`w-7 h-4 rounded-full relative transition-colors ${
              settings.enabled ? "bg-accent-cyan" : "bg-bg-tertiary border border-border-default"
            }`}
          >
            <span
              className={`absolute top-0.5 w-3 h-3 rounded-full transition-all ${
                settings.enabled
                  ? "right-0.5 bg-white"
                  : "left-0.5 bg-text-muted"
              }`}
            />
          </button>
          <span className="text-xs font-medium text-text-secondary">{settings.label}</span>
          {/* Activity indicator */}
          {isActive && (
            <span className="w-2 h-2 rounded-full bg-accent-cyan animate-pulse" title="Running" />
          )}
        </div>
        <div className="flex items-center gap-1.5">
          {!settings.is_default && (
            <button
              onClick={() => onReset(agentId)}
              className="text-[10px] text-accent-amber hover:text-accent-amber/80 flex items-center gap-0.5"
              title="Reset to defaults"
            >
              <RotateCcw className="w-2.5 h-2.5" />
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Temperature slider */}
      {settings.enabled && (
        <>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-text-muted w-8 shrink-0">Temp</span>
            <input
              type="range"
              min={0}
              max={2}
              step={0.05}
              defaultValue={settings.temperature}
              onChange={handleTempChange}
              className="flex-1 h-1 accent-accent-cyan"
            />
            <span className="text-[10px] font-mono text-text-secondary w-7 text-right">
              {settings.temperature.toFixed(2)}
            </span>
          </div>

          {/* Knowledge prompt (collapsible) */}
          <PromptSection
            label="Knowledge"
            preview={knowledgePreview}
            value={settings.knowledge_prompt}
            isOpen={knowledgeOpen}
            onToggle={() => setKnowledgeOpen(!knowledgeOpen)}
            onChange={(val) => debouncedUpdate({ knowledge_prompt: val })}
          />

          {/* Instruction prompt (collapsible) */}
          <PromptSection
            label="Instructions"
            preview={instructionPreview}
            value={settings.instruction_prompt}
            isOpen={instructionOpen}
            onToggle={() => setInstructionOpen(!instructionOpen)}
            onChange={(val) => debouncedUpdate({ instruction_prompt: val })}
          />
        </>
      )}
    </div>
  );
}

function PromptSection({
  label,
  preview,
  value,
  isOpen,
  onToggle,
  onChange,
}: {
  label: string;
  preview: string;
  value: string;
  isOpen: boolean;
  onToggle: () => void;
  onChange: (val: string) => void;
}) {
  return (
    <div>
      <button
        onClick={onToggle}
        className="text-[10px] text-text-muted hover:text-text-secondary flex items-center gap-1 w-full"
      >
        {isOpen ? <ChevronDown className="w-2.5 h-2.5" /> : <ChevronRight className="w-2.5 h-2.5" />}
        <span className="font-medium">{label}:</span>
        {!isOpen && <span className="truncate opacity-70">{preview}...</span>}
      </button>
      {isOpen && (
        <textarea
          defaultValue={value}
          onChange={(e) => onChange(e.target.value)}
          rows={5}
          className="mt-1 w-full text-[11px] bg-bg-primary border border-border-default rounded px-2 py-1.5 text-text-secondary resize-y font-mono leading-relaxed focus:outline-none focus:border-accent-cyan/50"
        />
      )}
    </div>
  );
}
