import {
  getDB,
  generateQueueId,
  QueuedOperation,
  EntityType,
  OperationType,
  QueueStatus,
} from "./db";

/**
 * Options for adding an operation to the offline queue
 */
export interface QueueOperationOptions {
  entityType: EntityType;
  entityId: string;
  operation: OperationType;
  data: Record<string, unknown>;
  endpoint: string;
  method: "POST" | "PUT" | "PATCH" | "DELETE";
  userId?: string;
}

/**
 * Add an operation to the offline queue
 */
export async function addToQueue(
  options: QueueOperationOptions
): Promise<QueuedOperation> {
  const db = await getDB();

  const queuedOperation: QueuedOperation = {
    id: generateQueueId(),
    entityType: options.entityType,
    entityId: options.entityId,
    operation: options.operation,
    data: options.data,
    endpoint: options.endpoint,
    method: options.method,
    timestamp: Date.now(),
    status: "pending",
    retryCount: 0,
    userId: options.userId,
  };

  await db.put("offlineQueue", queuedOperation);

  return queuedOperation;
}

/**
 * Get all pending operations from the queue
 */
export async function getPendingOperations(): Promise<QueuedOperation[]> {
  const db = await getDB();
  return db.getAllFromIndex("offlineQueue", "by-status", "pending");
}

/**
 * Get all operations from the queue (any status)
 */
export async function getAllOperations(): Promise<QueuedOperation[]> {
  const db = await getDB();
  const operations = await db.getAll("offlineQueue");
  // Sort by timestamp ascending (oldest first)
  return operations.sort((a, b) => a.timestamp - b.timestamp);
}

/**
 * Get operations for a specific entity
 */
export async function getOperationsForEntity(
  entityType: EntityType,
  entityId: string
): Promise<QueuedOperation[]> {
  const db = await getDB();
  return db.getAllFromIndex("offlineQueue", "by-entity", [entityType, entityId]);
}

/**
 * Update the status of a queued operation
 */
export async function updateOperationStatus(
  id: string,
  status: QueueStatus,
  error?: string
): Promise<void> {
  const db = await getDB();
  const operation = await db.get("offlineQueue", id);

  if (operation) {
    operation.status = status;
    if (error) {
      operation.lastError = error;
    }
    if (status === "failed") {
      operation.retryCount += 1;
    }
    await db.put("offlineQueue", operation);
  }
}

/**
 * Remove a completed operation from the queue
 */
export async function removeFromQueue(id: string): Promise<void> {
  const db = await getDB();
  await db.delete("offlineQueue", id);
}

/**
 * Remove all completed operations from the queue
 */
export async function clearCompletedOperations(): Promise<number> {
  const db = await getDB();
  const completed = await db.getAllFromIndex(
    "offlineQueue",
    "by-status",
    "completed"
  );

  const tx = db.transaction("offlineQueue", "readwrite");
  await Promise.all([
    ...completed.map((op) => tx.store.delete(op.id)),
    tx.done,
  ]);

  return completed.length;
}

/**
 * Get the count of pending operations
 */
export async function getPendingCount(): Promise<number> {
  const db = await getDB();
  return db.countFromIndex("offlineQueue", "by-status", "pending");
}

/**
 * Check if there are any pending operations for an entity
 */
export async function hasPendingOperations(
  entityType: EntityType,
  entityId: string
): Promise<boolean> {
  const operations = await getOperationsForEntity(entityType, entityId);
  return operations.some((op) => op.status === "pending");
}

/**
 * Reset failed operations to pending for retry
 */
export async function resetFailedOperations(maxRetries = 3): Promise<number> {
  const db = await getDB();
  const failed = await db.getAllFromIndex("offlineQueue", "by-status", "failed");

  const toReset = failed.filter((op) => op.retryCount < maxRetries);

  const tx = db.transaction("offlineQueue", "readwrite");
  await Promise.all([
    ...toReset.map((op) => {
      op.status = "pending";
      return tx.store.put(op);
    }),
    tx.done,
  ]);

  return toReset.length;
}

/**
 * Clear all operations from the queue (use with caution)
 */
export async function clearQueue(): Promise<void> {
  const db = await getDB();
  await db.clear("offlineQueue");
}
