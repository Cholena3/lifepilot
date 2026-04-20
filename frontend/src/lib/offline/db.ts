import { openDB, DBSchema, IDBPDatabase } from "idb";

/**
 * Entity types that can be queued for offline sync
 */
export type EntityType =
  | "expense"
  | "document"
  | "health_record"
  | "medicine"
  | "vital"
  | "wardrobe_item"
  | "skill"
  | "course"
  | "job_application"
  | "achievement";

/**
 * Operation types for offline queue
 */
export type OperationType = "create" | "update" | "delete";

/**
 * Status of a queued operation
 */
export type QueueStatus = "pending" | "syncing" | "failed" | "completed";

/**
 * Metadata for a queued offline operation
 */
export interface QueuedOperation {
  id: string;
  entityType: EntityType;
  entityId: string;
  operation: OperationType;
  data: Record<string, unknown>;
  endpoint: string;
  method: "POST" | "PUT" | "PATCH" | "DELETE";
  timestamp: number;
  status: QueueStatus;
  retryCount: number;
  lastError?: string;
  userId?: string;
}

/**
 * Cached entity data for offline viewing
 */
export interface CachedEntity {
  id: string;
  entityType: EntityType;
  data: Record<string, unknown>;
  cachedAt: number;
  expiresAt?: number;
}

/**
 * IndexedDB schema for LifePilot offline storage
 */
interface LifePilotDB extends DBSchema {
  offlineQueue: {
    key: string;
    value: QueuedOperation;
    indexes: {
      "by-status": QueueStatus;
      "by-entity": [EntityType, string];
      "by-timestamp": number;
    };
  };
  cachedEntities: {
    key: string;
    value: CachedEntity;
    indexes: {
      "by-type": EntityType;
      "by-expiry": number;
    };
  };
}

const DB_NAME = "lifepilot-offline";
const DB_VERSION = 1;

let dbInstance: IDBPDatabase<LifePilotDB> | null = null;

/**
 * Initialize and get the IndexedDB database instance
 */
export async function getDB(): Promise<IDBPDatabase<LifePilotDB>> {
  if (dbInstance) {
    return dbInstance;
  }

  dbInstance = await openDB<LifePilotDB>(DB_NAME, DB_VERSION, {
    upgrade(db) {
      // Create offline queue store
      if (!db.objectStoreNames.contains("offlineQueue")) {
        const queueStore = db.createObjectStore("offlineQueue", {
          keyPath: "id",
        });
        queueStore.createIndex("by-status", "status");
        queueStore.createIndex("by-entity", ["entityType", "entityId"]);
        queueStore.createIndex("by-timestamp", "timestamp");
      }

      // Create cached entities store
      if (!db.objectStoreNames.contains("cachedEntities")) {
        const cacheStore = db.createObjectStore("cachedEntities", {
          keyPath: "id",
        });
        cacheStore.createIndex("by-type", "entityType");
        cacheStore.createIndex("by-expiry", "expiresAt");
      }
    },
    blocked() {
      console.warn("LifePilot DB blocked - close other tabs");
    },
    blocking() {
      // Close the database if we're blocking a newer version
      dbInstance?.close();
      dbInstance = null;
    },
  });

  return dbInstance;
}

/**
 * Generate a unique ID for queue operations
 */
export function generateQueueId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
}

/**
 * Close the database connection
 */
export async function closeDB(): Promise<void> {
  if (dbInstance) {
    dbInstance.close();
    dbInstance = null;
  }
}
