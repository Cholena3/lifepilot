import { getDB, CachedEntity, EntityType } from "./db";

/**
 * Default cache TTL in milliseconds (24 hours)
 */
const DEFAULT_CACHE_TTL = 24 * 60 * 60 * 1000;

/**
 * Options for caching an entity
 */
export interface CacheOptions {
  ttl?: number; // Time to live in milliseconds
}

/**
 * Cache an entity for offline viewing
 */
export async function cacheEntity(
  entityType: EntityType,
  entityId: string,
  data: Record<string, unknown>,
  options: CacheOptions = {}
): Promise<CachedEntity> {
  const db = await getDB();
  const now = Date.now();
  const ttl = options.ttl ?? DEFAULT_CACHE_TTL;

  const cachedEntity: CachedEntity = {
    id: `${entityType}:${entityId}`,
    entityType,
    data,
    cachedAt: now,
    expiresAt: now + ttl,
  };

  await db.put("cachedEntities", cachedEntity);

  return cachedEntity;
}

/**
 * Get a cached entity
 */
export async function getCachedEntity(
  entityType: EntityType,
  entityId: string
): Promise<CachedEntity | undefined> {
  const db = await getDB();
  const key = `${entityType}:${entityId}`;
  const cached = await db.get("cachedEntities", key);

  // Check if expired
  if (cached && cached.expiresAt && cached.expiresAt < Date.now()) {
    await db.delete("cachedEntities", key);
    return undefined;
  }

  return cached;
}

/**
 * Get all cached entities of a specific type
 */
export async function getCachedEntitiesByType(
  entityType: EntityType
): Promise<CachedEntity[]> {
  const db = await getDB();
  const entities = await db.getAllFromIndex(
    "cachedEntities",
    "by-type",
    entityType
  );

  // Filter out expired entities
  const now = Date.now();
  const valid = entities.filter(
    (entity) => !entity.expiresAt || entity.expiresAt >= now
  );

  // Clean up expired entities
  const expired = entities.filter(
    (entity) => entity.expiresAt && entity.expiresAt < now
  );
  if (expired.length > 0) {
    const tx = db.transaction("cachedEntities", "readwrite");
    await Promise.all([
      ...expired.map((entity) => tx.store.delete(entity.id)),
      tx.done,
    ]);
  }

  return valid;
}

/**
 * Remove a cached entity
 */
export async function removeCachedEntity(
  entityType: EntityType,
  entityId: string
): Promise<void> {
  const db = await getDB();
  const key = `${entityType}:${entityId}`;
  await db.delete("cachedEntities", key);
}

/**
 * Clear all expired cached entities
 */
export async function clearExpiredCache(): Promise<number> {
  const db = await getDB();
  const now = Date.now();

  // Get all entities and filter expired ones
  const allEntities = await db.getAll("cachedEntities");
  const expired = allEntities.filter(
    (entity) => entity.expiresAt && entity.expiresAt < now
  );

  if (expired.length > 0) {
    const tx = db.transaction("cachedEntities", "readwrite");
    await Promise.all([
      ...expired.map((entity) => tx.store.delete(entity.id)),
      tx.done,
    ]);
  }

  return expired.length;
}

/**
 * Clear all cached entities of a specific type
 */
export async function clearCacheByType(entityType: EntityType): Promise<number> {
  const db = await getDB();
  const entities = await db.getAllFromIndex(
    "cachedEntities",
    "by-type",
    entityType
  );

  if (entities.length > 0) {
    const tx = db.transaction("cachedEntities", "readwrite");
    await Promise.all([
      ...entities.map((entity) => tx.store.delete(entity.id)),
      tx.done,
    ]);
  }

  return entities.length;
}

/**
 * Clear all cached entities
 */
export async function clearAllCache(): Promise<void> {
  const db = await getDB();
  await db.clear("cachedEntities");
}

/**
 * Update cached entity data (for optimistic updates)
 */
export async function updateCachedEntity(
  entityType: EntityType,
  entityId: string,
  updates: Partial<Record<string, unknown>>
): Promise<CachedEntity | undefined> {
  const db = await getDB();
  const key = `${entityType}:${entityId}`;
  const cached = await db.get("cachedEntities", key);

  if (cached) {
    cached.data = { ...cached.data, ...updates };
    cached.cachedAt = Date.now();
    await db.put("cachedEntities", cached);
    return cached;
  }

  return undefined;
}
