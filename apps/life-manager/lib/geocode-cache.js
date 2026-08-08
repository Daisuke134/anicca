// Persistent address -> coordinate cache used by the cloud travel filler.
//
// Coordinates are a shared fact about an address, not a user-owned event.  The
// cache therefore uses a canonical address key and is protected by the
// backend's service-role-only Supabase table.  A process-local Map remains a
// read-through optimization; it is never the production source of truth.
"use strict";

const DEFAULT_TABLE = "lm_geocode_cache";
const { recordGoogleGeocoding } = require("./provider-cost-adapters.js");

function normalizeGeocodeAddress(value) {
  if (value == null) return "";
  return String(value)
    .normalize("NFKC")
    .replace(/\s+/gu, " ")
    .trim()
    .toLocaleLowerCase("en-US");
}

function finiteCoordinate(value, min, max) {
  const n = Number(value);
  return Number.isFinite(n) && n >= min && n <= max ? n : null;
}

function validValue(value) {
  if (!value || typeof value !== "object") return null;
  const lat = finiteCoordinate(value.lat, -90, 90);
  const lng = finiteCoordinate(value.lng == null ? value.lon : value.lng, -180, 180);
  if (lat == null || lng == null) return null;
  return {
    lat,
    lng,
    provider: value.provider == null ? "google_geocoding" : String(value.provider),
    resolvedAt: value.resolvedAt || value.resolved_at || new Date().toISOString(),
  };
}

function authHeaders(key, extra) {
  return Object.assign({ apikey: key, Authorization: `Bearer ${key}` }, extra || {});
}

function normalizeStoreRow(row) {
  if (!row || typeof row !== "object") return null;
  return validValue({
    lat: row.lat,
    lng: row.lng == null ? row.lon : row.lng,
    provider: row.provider,
    resolvedAt: row.resolved_at || row.resolvedAt,
  });
}

function createSupabaseGeocodeStore({
  supaUrl,
  supaKey,
  fetchImpl = globalThis.fetch,
  now = () => Date.now(),
  table = DEFAULT_TABLE,
} = {}) {
  const baseUrl = String(supaUrl || "").replace(/\/$/u, "");
  const local = new Map();
  const request = (addressKey) =>
    `${baseUrl}/rest/v1/${encodeURIComponent(table)}?address_key=eq.${encodeURIComponent(addressKey)}&select=address_key,lat,lng,provider,resolved_at&limit=1`;

  async function get(rawKey) {
    const addressKey = normalizeGeocodeAddress(rawKey);
    if (!addressKey) return null;
    const localHit = local.get(addressKey);
    if (localHit) return localHit;
    if (!baseUrl || !supaKey || typeof fetchImpl !== "function") return null;
    try {
      const response = await fetchImpl(request(addressKey), { headers: authHeaders(supaKey) });
      if (!response || !response.ok) return null;
      const rows = await response.json();
      const value = normalizeStoreRow(Array.isArray(rows) ? rows[0] : null);
      if (value) local.set(addressKey, value);
      return value;
    } catch {
      return null;
    }
  }

  async function put(rawKey, rawValue) {
    const addressKey = normalizeGeocodeAddress(rawKey);
    const value = validValue(rawValue);
    if (!addressKey || !value || !baseUrl || !supaKey || typeof fetchImpl !== "function") return false;
    const body = {
      address_key: addressKey,
      lat: value.lat,
      lng: value.lng,
      provider: value.provider,
      resolved_at: value.resolvedAt,
    };
    try {
      const response = await fetchImpl(`${baseUrl}/rest/v1/${encodeURIComponent(table)}`, {
        method: "POST",
        headers: authHeaders(supaKey, {
          "Content-Type": "application/json",
          Prefer: "resolution=merge-duplicates,return=minimal",
        }),
        body: JSON.stringify(body),
      });
      if (!response || !response.ok) return false;
      local.set(addressKey, value);
      return true;
    } catch {
      return false;
    }
  }

  // Exposed for tests and diagnostics without making local state authoritative.
  void now;
  return { get, put };
}

const processMemo = new Map();
let defaultStore;

function getDefaultStore() {
  if (defaultStore !== undefined) return defaultStore;
  const supaUrl = process.env.SUPABASE_URL;
  const supaKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  defaultStore = supaUrl && supaKey
    ? createSupabaseGeocodeStore({ supaUrl, supaKey })
    : null;
  return defaultStore;
}

function valueToGeo(value) {
  const valid = validValue(value);
  return valid ? { lat: valid.lat, lon: valid.lng } : null;
}

// Geocode through the durable store first, then Google exactly once for a
// miss.  Failed/empty provider responses never enter either cache.
async function geocodeAddress(addr, mapsKey, {
  store = getDefaultStore(),
  fetchImpl = globalThis.fetch,
  now = () => new Date().toISOString(),
  uid = null,
  requestId,
  recordProviderCost,
} = {}) {
  const addressKey = normalizeGeocodeAddress(addr);
  if (!addressKey || !mapsKey) return null;
  if (processMemo.has(addressKey)) return processMemo.get(addressKey);

  if (store && typeof store.get === "function") {
    const cached = valueToGeo(await Promise.resolve(store.get(addressKey)).catch(() => null));
    if (cached) {
      processMemo.set(addressKey, cached);
      return cached;
    }
  }

  if (typeof fetchImpl !== "function") return null;
  try {
    const url = `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(addr)}&key=${encodeURIComponent(mapsKey)}`;
    const response = await fetchImpl(url);
    if (!response || !response.ok) return null;
    const json = await response.json();
    const location = json && Array.isArray(json.results) && json.results[0]
      && json.results[0].geometry && json.results[0].geometry.location;
    const value = validValue({
      lat: location && location.lat,
      lng: location && (location.lng == null ? location.lon : location.lng),
      provider: "google_geocoding",
      resolvedAt: now(),
    });
    if (!value) return null;
    const geo = { lat: value.lat, lon: value.lng };
    processMemo.set(addressKey, geo);
    if (store && typeof store.put === "function") await Promise.resolve(store.put(addressKey, value)).catch(() => false);
    if (typeof recordProviderCost === "function") {
      await recordGoogleGeocoding({
        uid,
        requestId: requestId || `google:geocoding:${addressKey}`,
        metadata: { cache: "miss" },
      }, { recordProviderCost }).catch(() => false);
    }
    return geo;
  } catch {
    return null;
  }
}

function clearGeocodeProcessMemo() {
  processMemo.clear();
}

module.exports = {
  DEFAULT_TABLE,
  normalizeGeocodeAddress,
  createSupabaseGeocodeStore,
  geocodeAddress,
  clearGeocodeProcessMemo,
};
