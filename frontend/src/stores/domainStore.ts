import { create } from "zustand";
import type { DomainInfo, DomainCreatePayload } from "@/lib/api/domains";
import {
  fetchDomains,
  createDomain as apiCreate,
  updateDomain as apiUpdate,
  deleteDomain as apiDelete,
} from "@/lib/api/domains";

interface DomainState {
  domains: DomainInfo[];
  isLoaded: boolean;
  isLoading: boolean;

  fetchAll: () => Promise<void>;
  addDomain: (data: DomainCreatePayload) => Promise<void>;
  updateDomain: (id: string, data: Partial<DomainCreatePayload>) => Promise<void>;
  removeDomain: (id: string) => Promise<void>;
  toggleEnabled: (id: string, enabled: boolean) => Promise<void>;
}

export const useDomainStore = create<DomainState>((set, get) => ({
  domains: [],
  isLoaded: false,
  isLoading: false,

  fetchAll: async () => {
    if (get().isLoading) return;
    set({ isLoading: true });
    try {
      const domains = await fetchDomains();
      set({ domains, isLoaded: true, isLoading: false });
    } catch (err) {
      console.error("[domainStore] Failed to fetch domains:", err);
      set({ isLoading: false });
    }
  },

  addDomain: async (data) => {
    try {
      const created = await apiCreate(data);
      set((s) => ({ domains: [...s.domains, created] }));
    } catch (err) {
      console.error("[domainStore] Failed to add domain:", err);
      throw err;
    }
  },

  updateDomain: async (id, data) => {
    try {
      const updated = await apiUpdate(id, data);
      set((s) => ({
        domains: s.domains.map((d) => (d.id === id ? updated : d)),
      }));
    } catch (err) {
      console.error("[domainStore] Failed to update domain:", err);
    }
  },

  removeDomain: async (id) => {
    try {
      await apiDelete(id);
      set((s) => ({ domains: s.domains.filter((d) => d.id !== id) }));
    } catch (err) {
      console.error("[domainStore] Failed to delete domain:", err);
    }
  },

  toggleEnabled: async (id, enabled) => {
    // Optimistic update
    set((s) => ({
      domains: s.domains.map((d) => (d.id === id ? { ...d, enabled } : d)),
    }));
    try {
      await apiUpdate(id, { enabled });
    } catch (err) {
      console.error("[domainStore] Failed to toggle domain:", err);
      // Rollback
      set((s) => ({
        domains: s.domains.map((d) => (d.id === id ? { ...d, enabled: !enabled } : d)),
      }));
    }
  },
}));
