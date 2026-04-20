import { apiClient } from "./client";
import {
  addToQueue,
  cacheEntity,
  getCachedEntity,
  updateCachedEntity,
  EntityType,
  QueuedOperation,
} from "@/lib/offline";

/**
 * Options for offline-aware API requests
 */
export interface OfflineRequestOptions {
  entityType: EntityType;
  entityId?: string;
  cacheResponse?: boolean;
  cacheTTL?: number;
}

/**
 * Check if the browser is currently online
 */
function isOnline(): boolean {
  return typeof navigator !== "undefined" ? navigator.onLine : true;
}

/**
 * Generate a temporary ID for new entities created offline
 */
export function generateTempId(): string {
  return `temp_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
}

/**
 * Offline-aware API client that queues modifications when offline
 * and serves cached data for reads
 */
export const offlineApiClient = {
  /**
   * GET request with offline caching support
   */
  async get<T>(
    endpoint: string,
    options?: OfflineRequestOptions
  ): Promise<T | null> {
    // Try online request first
    if (isOnline()) {
      try {
        const response = await apiClient.get<T>(endpoint);

        // Cache the response if requested
        if (options?.cacheResponse && options.entityType && options.entityId) {
          await cacheEntity(
            options.entityType,
            options.entityId,
            response as Record<string, unknown>,
            { ttl: options.cacheTTL }
          );
        }

        return response;
      } catch (error) {
        // If network error, fall through to cache
        if (error instanceof TypeError && error.message.includes("fetch")) {
          console.warn("Network error, falling back to cache");
        } else {
          throw error;
        }
      }
    }

    // Offline: try to get from cache
    if (options?.entityType && options?.entityId) {
      const cached = await getCachedEntity(options.entityType, options.entityId);
      if (cached) {
        return cached.data as T;
      }
    }

    return null;
  },

  /**
   * POST request with offline queue support
   */
  async post<T>(
    endpoint: string,
    data: Record<string, unknown>,
    options: OfflineRequestOptions
  ): Promise<T | QueuedOperation> {
    if (isOnline()) {
      try {
        const response = await apiClient.post<T>(endpoint, data);

        // Cache the response if it has an ID
        if (options.cacheResponse && options.entityType) {
          const responseData = response as Record<string, unknown>;
          const entityId = (responseData.id as string) || options.entityId;
          if (entityId) {
            await cacheEntity(options.entityType, entityId, responseData, {
              ttl: options.cacheTTL,
            });
          }
        }

        return response;
      } catch (error) {
        // If network error, queue the operation
        if (error instanceof TypeError && error.message.includes("fetch")) {
          console.warn("Network error, queuing operation");
        } else {
          throw error;
        }
      }
    }

    // Offline: queue the operation
    const entityId = options.entityId || generateTempId();
    const queued = await addToQueue({
      entityType: options.entityType,
      entityId,
      operation: "create",
      data,
      endpoint,
      method: "POST",
    });

    // Optimistically cache the data
    await cacheEntity(options.entityType, entityId, {
      ...data,
      id: entityId,
      _pendingSync: true,
    });

    return queued;
  },

  /**
   * PUT request with offline queue support
   */
  async put<T>(
    endpoint: string,
    data: Record<string, unknown>,
    options: OfflineRequestOptions & { entityId: string }
  ): Promise<T | QueuedOperation> {
    if (isOnline()) {
      try {
        const response = await apiClient.put<T>(endpoint, data);

        // Update cache
        if (options.cacheResponse && options.entityType) {
          await cacheEntity(
            options.entityType,
            options.entityId,
            response as Record<string, unknown>,
            { ttl: options.cacheTTL }
          );
        }

        return response;
      } catch (error) {
        if (error instanceof TypeError && error.message.includes("fetch")) {
          console.warn("Network error, queuing operation");
        } else {
          throw error;
        }
      }
    }

    // Offline: queue the operation
    const queued = await addToQueue({
      entityType: options.entityType,
      entityId: options.entityId,
      operation: "update",
      data,
      endpoint,
      method: "PUT",
    });

    // Optimistically update cache
    await updateCachedEntity(options.entityType, options.entityId, {
      ...data,
      _pendingSync: true,
    });

    return queued;
  },

  /**
   * PATCH request with offline queue support
   */
  async patch<T>(
    endpoint: string,
    data: Record<string, unknown>,
    options: OfflineRequestOptions & { entityId: string }
  ): Promise<T | QueuedOperation> {
    if (isOnline()) {
      try {
        const response = await apiClient.patch<T>(endpoint, data);

        // Update cache
        if (options.cacheResponse && options.entityType) {
          await updateCachedEntity(
            options.entityType,
            options.entityId,
            response as Record<string, unknown>
          );
        }

        return response;
      } catch (error) {
        if (error instanceof TypeError && error.message.includes("fetch")) {
          console.warn("Network error, queuing operation");
        } else {
          throw error;
        }
      }
    }

    // Offline: queue the operation
    const queued = await addToQueue({
      entityType: options.entityType,
      entityId: options.entityId,
      operation: "update",
      data,
      endpoint,
      method: "PATCH",
    });

    // Optimistically update cache
    await updateCachedEntity(options.entityType, options.entityId, {
      ...data,
      _pendingSync: true,
    });

    return queued;
  },

  /**
   * DELETE request with offline queue support
   */
  async delete<T>(
    endpoint: string,
    options: OfflineRequestOptions & { entityId: string }
  ): Promise<T | QueuedOperation> {
    if (isOnline()) {
      try {
        const response = await apiClient.delete<T>(endpoint);
        return response;
      } catch (error) {
        if (error instanceof TypeError && error.message.includes("fetch")) {
          console.warn("Network error, queuing operation");
        } else {
          throw error;
        }
      }
    }

    // Offline: queue the operation
    const queued = await addToQueue({
      entityType: options.entityType,
      entityId: options.entityId,
      operation: "delete",
      data: {},
      endpoint,
      method: "DELETE",
    });

    // Mark as pending deletion in cache
    await updateCachedEntity(options.entityType, options.entityId, {
      _pendingDelete: true,
      _pendingSync: true,
    });

    return queued;
  },

  /**
   * Check if a response is a queued operation (offline)
   */
  isQueuedOperation(response: unknown): response is QueuedOperation {
    return (
      typeof response === "object" &&
      response !== null &&
      "status" in response &&
      "operation" in response &&
      "entityType" in response
    );
  },
};

export default offlineApiClient;
