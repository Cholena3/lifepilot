"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import {
  syncPendingChanges,
  retryFailedOperations,
  getSyncStatus,
  setupAutoSync,
  addSyncListener,
  updateLastSyncTime,
  type SyncResult,
  type SyncEvent,
  type SyncConflict,
  type ConflictResolutionStrategy,
} from "@/lib/offline";

/**
 * Sync status state
 */
export interface SyncStatus {
  pendingCount: number;
  failedCount: number;
  isOnline: boolean;
  lastSyncTime?: Date;
  isSyncing: boolean;
  lastSyncResult?: SyncResult;
  conflicts: SyncConflict[];
}

/**
 * Hook for managing offline sync operations
 *
 * Validates: Requirements 35.4
 *
 * Features:
 * - Track sync status (pending, failed, syncing)
 * - Trigger manual sync
 * - Auto-sync when coming online
 * - Track and display conflicts
 * - Retry failed operations
 */
export function useSync() {
  const [status, setStatus] = useState<SyncStatus>({
    pendingCount: 0,
    failedCount: 0,
    isOnline: true,
    isSyncing: false,
    conflicts: [],
  });

  const cleanupRef = useRef<(() => void) | null>(null);

  // Load initial status
  useEffect(() => {
    const loadStatus = async () => {
      const syncStatus = await getSyncStatus();
      setStatus((prev) => ({
        ...prev,
        pendingCount: syncStatus.pendingCount,
        failedCount: syncStatus.failedCount,
        isOnline: syncStatus.isOnline,
        lastSyncTime: syncStatus.lastSyncTime
          ? new Date(syncStatus.lastSyncTime)
          : undefined,
      }));
    };

    loadStatus();
  }, []);

  // Setup auto-sync and event listeners
  useEffect(() => {
    // Setup auto-sync when coming online
    const cleanupAutoSync = setupAutoSync();

    // Listen for sync events
    const cleanupListener = addSyncListener((event: SyncEvent) => {
      switch (event.type) {
        case "sync_started":
          setStatus((prev) => ({ ...prev, isSyncing: true }));
          break;

        case "sync_completed":
          if (event.data?.result) {
            updateLastSyncTime();
            setStatus((prev) => ({
              ...prev,
              isSyncing: false,
              lastSyncResult: event.data!.result,
              lastSyncTime: new Date(),
              pendingCount: 0,
              failedCount: event.data!.result!.failedCount,
            }));
          }
          break;

        case "sync_failed":
          setStatus((prev) => ({
            ...prev,
            isSyncing: false,
          }));
          break;

        case "conflict_detected":
          if (event.data?.conflict) {
            setStatus((prev) => ({
              ...prev,
              conflicts: [...prev.conflicts, event.data!.conflict!],
            }));
          }
          break;

        case "change_synced":
          setStatus((prev) => ({
            ...prev,
            pendingCount: Math.max(0, prev.pendingCount - 1),
          }));
          break;

        case "change_failed":
          setStatus((prev) => ({
            ...prev,
            failedCount: prev.failedCount + 1,
          }));
          break;
      }
    });

    cleanupRef.current = () => {
      cleanupAutoSync();
      cleanupListener();
    };

    return () => {
      if (cleanupRef.current) {
        cleanupRef.current();
      }
    };
  }, []);

  // Update online status
  useEffect(() => {
    const handleOnline = () => {
      setStatus((prev) => ({ ...prev, isOnline: true }));
    };

    const handleOffline = () => {
      setStatus((prev) => ({ ...prev, isOnline: false }));
    };

    if (typeof window !== "undefined") {
      window.addEventListener("online", handleOnline);
      window.addEventListener("offline", handleOffline);

      return () => {
        window.removeEventListener("online", handleOnline);
        window.removeEventListener("offline", handleOffline);
      };
    }
  }, []);

  /**
   * Manually trigger sync
   */
  const sync = useCallback(
    async (
      strategy: ConflictResolutionStrategy = "last_write_wins"
    ): Promise<SyncResult> => {
      if (!status.isOnline) {
        return {
          success: false,
          syncedCount: 0,
          failedCount: 0,
          conflictCount: 0,
          results: [],
          serverTimestamp: new Date().toISOString(),
        };
      }

      return syncPendingChanges(strategy);
    },
    [status.isOnline]
  );

  /**
   * Retry failed operations
   */
  const retry = useCallback(
    async (maxRetries: number = 3): Promise<SyncResult> => {
      if (!status.isOnline) {
        return {
          success: false,
          syncedCount: 0,
          failedCount: 0,
          conflictCount: 0,
          results: [],
          serverTimestamp: new Date().toISOString(),
        };
      }

      return retryFailedOperations(maxRetries);
    },
    [status.isOnline]
  );

  /**
   * Clear conflicts list
   */
  const clearConflicts = useCallback(() => {
    setStatus((prev) => ({ ...prev, conflicts: [] }));
  }, []);

  /**
   * Refresh status from IndexedDB
   */
  const refreshStatus = useCallback(async () => {
    const syncStatus = await getSyncStatus();
    setStatus((prev) => ({
      ...prev,
      pendingCount: syncStatus.pendingCount,
      failedCount: syncStatus.failedCount,
      isOnline: syncStatus.isOnline,
      lastSyncTime: syncStatus.lastSyncTime
        ? new Date(syncStatus.lastSyncTime)
        : prev.lastSyncTime,
    }));
  }, []);

  return {
    ...status,
    sync,
    retry,
    clearConflicts,
    refreshStatus,
    hasPendingChanges: status.pendingCount > 0,
    hasFailedChanges: status.failedCount > 0,
    hasConflicts: status.conflicts.length > 0,
  };
}

export default useSync;
