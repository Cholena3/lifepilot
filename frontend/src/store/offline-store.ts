import { create } from "zustand";
import { persist } from "zustand/middleware";
import {
  QueuedOperation,
  getPendingCount,
  getAllOperations,
  clearCompletedOperations,
} from "@/lib/offline";

export interface OfflineState {
  // State
  pendingCount: number;
  operations: QueuedOperation[];
  lastSyncAt: number | null;
  isSyncing: boolean;
  syncError: string | null;
}

export interface OfflineActions {
  // Actions
  setPendingCount: (count: number) => void;
  setOperations: (operations: QueuedOperation[]) => void;
  setLastSyncAt: (timestamp: number | null) => void;
  setSyncing: (isSyncing: boolean) => void;
  setSyncError: (error: string | null) => void;
  refreshFromDB: () => Promise<void>;
  clearCompleted: () => Promise<number>;
}

export type OfflineStore = OfflineState & OfflineActions;

export const useOfflineStore = create<OfflineStore>()(
  persist(
    (set) => ({
      // Initial state
      pendingCount: 0,
      operations: [],
      lastSyncAt: null,
      isSyncing: false,
      syncError: null,

      // Actions
      setPendingCount: (count) => set({ pendingCount: count }),
      setOperations: (operations) => set({ operations }),
      setLastSyncAt: (timestamp) => set({ lastSyncAt: timestamp }),
      setSyncing: (isSyncing) => set({ isSyncing }),
      setSyncError: (error) => set({ syncError: error }),

      refreshFromDB: async () => {
        try {
          const [count, ops] = await Promise.all([
            getPendingCount(),
            getAllOperations(),
          ]);
          set({ pendingCount: count, operations: ops });
        } catch (error) {
          console.error("Failed to refresh offline store from DB:", error);
        }
      },

      clearCompleted: async () => {
        const cleared = await clearCompletedOperations();
        const [count, ops] = await Promise.all([
          getPendingCount(),
          getAllOperations(),
        ]);
        set({ pendingCount: count, operations: ops });
        return cleared;
      },
    }),
    {
      name: "lifepilot-offline",
      partialize: (state) => ({
        lastSyncAt: state.lastSyncAt,
      }),
    }
  )
);
