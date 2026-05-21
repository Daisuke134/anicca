import { prisma } from '../../lib/prisma.js';

// In-memory cache (5min TTL)
const cache = new Map();
const CACHE_TTL_MS = 5 * 60 * 1000;

/**
 * Get policy value (with cache)
 * @param {string} key
 * @returns {Promise<Object|null>}
 */
export async function getPolicy(key) {
  const cached = cache.get(key);
  if (cached && Date.now() - cached.fetchedAt < CACHE_TTL_MS) {
    return cached.value;
  }

  const row = await prisma.opsPolicy.findUnique({ where: { key } });
  const value = row?.value ?? null;

  cache.set(key, { value, fetchedAt: Date.now() });
  return value;
}

/**
 * Set policy value (invalidates cache)
 * @param {string} key
 * @param {Object} value
 */
export async function setPolicy(key, value) {
  await prisma.opsPolicy.upsert({
    where: { key },
    create: { key, value },
    update: { value, updatedAt: new Date() }
  });

  cache.delete(key);
}

/**
 * Clear cache (for testing)
 */
export function clearPolicyCache() {
  cache.clear();
}
