"use client";

import { useEffect, useState } from "react";
import { Trash2, Plus, Globe, ChevronDown, ChevronRight } from "lucide-react";
import { useDomainStore } from "@/stores/domainStore";

export default function DomainsSection() {
  const { domains, isLoaded, isLoading, fetchAll, addDomain, removeDomain, toggleEnabled } =
    useDomainStore();
  const [open, setOpen] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [newDomain, setNewDomain] = useState("");
  const [newName, setNewName] = useState("");
  const [newTemplate, setNewTemplate] = useState("");
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isLoaded) fetchAll();
  }, [isLoaded, fetchAll]);

  const handleAdd = async () => {
    if (!newDomain.trim() || !newName.trim()) return;
    setAdding(true);
    setError("");
    try {
      await addDomain({
        domain: newDomain.trim(),
        display_name: newName.trim(),
        search_url_template: newTemplate.trim() || undefined,
      });
      setNewDomain("");
      setNewName("");
      setNewTemplate("");
      setShowAdd(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add domain");
    } finally {
      setAdding(false);
    }
  };

  const enabledCount = domains.filter((d) => d.enabled).length;

  return (
    <div className="border border-border-default rounded-md overflow-hidden mb-1">
      {/* Header */}
      <div className="px-2 py-1.5 bg-bg-tertiary flex items-center justify-between">
        <button
          onClick={() => setOpen(!open)}
          className="flex items-center gap-1.5 text-xs font-medium text-text-secondary"
        >
          {open ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          <Globe className="w-3 h-3" />
          Search Domains
          <span className="text-text-muted font-normal">
            ({enabledCount}/{domains.length})
          </span>
        </button>
      </div>

      {open && (
        <div className="px-2 py-2 space-y-1.5">
          {isLoading ? (
            <span className="text-[10px] text-text-muted">Loading domains...</span>
          ) : domains.length === 0 ? (
            <span className="text-[10px] text-text-muted">No search domains configured.</span>
          ) : (
            <div className="space-y-1">
              {domains.map((d) => (
                <div
                  key={d.id}
                  className="flex items-center gap-2 text-[10px] p-1 rounded bg-bg-hover"
                >
                  {/* Enabled toggle */}
                  <button
                    onClick={() => toggleEnabled(d.id, !d.enabled)}
                    className={`w-7 h-4 rounded-full relative transition-colors shrink-0 ${
                      d.enabled ? "bg-accent-cyan" : "bg-bg-tertiary border border-border-default"
                    }`}
                  >
                    <span
                      className={`absolute top-0.5 w-3 h-3 rounded-full transition-all ${
                        d.enabled ? "right-0.5 bg-white" : "left-0.5 bg-text-muted"
                      }`}
                    />
                  </button>

                  {/* Domain info */}
                  <div className="flex-1 min-w-0 truncate">
                    <span className="font-medium text-text-secondary">{d.display_name}</span>
                    <span className="text-text-muted ml-1 font-mono">{d.domain}</span>
                  </div>

                  {/* Fetch mode badge */}
                  {d.fetch_mode === "render" && (
                    <span className="px-1 py-0.5 rounded bg-accent-amber/20 text-accent-amber text-[9px] shrink-0">
                      JS
                    </span>
                  )}

                  {/* Delete button (non-default only) */}
                  {!d.is_default && (
                    <button
                      onClick={() => removeDomain(d.id)}
                      className="text-accent-amber hover:text-accent-amber/80 p-0.5 shrink-0"
                      title="Remove domain"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Add domain */}
          <div className="pt-1.5 border-t border-border-default">
            {showAdd ? (
              <div className="space-y-1.5">
                <input
                  type="text"
                  placeholder="domain.com"
                  value={newDomain}
                  onChange={(e) => setNewDomain(e.target.value)}
                  className="w-full text-[10px] bg-bg-primary border border-border-default rounded px-1.5 py-1 text-text-secondary placeholder:text-text-muted focus:outline-none focus:border-accent-cyan/50"
                />
                <input
                  type="text"
                  placeholder="Display Name"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="w-full text-[10px] bg-bg-primary border border-border-default rounded px-1.5 py-1 text-text-secondary placeholder:text-text-muted focus:outline-none focus:border-accent-cyan/50"
                />
                <input
                  type="text"
                  placeholder="https://domain.com/search?q={query}"
                  value={newTemplate}
                  onChange={(e) => setNewTemplate(e.target.value)}
                  className="w-full text-[10px] bg-bg-primary border border-border-default rounded px-1.5 py-1 text-text-secondary placeholder:text-text-muted focus:outline-none focus:border-accent-cyan/50 font-mono"
                />
                {error && <div className="text-[10px] text-accent-amber">{error}</div>}
                <div className="flex gap-1">
                  <button
                    onClick={handleAdd}
                    disabled={adding || !newDomain.trim() || !newName.trim()}
                    className="px-2 py-1 bg-accent-cyan/20 text-accent-cyan text-[10px] rounded hover:bg-accent-cyan/30 disabled:opacity-50 flex items-center gap-1"
                  >
                    <Plus className="w-3 h-3" />
                    {adding ? "Adding..." : "Add"}
                  </button>
                  <button
                    onClick={() => {
                      setShowAdd(false);
                      setError("");
                      setNewDomain("");
                      setNewName("");
                      setNewTemplate("");
                    }}
                    className="px-2 py-1 text-text-muted text-[10px] rounded hover:bg-bg-hover"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <button
                onClick={() => setShowAdd(true)}
                className="flex items-center gap-1 text-[10px] text-accent-cyan hover:text-accent-cyan/80"
              >
                <Plus className="w-3 h-3" />
                Add Domain
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
