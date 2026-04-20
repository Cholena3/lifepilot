/**
 * Sync service for offline data synchronization with conflict resolution.
 *
 * Validates: Requirements 35.4
 *
 * Features:
 * - Sync queued changes when online
 * - Last-write-wins conflict resolution
 * - Notify users of sync conflicts
 * - Update local cache after successful sync
 */

import { apiClient } from "@/lib/api/client";
import {
  getDB,
  QueuedOperation,
  QueueStatus,
  EntityType,
  OperationType,
} from "./db";
import {
  getPendingOperations,
  updateOperationStatus,
  removeFromQueue,
  clearCompletedOperations,
} from "./queue";
import {
  cacheEntity,
  removeCachedEntity,
  updateCachedEntity,
} from "./cache";

/**
 * Conflict resolution strategy
 */
export type ConflictResolutionStrategy =
  | "last_write_wins"
  | "server_wins"
  | "client_wins";

/**
 * Sync conflict details
 */
export interface SyncConflict {
  changeId: string;
  entityType: EntityType;
  entityId: string;
  clientData: Record<string, unknown>;
  serverData: Record<string, unknown>;
  clientTimestamp: number;
  serverTimestamp: string;
  resolution: ConflictResolutionStrategy;
  resolvedData: Record<string, unknown>;
}

/**
 * Result of syncing a single change
 */
export interface SyncChangeResult {
  changeId: string;
  success: boolean;
  entityId: string;
  conflict?: SyncConflict;
  error?: string;
}

/**
 * Overall sync result
 */
export interface SyncResult {
  success: boolean;
  syncedCount: number;
  failedCount: number;
  conflictCount: number;
  results: SyncChangeResult[];
  serverTimestamp: string;
}

/**
 * Sync event types for listeners
 */
export type SyncEventType =
  | "sync_started"
  | "sync_completed"
  | "sync_failed"
  | "conflict_detected"
  | "change_synced"
  | "change_failed";

/**
 * Sync event data
 */
export interface SyncEvent {
  type: SyncEventType;
  data?: {
    result?: SyncResult;
    change?: QueuedOperation;
    conflict?: SyncConflict;
    error?: string;
  };
}

/**
 * Sync event listener
 */
export type SyncEventListener = (event: SyncEvent) => void;

// Event listeners
const listeners: Set<SyncEventListener> = new Set();

/**
 * Add a sync event listener
 */
