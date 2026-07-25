"use strict";
// lib/care-candidate-search.js — 11b PHY-b (§10 row 11b): discover care candidates
// bound to (detected care category) × (the user's 生活圏 anchors from care-anchors.js).
// Google Places Text Search with a location bias per anchor; any result outside
// radiusM of BOTH anchors is rejected — this is the "Kyoto barber for a Tokyo
// user" guard. A usual provider (いつもの店) for the category is placed first
// regardless of distance: a human returns to their usual shop, we do not
// discover novelty when one exists. Output is exactly the definitions shape
// evaluateCareCandidates (care-candidates.js) consumes; fewer than 3 candidates
// ships with an honest shortfallReason, never padding. fetchImpl + apiKey are
// injected — no env reads, no ambient I/O inside this lib.

const TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json";
const DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json";
const MAX_CANDIDATES = 3;

// Category → Japanese search keyword for the 11a care types
// (care-detector eval phy-cases.jsonl: dental / haircut / clinic — no invented types).
const CATEGORY_KEYWORDS = Object.freeze({
  dental: "歯科",
  haircut: "美容室",
  clinic: "クリニック",
});

const EARTH_RADIUS_M = 6371000;

function haversineM(a, b) {
  const rad = (deg) => (deg * Math.PI) / 180;
  const dLat = rad(b.lat - a.lat);
  const dLng = rad(b.lng - a.lng);
  const h = Math.sin(dLat / 2) ** 2
    + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.sqrt(h));
}

async function textSearch(fetchImpl, apiKey, query, bias) {
  let url = `${TEXT_SEARCH_URL}?query=${encodeURIComponent(query)}&key=${encodeURIComponent(apiKey)}`;
  if (bias) url += `&location=${bias.lat},${bias.lng}&radius=${bias.radiusM}`;
  const response = await fetchImpl(url, { signal: AbortSignal.timeout(15_000) }).catch(() => null);
  if (!response || !response.ok) return [];
  const body = await response.json().catch(() => null);
  return body && body.status === "OK" && Array.isArray(body.results) ? body.results : [];
}

async function placeWebsite(fetchImpl, apiKey, placeId) {
  const url = `${DETAILS_URL}?place_id=${encodeURIComponent(placeId)}`
    + `&fields=${encodeURIComponent("name,website,geometry")}&key=${encodeURIComponent(apiKey)}`;
  const response = await fetchImpl(url, { signal: AbortSignal.timeout(15_000) }).catch(() => null);
  if (!response || !response.ok) return null;
  const body = await response.json().catch(() => null);
  const website = body && body.status === "OK" ? body.result?.website : null;
  return typeof website === "string" && /^https?:\/\//i.test(website) ? website : null;
}

// Anchors are address strings; the same Text Search endpoint resolves them to a
// lat/lng (first result's geometry) so everything stays behind one injectable fetch.
async function geocodeAnchor(fetchImpl, apiKey, address) {
  const results = await textSearch(fetchImpl, apiKey, address, null);
  const location = results[0]?.geometry?.location;
  return Number.isFinite(location?.lat) && Number.isFinite(location?.lng)
    ? { lat: location.lat, lng: location.lng }
    : null;
}

async function searchCareCandidates({ category, anchors, apiKey, fetchImpl = fetch, radiusM = 3000 }) {
  const keyword = CATEGORY_KEYWORDS[category];
  if (!keyword) throw new Error(`unknown care category: ${category}`);

  // Home first, then work if distinct — the spec's 生活圏 is these two points.
  const anchorAddresses = [];
  if (anchors?.home) anchorAddresses.push(anchors.home);
  if (anchors?.work && anchors.work !== anchors.home) anchorAddresses.push(anchors.work);
  const anchorPoints = [];
  for (const address of anchorAddresses) {
    const point = await geocodeAnchor(fetchImpl, apiKey, address);
    if (point) anchorPoints.push(point);
  }
  if (anchorPoints.length === 0) {
    return {
      definitions: [],
      shortfallReason: "no resolvable life-sphere anchor (home/work) — refusing to search outside the user's 生活圏",
    };
  }

  const definitions = [];
  const usedPlaceIds = new Set();

  // Usual provider for THIS category goes first, distance notwithstanding.
  const usual = (anchors.usualProviders || []).find((p) => p.careType === category);
  if (usual) {
    const match = (await textSearch(fetchImpl, apiKey, usual.location, null))[0];
    if (match?.place_id) {
      const website = await placeWebsite(fetchImpl, apiKey, match.place_id);
      if (website) {
        usedPlaceIds.add(match.place_id);
        definitions.push({
          providerId: match.place_id,
          publicName: match.name,
          officialUrl: website,
          proximityRank: 1,
          usualProvider: true,
        });
      }
    }
  }

  // Discovery: category keyword biased around each anchor, then a hard filter —
  // a result farther than radiusM from EVERY anchor is outside the 生活圏 and
  // rejected no matter how the API ranked it.
  const discovered = new Map();
  for (const point of anchorPoints) {
    const results = await textSearch(fetchImpl, apiKey, keyword, { ...point, radiusM });
    for (const result of results) {
      const location = result?.geometry?.location;
      if (!result?.place_id || discovered.has(result.place_id)) continue;
      if (!Number.isFinite(location?.lat) || !Number.isFinite(location?.lng)) continue;
      const minDistanceM = Math.min(...anchorPoints.map((anchor) => haversineM(anchor, location)));
      if (minDistanceM > radiusM) continue;
      discovered.set(result.place_id, { result, minDistanceM });
    }
  }
  const ranked = [...discovered.values()].sort((a, b) =>
    a.minDistanceM - b.minDistanceM || a.result.place_id.localeCompare(b.result.place_id));

  for (const { result } of ranked) {
    if (definitions.length >= MAX_CANDIDATES) break;
    if (usedPlaceIds.has(result.place_id)) continue;
    const website = await placeWebsite(fetchImpl, apiKey, result.place_id);
    if (!website) continue; // no official site → route judgment impossible → not a candidate
    usedPlaceIds.add(result.place_id);
    definitions.push({
      providerId: result.place_id,
      publicName: result.name,
      officialUrl: website,
      proximityRank: definitions.length + 1,
      usualProvider: false,
    });
  }

  const shortfallReason = definitions.length < MAX_CANDIDATES
    ? `only ${definitions.length} of ${MAX_CANDIDATES} ${category} candidates with an official website within ${radiusM}m of the user's anchors`
    : null;
  return { definitions, shortfallReason };
}

module.exports = { searchCareCandidates, CATEGORY_KEYWORDS };
