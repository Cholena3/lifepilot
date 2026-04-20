// Database types and utilities
export {
  getDB,
  closeDB,
  generateQueueId,
  type EntityType,
  type OperationType,
  type QueueStatus,
  type QueuedOperation,
  type CachedEntity,
} from "./db";

// Queue operations
export {
  addToQueue,
  getPendingOperations,
  getAllOperations,
  getOperationsForEntity,
  updateOperationStatus,
  removeFromQueue,
  clearCompletedOperations,
  getPendingCount,
  hasPendingOperations,
  resetFailedOperations,
  clearQueue,
  type QueueOperationOptions,
} from "./queue";

// Cache operations
export {
  cacheEntity,
  getCachedEntity,
  getCachedEntitiesByType,
  removeCachedEntity,
  clearExpiredCache,
  clearCacheByType,
  clearAllCache,
  updateCachedEntity,
  type CacheOptions,
} from "./cache";

// Sync operations
export {
  syncPendingChanges,
  retryFailedOperations,
  setupAutoSync,
  getSyncStatus,
  updateLastSyncTime,
  clearSyncData,
  addSyncListener,
  type ConflictResolutionStrategy,
  type SyncConflict,
  type SyncChangeResult,
  type SyncResult,
  type SyncEventType,
  type SyncEvent,
  type SyncEventListener,
} from "./sync";