export function addSyncListener(listener: SyncEventListener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/**
 * Emit a sync event to all listeners
 */
function emitSyncEvent(event: SyncEvent): void {
  listeners.forEach((listener) => {
    try {
      listener(event);
    } catch (error) {
      console.error("Error in sync event listener:", error);
    }
  });
}

/**
 * Check if the browser is currently online
 */
function isOnline(): boolean {
  return typeof navigator !== "undefined" ? navigator.onLine : true;
}

/**
 * Convert frontend entity type to backend format
 */
function toBackendEntityType(entityType: EntityType): string {
  return entityType;
}

/**
 * Convert frontend operation type to backend format
 */
function toBackendOperationType(operation: OperationType): string {
  return operation;
}

/**
 * Sync all pending operations to the server
 *
 * Validates: Requirements 35.4
 */
export async function syncPendingChanges(
  resolutionStrategy: ConflictResolutionStrategy = "last_write_wins"
): Promise<SyncResult> {
  if (!isOnline()) {
    return {
      success: false,
      syncedCount: 0,
      failedCount: 0,
      conflictCount: 0,
      results: [],
      serverTimestamp: new Date().toISOString(),
    };
  }

  const pendingOperations = await getPendingOperations();

  if (pendingOperations.length === 0) {
    return {
      success: true,
      syncedCount: 0,
      failedCount: 0,
      conflictCount: 0,
      results: [],
      serverTimestamp: new Date().toISOString(),
    };
  }

  emitSyncEvent({ type: "sync_started" });

  // Mark all operations as syncing
  for (const op of pendingOperations) {
    await updateOperationStatus(op.id, "syncing");
  }

  try {
    // Prepare changes for the API
    const changes = pendingOperations.map((op) => ({
      id: op.id,
      entity_type: toBackendEntityType(op.entityType),
      entity_id: op.entityId,
      operation: toBackendOperationType(op.operation),
      data: op.data,
      timestamp: op.timestamp,
      endpoint: op.endpoint,
      method: op.method,
    }));

    // Send to server
    const response = await apiClient.post<{
      success: boolean;
      synced_count: number;
      failed_count: number;
      conflict_count: number;
      results: Array<{
        change_id: string;
        success: boolean;
        entity_id: string;
        conflict?: {
          change_id: string;
          entity_type: string;
          entity_id: string;
          client_data: Record<string, unknown>;
          server_data: Record<string, unknown>;
          client_timestamp: number;
          server_timestamp: string;
          resolution: string;
          resolved_data: Record<string, unknown>;
        };
        error?: string;
      }>;
      server_timestamp: string;
    }>("/api/v1/sync/changes", {
      changes,
      resolution_strategy: resolutionStrategy,
    });

    // Process results
    const results: SyncChangeResult[] = [];

    for (const result of response.results) {
      const operation = pendingOperations.find((op) => op.id === result.change_id);

      if (result.success) {
        // Update operation status to completed
        await updateOperationStatus(result.change_id, "completed");

        // Update local cache
        if (operation) {
          await updateLocalCache(operation, result.entity_id);
        }

        // Remove from queue
        await removeFromQueue(result.change_id);

        emitSyncEvent({
          type: "change_synced",
          data: { change: operation },
        });
      } else {
        // Update operation status to failed
        await updateOperationStatus(result.change_id, "failed", result.error);

        emitSyncEvent({
          type: "change_failed",
          data: { change: operation, error: result.error },
        });
      }

      // Handle conflict notification
      if (result.conflict) {
        const conflict: SyncConflict = {
          changeId: result.conflict.change_id,
          entityType: result.conflict.entity_type as EntityType,
          entityId: result.conflict.entity_id,
          clientData: result.conflict.client_data,
          serverData: result.conflict.server_data,
          clientTimestamp: result.conflict.client_timestamp,
          serverTimestamp: result.conflict.server_timestamp,
          resolution: result.conflict.resolution as ConflictResolutionStrategy,
          resolvedData: result.conflict.resolved_data,
        };

        emitSyncEvent({
          type: "conflict_detected",
          data: { conflict },
        });

        results.push({
          changeId: result.change_id,
          success: result.success,
          entityId: result.entity_id,
          conflict,
          error: result.error,
        });
      } else {
        results.push({
          changeId: result.change_id,
          success: result.success,
          entityId: result.entity_id,
          error: result.error,
        });
      }
    }

    const syncResult: SyncResult = {
      success: response.success,
      syncedCount: response.synced_count,
      failedCount: response.failed_count,
      conflictCount: response.conflict_count,
      results,
      serverTimestamp: response.server_timestamp,
    };

    emitSyncEvent({
      type: "sync_completed",
      data: { result: syncResult },
    });

    return syncResult;
  } catch (error) {
    // Reset operations to pending on error
    for (const op of pendingOperations) {
      await updateOperationStatus(op.id, "pending");
    }

    const errorMessage = error instanceof Error ? error.message : "Unknown error";

    emitSyncEvent({
      type: "sync_failed",
      data: { error: errorMessage },
    });

    return {
      success: false,
      syncedCount: 0,
      failedCount: pendingOperations.length,
      conflictCount: 0,
      results: pendingOperations.map((op) => ({
        changeId: op.id,
        success: false,
        entityId: op.entityId,
        error: errorMessage,
      })),
      serverTimestamp: new Date().toISOString(),
    };
  }
}

/**
 * Update local cache after successful sync
 */
async function updateLocalCache(
  operation: QueuedOperation,
  newEntityId: string
): Promise<void> {
  const { entityType, entityId, operation: opType, data } = operation;

  try {
    if (opType === "create") {
      // For creates, update the cache with the new server ID
      // Remove the temp ID entry
      await removeCachedEntity(entityType, entityId);

      // Cache with the new server ID
      await cacheEntity(entityType, newEntityId, {
        ...data,
        id: newEntityId,
        _pendingSync: false,
      });
    } else if (opType === "update") {
      // For updates, update the cache with synced data
      await updateCachedEntity(entityType, entityId, {
        ...data,
        _pendingSync: false,
      });
    } else if (opType === "delete") {
      // For deletes, remove from cache
      await removeCachedEntity(entityType, entityId);
    }
  } catch (error) {
    console.error("Error updating local cache:", error);
  }
}

/**
 * Retry failed sync operations
 */
export async function retryFailedOperations(
  maxRetries: number = 3
): Promise<SyncResult> {
  const db = await getDB();
  const failed = await db.getAllFromIndex("offlineQueue", "by-status", "failed");

  // Filter operations that haven't exceeded max retries
  const toRetry = failed.filter((op) => op.retryCount < maxRetries);

  if (toRetry.length === 0) {
    return {
      success: true,
      syncedCount: 0,
      failedCount: 0,
      conflictCount: 0,
      results: [],
      serverTimestamp: new Date().toISOString(),
    };
  }

  // Reset to pending
  for (const op of toRetry) {
    await updateOperationStatus(op.id, "pending");
  }

  // Sync again
  return syncPendingChanges();
}

/**
 * Auto-sync when coming back online
 */
export function setupAutoSync(): () => void {
  const handleOnline = async () => {
    console.log("Connection restored, starting auto-sync...");
    try {
      const result = await syncPendingChanges();
      console.log(
        `Auto-sync completed: ${result.syncedCount} synced, ${result.failedCount} failed`
      );
    } catch (error) {
      console.error("Auto-sync failed:", error);
    }
  };

  if (typeof window !== "undefined") {
    window.addEventListener("online", handleOnline);
    return () => window.removeEventListener("online", handleOnline);
  }

  return () => {};
}

/**
 * Get sync status summary
 */
export async function getSyncStatus(): Promise<{
  pendingCount: number;
  failedCount: number;
  isOnline: boolean;
  lastSyncTime?: number;
}> {
  const db = await getDB();
  const pending = await db.countFromIndex("offlineQueue", "by-status", "pending");
  const failed = await db.countFromIndex("offlineQueue", "by-status", "failed");

  // Get last sync time from localStorage
  let lastSyncTime: number | undefined;
  if (typeof localStorage !== "undefined") {
    const stored = localStorage.getItem("lifepilot-last-sync");
    if (stored) {
      lastSyncTime = parseInt(stored, 10);
    }
  }

  return {
    pendingCount: pending,
    failedCount: failed,
    isOnline: isOnline(),
    lastSyncTime,
  };
}

/**
 * Update last sync time
 */
export function updateLastSyncTime(): void {
  if (typeof localStorage !== "undefined") {
    localStorage.setItem("lifepilot-last-sync", Date.now().toString());
  }
}

/**
 * Clear all sync data (use with caution)
 */
export async function clearSyncData(): Promise<void> {
  await clearCompletedOperations();
}
