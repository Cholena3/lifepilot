"use client";

import { useCallback, useEffect, useState } from "react";
import { useOnlineStatus } from "./useOnlineStatus";
import {
  addToQueue,
  getPendingOperations,
  getPendingCount,
  getAllOperations,
  clearCompletedOperations,
  QueuedOperation,
  EntityType,
  OperationType,
  QueueOperationOptions,
} from "@/lib/offline";

/**
 * Options for queuing a modification
 */
export interface QueueModificationOptions {
  entityType: EntityType;
  entityId: string;
  operation: OperationType;
  data: Record<string, unknown>;
  endpoint: string;
  method: "POST" | "PUT" | "PATCH" | "DELETE";
}

/**
 * Hook for managing offline data modification queue
 *
 * Provides functionality to:
 * - Queue modifications when offline
 * - Track pending operations count
 * - Access queued operations
 * - Clear completed operations
 *
 * @returns Object containing queue state and operations
 */
export function useOfflineQueue() {
  const { isOnline, isOffline } = useOnlineStatus();
  const [pendingCount, setPendingCount] = useState(0);
  const [operations, setOperations] = useState<QueuedOperation[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  /**
   * Load pending operations count and list
   */
  const refreshQueue = useCallback(async () => {
    try {
      const [count, ops] = await Promise.all([
        getPendingCount(),
        getAllOperations(),
      ]);
      setPendingCount(count);
      setOperations(ops);
    } catch (error) {
      console.error("Failed to refresh offline queue:", error);
    }
  }, []);

  /**
   * Queue a modification for later sync
   */
  const queueModification = useCallback(
    async (options: QueueModificationOptions): Promise<QueuedOperation> => {
      const queueOptions: QueueOperationOptions = {
        entityType: options.entityType,
        entityId: options.entityId,
        operation: options.operation,
        data: options.data,
        endpoint: options.endpoint,
        method: options.method,
      };

      const queued = await addToQueue(queueOptions);
      await refreshQueue();
      return queued;
    },
    [refreshQueue]
  );

  /**
   * Clear all completed operations from the queue
   */
  const clearCompleted = useCallback(async (): Promise<number> => {
    const cleared = await clearCompletedOperations();
    await refreshQueue();
    return cleared;
  }, [refreshQueue]);

  /**
   * Get pending operations
   */
  const getPending = useCallback(async (): Promise<QueuedOperation[]> => {
    return getPendingOperations();
  }, []);

  // Initial load
  useEffect(() => {
    const init = async () => {
      setIsLoading(true);
      await refreshQueue();
      setIsLoading(false);
    };
    init();
  }, [refreshQueue]);

  // Refresh when coming back online
  useEffect(() => {
    if (isOnline) {
      refreshQueue();
    }
  }, [isOnline, refreshQueue]);

  return {
    // State
    isOnline,
    isOffline,
    pendingCount,
    operations,
    isLoading,
    hasPendingChanges: pendingCount > 0,

    // Actions
    queueModification,
    clearCompleted,
    getPending,
    refreshQueue,
  };
}

export default useOfflineQueue;
