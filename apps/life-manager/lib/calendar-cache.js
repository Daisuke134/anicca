// In-process calendar read cache for the 60-second scheduler tick. This cache is intentionally
// non-persistent: a Railway restart only causes the next read to fetch from the inner transport.
"use strict";

const DEFAULT_TTL_MS = 5 * 60_000;
const MINUTE_MS = 60_000;

function configuredTtlMs(explicitTtlMs) {
  const candidate = explicitTtlMs == null ? Number(process.env.LM_CAL_CACHE_TTL_MS) : Number(explicitTtlMs);
  return Number.isFinite(candidate) && candidate >= 0 ? candidate : DEFAULT_TTL_MS;
}

function minuteBucket(value) {
  const epochMs = Date.parse(value);
  return Number.isFinite(epochMs) ? Math.floor(epochMs / MINUTE_MS) : String(value == null ? "" : value);
}

function cacheKey(uid, { timeMin, timeMax } = {}) {
  return [uid, minuteBucket(timeMin), minuteBucket(timeMax)].join("|");
}

function makeCachedCalendar(inner, opts = {}) {
  const ttlMs = configuredTtlMs(opts.ttlMs);
  const now = opts.now || Date.now;
  const entries = new Map();

  function invalidateUid(uid) {
    for (const [key, entry] of entries) {
      if (entry.uid === uid) entries.delete(key);
    }
  }

  return {
    ...inner,
    async listEventsRaw(uid, input = {}) {
      const key = cacheKey(uid, input);
      const timestamp = now();
      const hit = entries.get(key);
      if (hit && timestamp - hit.fetchedAt < ttlMs) return hit.promise;

      const promise = Promise.resolve().then(() => inner.listEventsRaw(uid, input));
      const entry = { uid, fetchedAt: timestamp, promise };
      entries.set(key, entry);
      try {
        return await promise;
      } catch (error) {
        if (entries.get(key) === entry) entries.delete(key);
        throw error;
      }
    },
    async createEvent(uid, input) {
      const result = await inner.createEvent(uid, input);
      invalidateUid(uid);
      return result;
    },
    async patchEvent(uid, input) {
      const result = await inner.patchEvent(uid, input);
      invalidateUid(uid);
      return result;
    },
  };
}

module.exports = { makeCachedCalendar, cacheKey, DEFAULT_TTL_MS };
