"use strict";

const {
  MobileError,
  legacyMobileRouteCacheKey,
  mobileRouteCacheKey,
  nowIso,
  safeTimeZone,
  sha256,
  tenantRouteCacheKey,
  randomOpaque,
} = require("./mobile-utils.js");

function requireScope(scope) {
  if (!scope || !scope.uid || typeof scope.uid !== "string") throw new MobileError("scope_required", "An authenticated mobile scope is required.", 401);
  return scope;
}

function encodeFilter(value) {
  return encodeURIComponent(String(value));
}

function asRow(body) {
  if (Array.isArray(body)) return body[0] || null;
  return body && typeof body === "object" ? body : null;
}

function asRows(body) {
  return Array.isArray(body) ? body : [];
}

function normalizeApnsResult(scope, input = {}) {
  requireScope(scope);
  const messageId = String(input.messageId || input.message_id || "").trim();
  if (!messageId) throw new MobileError("apns_result_invalid", "An APNs result needs a message id.", 400);
  const environmentValue = input.environment == null ? null : String(input.environment).trim().toLowerCase();
  if (environmentValue !== null && !["production", "development"].includes(environmentValue)) {
    throw new MobileError("apns_result_invalid", "An APNs result has an invalid environment.", 400);
  }
  const statusValue = input.status == null ? null : Number(input.status);
  if (statusValue !== null && !Number.isInteger(statusValue)) {
    throw new MobileError("apns_result_invalid", "An APNs result has an invalid status.", 400);
  }
  return {
    uid: scope.uid,
    deviceId: input.deviceId || input.device_id || null,
    apnsId: input.apnsId || input.apns_id || null,
    status: statusValue,
    reason: input.reason == null ? null : String(input.reason),
    environment: environmentValue,
    messageId,
  };
}

const MOBILE_PUSH_DEFAULT_LEASE_MS = 60_000;
const MOBILE_PUSH_DEFAULT_BACKOFF_MS = 30_000;
const MOBILE_PUSH_MAX_ATTEMPTS = 8;

function mobilePushNow(value) {
  if (typeof value === "function") return Number(value());
  if (value instanceof Date) return value.getTime();
  if (typeof value === "string") {
    const parsed = Date.parse(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  const number = Number(value);
  return Number.isFinite(number) ? number : Date.now();
}

function normalizeMobilePushJob(row) {
  if (!row || typeof row !== "object") return null;
  const nextAttempt = row.nextAttemptAt || row.next_attempt_at;
  const leaseExpires = row.leaseExpiresAt || row.lease_expires_at;
  return {
    ...row,
    uid: row.uid,
    messageId: row.messageId || row.message_id,
    status: row.status || "pending",
    attempts: Number(row.attempts || 0),
    nextAttemptAt: nextAttempt == null ? null : nextAttempt,
    leaseExpiresAt: leaseExpires == null ? null : leaseExpires,
    lastError: row.lastError || row.last_error || null,
    createdAt: row.createdAt || row.created_at,
    updatedAt: row.updatedAt || row.updated_at,
    completedAt: row.completedAt || row.completed_at || null,
  };
}

function mobilePushKey(uid, messageId) {
  return `${String(uid)}\u0000${String(messageId)}`;
}

function normalizeOAuthStateRow(row) {
  if (!row || typeof row !== "object") return row;
  return {
    ...row,
    stateHash: row.stateHash || row.state_hash,
    subjectHash: row.subjectHash || row.subject_hash,
    redirectUri: row.redirectUri || row.redirect_uri,
    expiresAt: row.expiresAt || row.expires_at,
    usedAt: row.usedAt || row.used_at,
    composioUserId: row.composioUserId || row.composio_user_id,
    connectedAccountId: row.connectedAccountId || row.connected_account_id,
    authConfigId: row.authConfigId || row.auth_config_id,
  };
}

function normalizeTravelRow(row) {
  if (!row || typeof row !== "object") return row;
  return {
    ...row,
    eventKey: row.eventKey || row.event_key,
    calendarId: row.calendarId || row.calendar_id,
    analysisKey: row.analysisKey || row.analysis_key,
    payloadHash: row.payloadHash || row.payload_hash,
    providerEventId: row.providerEventId || row.provider_event_id,
    composioUserId: row.composioUserId || row.composio_user_id,
    connectedAccountId: row.connectedAccountId || row.connected_account_id,
    providerEtag: row.providerEtag || row.provider_etag,
    claimToken: row.claimToken || row.claim_token,
    claimWorkerId: row.claimWorkerId || row.claim_worker_id,
    claimAcquiredAt: row.claimAcquiredAt || row.claim_acquired_at,
    leaseExpiresAt: row.leaseExpiresAt || row.lease_expires_at,
    createStartedAt: row.createStartedAt || row.create_started_at,
    providerObservedAt: row.providerObservedAt || row.provider_observed_at,
    confirmedAt: row.confirmedAt || row.confirmed_at,
    attemptCount: row.attemptCount == null ? row.attempt_count : row.attemptCount,
    lastErrorCode: row.lastErrorCode || row.last_error_code,
    updatedAt: row.updatedAt || row.updated_at,
  };
}

function normalizeTravelResult(value) {
  const root = asRow(value) || {};
  const row = normalizeTravelRow(asRow(root.row) || (root.status ? root : null));
  return { ...root, ...(row || {}), row: row || null };
}

function travelInputBody(input = {}) {
  const body = {
    p_uid: input.uid,
    p_event_key: input.eventKey || input.event_key,
    p_leg: input.leg,
    p_calendar_id: input.calendarId || input.calendar_id || "primary",
    p_analysis_key: input.analysisKey || input.analysis_key,
    p_payload_hash: input.payloadHash || input.payload_hash,
    p_marker: input.marker,
    p_provider_event_id: input.providerEventId || input.provider_event_id,
    p_composio_user_id: input.composioUserId || input.composio_user_id || input.calendarComposioUserId,
    p_connected_account_id: input.connectedAccountId || input.connected_account_id || input.gmailAccountId,
    p_claim_worker_id: input.claimWorkerId || input.claim_worker_id || "mobile",
    p_lease_seconds: input.leaseSeconds == null ? 120 : input.leaseSeconds,
  };
  if (input.now || input.nowIso) body.p_now = input.now || input.nowIso;
  return body;
}

function routeCacheEntry(row, now = Date.now) {
  const route = row && (row.route_result == null ? (row.route == null ? row.value : row.route) : row.route_result);
  if (!route || !row.computed_at) return null;
  const computedAt = Date.parse(row.computed_at);
  const ttlSecs = Number(row.ttl_secs);
  if (!Number.isFinite(computedAt) || !Number.isFinite(ttlSecs) || ttlSecs < 0 || now() - computedAt >= ttlSecs * 1000) return null;
  return { value: route, computedAt };
}

function routeCacheColumnMissing(error) {
  const status = error && error.details && Number(error.details.status);
  return status === 400 || status === 404;
}

function legacyRouteEndpoint(value) {
  if (typeof value === "string") return value.trim() || null;
  if (!value || typeof value !== "object") return null;
  const endpoint = value.displayName || value.display_name || value.address || value.name;
  return endpoint == null ? null : String(endpoint).trim() || null;
}

function routeCacheLegacyRow(scope, routeRequest, value, computedAt) {
  const origin = legacyRouteEndpoint(routeRequest && routeRequest.origin);
  const destination = legacyRouteEndpoint(routeRequest && routeRequest.destination);
  const anchor = routeRequest && (routeRequest.direction === "return" ? routeRequest.departAt : routeRequest.arriveBy);
  const anchorMs = Date.parse(String(anchor || ""));
  const timeBucket = Number.isFinite(anchorMs) ? Math.floor(anchorMs / 600000) : null;
  const duration = Number(value && (value.durationSeconds ?? value.duration_secs));
  const provider = value && value.provider != null ? String(value.provider).trim() : "";
  const computedMs = Date.parse(String(computedAt || ""));
  const ttlSecs = Number(value && (value.ttlSecs ?? value.ttl_secs ?? 600));
  if (!origin || !destination || !Number.isFinite(timeBucket) || !Number.isFinite(duration) || duration < 0 || !provider
    || !Number.isFinite(computedMs) || !Number.isFinite(ttlSecs) || ttlSecs <= 0) {
    throw new MobileError("route_cache_write_failed", "The route result is missing durable cache facts.", 503, true);
  }
  return {
    uid: scope.uid,
    from_geo: origin,
    to_geo: destination,
    time_bucket: timeBucket,
    provider,
    duration_secs: Math.floor(duration),
    geometry: value && value.geometry !== undefined ? value.geometry : null,
    route_result: value || null,
    computed_at: new Date(computedMs).toISOString(),
    ttl_secs: Math.floor(ttlSecs),
  };
}

function scopedMemoryRouteKey(uid, cacheKey) {
  return `${String(uid)}\u0000${cacheKey}`;
}

function createSupabaseMobileStore(options = {}) {
  const base = String(options.supaUrl || "").replace(/\/$/u, "");
  const key = String(options.supaKey || "");
  const fetchImpl = options.fetchImpl || fetch;
  if (!base || !key) throw new MobileError("store_config_invalid", "Supabase mobile storage is not configured.", 503, true);

  const headers = (extra = {}) => ({ apikey: key, Authorization: `Bearer ${key}`, ...extra });
  async function request(path, init = {}, code = "mobile_store_failed") {
    const response = await fetchImpl(`${base}${path}`, { ...init, headers: headers(init.headers || {}) });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (response.status === 409) return { conflict: true, status: response.status, body };
      throw new MobileError(code, "Mobile storage is temporarily unavailable.", 503, true, { status: response.status });
    }
    return { body, status: response.status };
  }
  async function rows(table, params = {}) {
    const query = new URLSearchParams(params);
    const result = await request(`/rest/v1/${table}?${query.toString()}`, { method: "GET" }, "mobile_store_read_failed");
    return asRows(result.body);
  }
  function scopedParams(scope, params = {}) {
    requireScope(scope);
    return { uid: `eq.${scope.uid}`, ...params };
  }
  async function rpc(name, body, code = "mobile_store_rpc_failed") {
    const result = await request(`/rest/v1/rpc/${name}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    }, code);
    return result.body;
  }

  return {
    async readUser(scope) {
      const rowsFound = await rows("lm_users", scopedParams(scope, {
        select: "uid,name,phone,paid,home_address,calendar_provider,gmail_account_id,calendar_composio_user_id,product_locale,calls_enabled,call_language,time_zone,calendar_status",
        limit: "1",
      }));
      return rowsFound[0] || null;
    },
    async patchUser(scope, patch) {
      requireScope(scope);
      const result = await request(`/rest/v1/lm_users?uid=eq.${encodeFilter(scope.uid)}`, {
        method: "PATCH",
        headers: { "content-type": "application/json", Prefer: "return=representation" },
        body: JSON.stringify({ ...patch, updated_at: new Date().toISOString() }),
      }, "mobile_profile_write_failed");
      return asRow(result.body) || patch;
    },
    async readAnalysisState(scope) {
      const found = await rows("lm_mobile_analysis_states", scopedParams(scope, { select: "status,analysis_id,updated_at", limit: "1" }));
      return found[0] || { status: "idle" };
    },
    async writeAnalysisState(scope, state) {
      requireScope(scope);
      const result = await request("/rest/v1/lm_mobile_analysis_states", {
        method: "POST",
        headers: { "content-type": "application/json", Prefer: "resolution=merge-duplicates,return=representation" },
        body: JSON.stringify({
          uid: scope.uid,
          status: state.status,
          analysis_id: state.analysisId || state.analysis_id || null,
          updated_at: state.updatedAt || new Date().toISOString(),
        }),
      }, "analysis_state_write_failed");
      return asRow(result.body) || state;
    },
    async claimTravelBlock(input = {}) {
      const value = await rpc("claim_lm_travel_block", travelInputBody(input), "travel_block_claim_failed");
      return normalizeTravelResult(value);
    },
    async markTravelCreateStarted(input = {}) {
      const body = {
        p_uid: input.uid, p_event_key: input.eventKey || input.event_key, p_leg: input.leg,
        p_claim_token: input.claimToken || input.claim_token,
      };
      if (input.now || input.nowIso) body.p_now = input.now || input.nowIso;
      const value = await rpc("mark_lm_travel_create_started", body, "travel_block_claim_failed");
      return normalizeTravelResult(value);
    },
    async confirmTravelBlock(input = {}) {
      const body = {
        p_uid: input.uid, p_event_key: input.eventKey || input.event_key, p_leg: input.leg,
        p_claim_token: input.claimToken || input.claim_token, p_provider_etag: input.providerEtag || input.provider_etag || null,
        p_provider_observed_at: input.providerObservedAt || input.provider_observed_at || undefined,
      };
      if (input.now || input.nowIso) body.p_now = input.now || input.nowIso;
      if (!body.p_provider_observed_at) delete body.p_provider_observed_at;
      const value = await rpc("confirm_lm_travel_block", body, "travel_block_confirm_failed");
      return normalizeTravelResult(value);
    },
    async releaseTravelClaim(input = {}) {
      const body = {
        p_uid: input.uid, p_event_key: input.eventKey || input.event_key, p_leg: input.leg,
        p_claim_token: input.claimToken || input.claim_token,
        p_error_code: input.errorCode || input.error_code || "provider_readback_failed",
      };
      if (input.now || input.nowIso) body.p_now = input.now || input.nowIso;
      const value = await rpc("release_lm_travel_claim", body, "travel_block_claim_failed");
      return normalizeTravelResult(value);
    },
    async blockTravelCollision(input = {}) {
      const body = {
        p_uid: input.uid, p_event_key: input.eventKey || input.event_key, p_leg: input.leg,
        p_claim_token: input.claimToken || input.claim_token,
        p_error_code: input.errorCode || input.error_code || "provider_collision",
      };
      if (input.now || input.nowIso) body.p_now = input.now || input.nowIso;
      const value = await rpc("block_lm_travel_collision", body, "travel_block_collision_failed");
      return normalizeTravelResult(value);
    },
    async readTravelBlock(input = {}) {
      const uid = String(input.uid || "");
      const eventKey = String(input.eventKey || input.event_key || "");
      const leg = String(input.leg || "");
      const found = await rows("lm_travel_log", {
        uid: `eq.${encodeFilter(uid)}`, event_key: `eq.${encodeFilter(eventKey)}`, leg: `eq.${encodeFilter(leg)}`,
        select: "*", limit: "1",
      });
      return normalizeTravelRow(found[0] || null);
    },
    async readRouteCache(scope, routeRequest) {
      const scoped = requireScope(scope);
      const cacheKey = mobileRouteCacheKey(scoped, routeRequest);
      const storageKeys = [tenantRouteCacheKey(scoped.uid, cacheKey), cacheKey, legacyMobileRouteCacheKey(scoped.uid, cacheKey)];
      for (const storageKey of storageKeys) {
        const params = scopedParams(scoped, {
          cache_key: `eq.${encodeFilter(storageKey)}`,
          select: "cache_key,legacy_cache_key,route_result,route,computed_at,ttl_secs",
          limit: "1",
        });
        let found;
        try {
          found = await rows("lm_route_cache", params);
        } catch (error) {
          // During the additive migration window, older deployments may not have
          // route_result or legacy_cache_key yet. Retry only the scoped legacy
          // projection; do not hide auth/network/storage failures behind a broad
          // fallback.
          if (!routeCacheColumnMissing(error)) throw error;
          found = await rows("lm_route_cache", scopedParams(scoped, {
            cache_key: `eq.${encodeFilter(storageKey)}`,
            select: "cache_key,route,computed_at,ttl_secs",
            limit: "1",
          }));
        }
        const hit = routeCacheEntry(found[0]);
        if (hit) return hit;
      }
      return null;
    },
    async writeRouteCache(scope, routeRequest, value) {
      const scoped = requireScope(scope);
      const cacheKey = mobileRouteCacheKey(scoped, routeRequest);
      const computedAt = value && value.computedAt ? value.computedAt : new Date().toISOString();
      const row = {
        ...routeCacheLegacyRow(scoped, routeRequest, value, computedAt),
        cache_key: tenantRouteCacheKey(scoped.uid, cacheKey),
      };
      const result = await request("/rest/v1/lm_route_cache?on_conflict=uid%2Ccache_key", {
        method: "POST",
        headers: { "content-type": "application/json", Prefer: "resolution=merge-duplicates,return=representation" },
        body: JSON.stringify(row),
      }, "route_cache_write_failed");
      if (result.conflict) {
        throw new MobileError("route_cache_write_failed", "The route cache could not be persisted.", 503, true, { status: result.status });
      }
      const persisted = routeCacheEntry(asRow(result.body));
      if (!persisted) {
        throw new MobileError("route_cache_write_failed", "The route cache returned no persisted route.", 503, true);
      }
      return persisted;
    },
    async createOAuthState(row) {
      const body = {
        state_hash: row.stateHash,
        uid: row.uid || null,
        subject_hash: row.subject ? require("node:crypto").createHash("sha256").update(String(row.subject)).digest("hex") : null,
        provider: row.provider,
        redirect_uri: row.redirectUri || null,
        composio_user_id: row.composioUserId || null,
        connected_account_id: row.connectedAccountId || null,
        auth_config_id: row.authConfigId || null,
        expires_at: row.expiresAt,
      };
      const result = await request("/rest/v1/lm_mobile_oauth_states", {
        method: "POST", headers: { "content-type": "application/json", Prefer: "return=minimal" }, body: JSON.stringify(body),
      }, "oauth_state_failed");
      if (result.conflict) throw new MobileError("oauth_state_failed", "Calendar connection is temporarily unavailable.", 503, true);
    },
    async updateOAuthState(stateHash, patch) {
      const result = await request(`/rest/v1/lm_mobile_oauth_states?state_hash=eq.${encodeFilter(stateHash)}`, {
        method: "PATCH", headers: { "content-type": "application/json", Prefer: "return=minimal" },
        body: JSON.stringify({
          connected_account_id: patch.connectedAccountId || null,
        }),
      }, "oauth_state_failed");
      if (result.conflict) throw new MobileError("oauth_state_failed", "Calendar connection is temporarily unavailable.", 503, true);
    },
    async claimOAuthState(stateHash, expected = {}) {
      const value = await rpc("claim_lm_mobile_oauth_state_v2", { p_state_hash: stateHash }, "oauth_state_failed");
      return normalizeOAuthStateRow(asRow(value)) || (value === true ? { stateHash } : null);
    },
    async linkCalendarIdentity(value) {
      const result = await rpc("link_lm_mobile_calendar_identity", {
        p_provider: value.provider || "google_calendar",
        p_provider_subject_hash: value.providerSubjectHash,
        p_uid: value.uid,
        p_composio_user_id: value.composioUserId,
        p_connected_account_id: value.connectedAccountId,
        p_auth_config_id: value.authConfigId,
        p_product_locale: value.productLocale || "en",
      }, "oauth_identity_failed");
      return asRow(result);
    },
    async createMobileSession(row) {
      const result = await request("/rest/v1/lm_mobile_sessions", {
        method: "POST", headers: { "content-type": "application/json", Prefer: "return=minimal" }, body: JSON.stringify({
          session_id: row.sessionId, family_id: row.familyId, uid: row.uid,
          access_token_hash: row.accessTokenHash, refresh_token_hash: row.refreshTokenHash,
          product_locale: row.productLocale, access_expires_at: row.accessExpiresAt,
          refresh_expires_at: row.refreshExpiresAt, provider_connection: row.providerConnection || null,
        }),
      }, "session_write_failed");
      if (result.conflict) throw new MobileError("session_write_failed", "The mobile session could not be created.", 503, true);
    },
    async findAccessSession(accessTokenHash) {
      const found = await rows("lm_mobile_sessions", {
        access_token_hash: `eq.${accessTokenHash}`,
        select: "session_id,family_id,uid,access_token_hash,product_locale,access_expires_at,refresh_expires_at,revoked_at,rotated_at",
        limit: "1",
      });
      return found[0] || null;
    },
    async findRefreshSession(refreshTokenHash) {
      const found = await rows("lm_mobile_sessions", {
        refresh_token_hash: `eq.${refreshTokenHash}`,
        select: "session_id,family_id,uid,refresh_token_hash,product_locale,access_expires_at,refresh_expires_at,revoked_at,rotated_at",
        limit: "1",
      });
      return found[0] || null;
    },
    async rotateRefreshSession(row, next) {
      const value = await rpc("rotate_lm_mobile_refresh", {
        p_session_id: row.session_id || row.sessionId,
        p_family_id: row.family_id || row.familyId,
        p_uid: row.uid,
        p_next_session_id: next.sessionId, p_next_access_token_hash: next.accessTokenHash,
        p_next_refresh_token_hash: next.refreshTokenHash, p_next_access_expires_at: next.accessExpiresAt,
        p_next_refresh_expires_at: next.refreshExpiresAt, p_product_locale: next.productLocale,
      }, "session_refresh_failed");
      if (value && (value.replay || value.revoked)) return value;
      return { session: next, ...(asRow(value) || {}) };
    },
    async revokeMobileSession(scope) {
      requireScope(scope);
      await request(`/rest/v1/lm_mobile_sessions?uid=eq.${encodeFilter(scope.uid)}&session_id=eq.${encodeFilter(scope.sessionId)}`, {
        method: "PATCH", headers: { "content-type": "application/json", Prefer: "return=minimal" }, body: JSON.stringify({ revoked_at: new Date().toISOString() }),
      }, "session_revoke_failed");
    },
    async revokeAllSessions(scope) {
      requireScope(scope);
      await request(`/rest/v1/lm_mobile_sessions?uid=eq.${encodeFilter(scope.uid)}`, {
        method: "PATCH", headers: { "content-type": "application/json", Prefer: "return=minimal" }, body: JSON.stringify({ revoked_at: new Date().toISOString() }),
      }, "session_revoke_failed");
    },
    async readIdempotency(scope, key) {
      const found = await rows("lm_mobile_idempotency", scopedParams(scope, {
        idempotency_key: `eq.${encodeFilter(key)}`, select: "request_hash,status,result,result_expires_at,error,status_code", limit: "1",
      }));
      return found[0] || null;
    },
    async claimIdempotency(scope, key, value) {
      requireScope(scope);
      const result = await request("/rest/v1/lm_mobile_idempotency", {
        method: "POST", headers: { "content-type": "application/json", Prefer: "return=minimal" }, body: JSON.stringify({
          uid: scope.uid, idempotency_key: key, request_hash: value.requestHash, status: "pending",
        }),
      }, "idempotency_failed");
      return !result.conflict;
    },
    async completeIdempotency(scope, key, value) {
      requireScope(scope);
      await request(`/rest/v1/lm_mobile_idempotency?uid=eq.${encodeFilter(scope.uid)}&idempotency_key=eq.${encodeFilter(key)}`, {
        method: "PATCH", headers: { "content-type": "application/json", Prefer: "return=minimal" }, body: JSON.stringify({
          status: value.status, result: value.result === undefined ? null : value.result,
          result_expires_at: value.resultExpiresAt || value.result_expires_at || null,
          error: value.error || null, status_code: value.statusCode || null, updated_at: new Date().toISOString(),
        }),
      }, "idempotency_failed");
    },
    async reopenIdempotency(scope, key, value) {
      requireScope(scope);
      const result = await request(`/rest/v1/lm_mobile_idempotency?uid=eq.${encodeFilter(scope.uid)}&idempotency_key=eq.${encodeFilter(key)}&status=eq.failed&request_hash=eq.${encodeFilter(value.requestHash)}`, {
        method: "PATCH", headers: { "content-type": "application/json", Prefer: "return=representation" }, body: JSON.stringify({ status: "pending", result: null, result_expires_at: null, error: null, status_code: null, updated_at: new Date().toISOString() }),
      }, "idempotency_failed");
      return Boolean(asRow(result.body));
    },
    async appendOutbox(scope, row) {
      requireScope(scope);
      const body = {
        p_uid: scope.uid, p_id: row.id, p_key: row.key, p_type: row.type || null,
        p_args: row.args || {}, p_user_content: row.userContent || null, p_question: row.question || null,
        p_route: row.route || null, p_created_at: row.createdAt || new Date().toISOString(),
        p_mutation_key: row.mutationKey || null,
      };
      // The RPC inserts the semantic row and its dispatch job in one database
      // transaction. A deployment that has not applied the durable-delivery
      // migration is rejected instead of silently falling back to a split write.
      const value = await rpc("append_lm_mobile_outbox_with_push_job", body, "outbox_write_failed");
      const stored = asRow(value && value.row) || asRow(value) || row;
      return { ...stored, __inserted: value && value.inserted === false ? false : true };
    },
    async listOutbox(scope, afterSequence = 0, limit = 50) {
      const found = await rows("lm_mobile_outbox", scopedParams(scope, {
        sequence: `gt.${Math.max(0, Number(afterSequence) || 0)}`, order: "sequence.asc", limit: String(Math.min(100, Math.max(1, limit))),
      }));
      return found;
    },
    async readOutbox(scope, messageId) {
      const found = await rows("lm_mobile_outbox", scopedParams(scope, {
        id: `eq.${encodeFilter(messageId)}`, limit: "1",
      }));
      return found[0] || null;
    },
    async readMobilePushJob(scope, messageId) {
      const found = await rows("lm_mobile_push_jobs", scopedParams(scope, {
        message_id: `eq.${encodeFilter(messageId)}`, limit: "1",
      }));
      return normalizeMobilePushJob(found[0] || null);
    },
    async listMobilePushJobs(scope, options2 = {}) {
      const params = scope && scope.uid ? scopedParams(scope, {}) : {};
      const statuses = Array.isArray(options2.statuses) && options2.statuses.length
        ? options2.statuses.map((value) => String(value)).join(",") : "pending,processing";
      params.status = `in.(${statuses})`;
      if (options2.now !== undefined) params.next_attempt_at = `lte.${encodeFilter(new Date(mobilePushNow(options2.now)).toISOString())}`;
      params.order = "next_attempt_at.asc,created_at.asc";
      params.limit = String(Math.min(100, Math.max(1, Number(options2.limit || 20))));
      const found = await rows("lm_mobile_push_jobs", params);
      return found.map(normalizeMobilePushJob).filter(Boolean);
    },
    async claimMobilePushJob(scope, messageId, options2 = {}) {
      const value = await rpc("claim_lm_mobile_push_job", {
        p_uid: requireScope(scope).uid, p_message_id: messageId,
        p_now: new Date(mobilePushNow(options2.now)).toISOString(),
        p_lease_seconds: Math.max(1, Math.floor(Number(options2.leaseMs || MOBILE_PUSH_DEFAULT_LEASE_MS) / 1000)),
      }, "push_job_claim_failed");
      return normalizeMobilePushJob(asRow(value));
    },
    async markMobilePushJobSuccess(scope, messageId, result) {
      const value = await rpc("complete_lm_mobile_push_job", {
        p_uid: requireScope(scope).uid, p_message_id: messageId, p_result: result || {},
      }, "push_job_complete_failed");
      return normalizeMobilePushJob(asRow(value));
    },
    async markMobilePushJobFailure(scope, messageId, error, options2 = {}) {
      const now = mobilePushNow(options2.now);
      const attempts = Number(options2.attempts || 1);
      const backoffMs = Number(options2.backoffMs || MOBILE_PUSH_DEFAULT_BACKOFF_MS) * (2 ** Math.max(0, attempts - 1));
      const value = await rpc("retry_lm_mobile_push_job", {
        p_uid: requireScope(scope).uid, p_message_id: messageId,
        p_error: String(error && (error.code || error.reason || error.message) || "apns_push_failed"),
        p_next_attempt_at: new Date(now + backoffMs).toISOString(), p_max_attempts: MOBILE_PUSH_MAX_ATTEMPTS,
      }, "push_job_retry_failed");
      return normalizeMobilePushJob(asRow(value));
    },
    async createQuestion(scope, question) {
      requireScope(scope);
      const result = await request("/rest/v1/lm_mobile_questions", {
        method: "POST", headers: { "content-type": "application/json", Prefer: "return=representation" }, body: JSON.stringify({
          uid: scope.uid,
          id: question.id,
          type: question.type,
          prompt: question.prompt || null,
          event_id: question.eventId || question.event_id || null,
          status: question.status || "open",
        }),
      }, "question_write_failed");
      if (result.conflict) {
        const found = await rows("lm_mobile_questions", scopedParams(scope, { id: `eq.${encodeFilter(question.id)}`, limit: "1" }));
        return found[0] || question;
      }
      return asRow(result.body) || question;
    },
    async consumeOpenQuestion(scope, questionId, answer) {
      const value = await rpc("consume_lm_mobile_question", { p_uid: requireScope(scope).uid, p_question_id: questionId, p_answer: answer }, "question_reply_failed");
      return asRow(value) || (value === true ? { id: questionId, answer } : null);
    },
    async claimOpenQuestion(scope, questionId, answer) {
      const value = await rpc("claim_lm_mobile_question", { p_uid: requireScope(scope).uid, p_question_id: questionId, p_answer: answer }, "question_reply_failed");
      return asRow(value) || null;
    },
    async completeQuestionReply(scope, questionId, answer) {
      const value = await rpc("complete_lm_mobile_question", { p_uid: requireScope(scope).uid, p_question_id: questionId, p_answer: answer }, "question_reply_failed");
      return asRow(value) || null;
    },
    async claimCallAttempt(scope, value) {
      const result = await rpc("claim_lm_mobile_call", { p_uid: requireScope(scope).uid, p_idempotency_key: value.idempotencyKey, p_now: value.now || new Date().toISOString() }, "call_limit_failed");
      return asRow(result) || result || null;
    },
    async finishCallAttempt(scope, value) {
      requireScope(scope);
      await request(`/rest/v1/lm_mobile_call_attempts?uid=eq.${encodeFilter(scope.uid)}&attempt_id=eq.${encodeFilter(value.attemptId)}`, {
        method: "PATCH", headers: { "content-type": "application/json", Prefer: "return=minimal" }, body: JSON.stringify({ status: value.status, provider_receipt: value.providerReceipt || null, error: value.error || null }),
      }, "call_write_failed");
    },
    async upsertDevice(scope, value) {
      const result = await rpc("claim_lm_mobile_device", {
        p_uid: requireScope(scope).uid, p_token: value.token, p_environment: value.environment,
        p_locale: value.locale, p_timezone: value.timezone, p_last_seen_at: value.last_seen_at || new Date().toISOString(),
      }, "device_write_failed");
      return asRow(result) || value;
    },
    async deleteDevice(scope, token) {
      requireScope(scope);
      await request(`/rest/v1/lm_mobile_devices?uid=eq.${encodeFilter(scope.uid)}&token=eq.${encodeFilter(token)}`, { method: "DELETE", headers: { Prefer: "return=minimal" } }, "device_delete_failed");
      return { deleted: true };
    },
    async listDevices(scope) {
      const scoped = requireScope(scope);
      const found = await rows("lm_mobile_devices", scopedParams(scoped, {
        select: "token,environment,locale,timezone,last_seen_at,created_at,updated_at",
        order: "updated_at.desc",
      }));
      return found.map((row) => ({
        ...row,
        deviceId: row.deviceId || row.device_id || `device:v1:${scoped.uid}:${String(row.token || "").slice(-8)}`,
        token: row.token,
        environment: row.environment,
        locale: row.locale,
        timezone: row.timezone,
      }));
    },
    async removeDevice(scope, token) {
      requireScope(scope);
      await request(`/rest/v1/lm_mobile_devices?uid=eq.${encodeFilter(scope.uid)}&token=eq.${encodeFilter(token)}`, { method: "DELETE", headers: { Prefer: "return=minimal" } }, "device_delete_failed");
      return { deleted: true };
    },
    async recordApnsResult(scope, input) {
      const result = normalizeApnsResult(scope, input);
      await request("/rest/v1/lm_mobile_apns_results", {
        method: "POST",
        headers: { "content-type": "application/json", Prefer: "return=representation" },
        body: JSON.stringify({
          uid: result.uid,
          message_id: result.messageId,
          device_id: result.deviceId,
          apns_id: result.apnsId,
          status: result.status,
          reason: result.reason,
          environment: result.environment,
        }),
      }, "apns_result_write_failed");
      return { ...result };
    },
    async writeDeletionReceipt(scope, receipt) {
      const result = await request("/rest/v1/lm_mobile_deletion_receipts", {
        method: "POST", headers: { "content-type": "application/json", Prefer: "resolution=merge-duplicates,return=representation" }, body: JSON.stringify({
          uid: requireScope(scope).uid,
          operation_id: receipt.operationId || receipt.operation_id,
          status: receipt.status,
          completed_at: receipt.completedAt || receipt.completed_at || null,
          capability_hash: receipt.capabilityHash || receipt.capability_hash || null,
          provider_cleanup: receipt.providerCleanup || receipt.provider_cleanup || [],
        }),
      }, "deletion_receipt_failed");
      return asRow(result.body) || receipt;
    },
    async readDeletionReceipt(scope, operationId) {
      const found = await rows("lm_mobile_deletion_receipts", scopedParams(scope, {
        operation_id: `eq.${encodeFilter(operationId)}`,
        select: "operation_id,status,completed_at,provider_cleanup,capability_hash",
        limit: "1",
      }));
      return found[0] || null;
    },
    async readDeletionReceiptByCapability(capability, operationId) {
      const found = await rows("lm_mobile_deletion_receipts", {
        capability_hash: `eq.${encodeFilter(sha256(capability))}`,
        operation_id: `eq.${encodeFilter(operationId)}`,
        select: "operation_id,status,completed_at,provider_cleanup,capability_hash",
        limit: "1",
      });
      return found[0] || null;
    },
    async finalizeAccountDeletion(scope, options2 = {}) {
      const value = await rpc("finalize_lm_mobile_deletion", {
        p_uid: requireScope(scope).uid,
        p_operation_id: options2.operationId,
        p_capability_hash: options2.capabilityHash,
        p_provider_cleanup: options2.providerCleanup || [],
        p_preserve_idempotency_key: options2.preserveIdempotencyKey || null,
      }, "account_delete_failed");
      return asRow(value) || value;
    },
    async deleteAccount(scope, options2 = {}) {
      return rpc("delete_lm_mobile_account", {
        p_uid: requireScope(scope).uid,
        p_preserve_idempotency_key: options2.preserveIdempotencyKey || null,
      }, "account_delete_failed");
    },
  };
}

function createMemoryMobileStore(options = {}) {
  const users = new Map((options.users || []).map((row) => [String(row.uid), { ...row }]));
  const sessions = new Map();
  const states = new Map();
  const idempotency = new Map();
  const outbox = new Map();
  const questions = new Map();
  const devices = new Map();
  const calls = new Map();
  const deletionReceipts = new Map();
  const apnsResults = [];
  const mobilePushJobs = new Map();
  const calendarConnections = new Map();
  const travelBlocks = new Map();
  const routeCache = options.routeCacheStore || new Map();
  const callDayGuards = new Map();
  const callDailyUserLimit = Number.isSafeInteger(options.callDailyUserLimit) && options.callDailyUserLimit > 0 ? options.callDailyUserLimit : 5;
  const callDailyGlobalLimit = Number.isSafeInteger(options.callDailyGlobalLimit) && options.callDailyGlobalLimit > 0 ? options.callDailyGlobalLimit : 100;
  const callCooldownMs = Number.isSafeInteger(options.callCooldownMs) && options.callCooldownMs >= 0 ? options.callCooldownMs : 10 * 60 * 1000;
  const callAttemptIdFactory = typeof options.callAttemptIdFactory === "function" ? options.callAttemptIdFactory : null;
  const deviceIdFactory = typeof options.deviceIdFactory === "function" ? options.deviceIdFactory : null;
  const memoryNow = typeof options.now === "function" ? options.now : Date.now;
  const travelRows = Array.isArray(options.travelBlocks || options.travelRows) ? (options.travelBlocks || options.travelRows) : [];
  for (const source of travelRows) {
    if (!source || source.uid == null || source.event_key == null || source.leg == null) continue;
    const row = normalizeTravelRow({
      ...source,
      status: source.status || "legacy_terminal",
      calendar_id: source.calendar_id || "primary",
      attempt_count: source.attempt_count || 0,
      updated_at: source.updated_at || new Date(memoryNow()).toISOString(),
    });
    travelBlocks.set(`${row.uid}\u0000${row.eventKey}\u0000${row.leg}`, row);
  }
  let sequence = 0;
  function scoped(scope, expectedUid) {
    requireScope(scope);
    if (expectedUid && expectedUid !== scope.uid) throw new MobileError("scope_mismatch", "The authenticated scope does not match the requested account.", 403);
    return scope.uid;
  }
  function user(scope, expectedUid) {
    const uid = scoped(scope, expectedUid);
    return users.get(uid) || null;
  }
  return {
    _users: users, _sessions: sessions, _states: states, _idempotency: idempotency, _outbox: outbox, _mobilePushJobs: mobilePushJobs, _questions: questions, _devices: devices, _calls: calls, _callDayGuards: callDayGuards, _deletionReceipts: deletionReceipts, _apnsResults: apnsResults, _routeCache: routeCache, _calendarConnections: calendarConnections, _travelBlocks: travelBlocks,
    async readUser(scope) { const row = user(scope); return row ? { ...row } : null; },
    async patchUser(scope, patch, options2 = {}) { const row = user(scope, options2.expectedUid); if (!row) throw new MobileError("account_not_found", "Account not found.", 404); Object.assign(row, patch); return { ...row }; },
    async readAnalysisState(scope) { const row = user(scope); return row && row.analysisState ? { ...row.analysisState } : { status: "idle" }; },
    async writeAnalysisState(scope, state) { const row = user(scope); if (!row) throw new MobileError("account_not_found", "Account not found.", 404); row.analysisState = { ...state, updatedAt: state.updatedAt || nowIso() }; return { ...row.analysisState }; },
    async claimTravelBlock(input = {}) {
      const now = input.now ? Date.parse(input.now) : memoryNow();
      const nowDate = Number.isFinite(now) ? new Date(now).toISOString() : new Date(memoryNow()).toISOString();
      const eventKey = String(input.eventKey || input.event_key || "");
      const uid = String(input.uid || "");
      const leg = String(input.leg || "");
      const key = `${uid}\u0000${eventKey}\u0000${leg}`;
      const payloadHash = input.payloadHash || input.payload_hash;
      const calendarId = input.calendarId || input.calendar_id || "primary";
      const providerEventId = input.providerEventId || input.provider_event_id;
      const marker = input.marker;
      const composioUserId = input.composioUserId || input.composio_user_id || input.calendarComposioUserId;
      const connectedAccountId = input.connectedAccountId || input.connected_account_id || input.gmailAccountId;
      if (!composioUserId || !connectedAccountId) return { decision: "provider_binding_invalid", row: null };
      const tenant = users.get(uid);
      if (tenant) {
        const durableOwner = tenant.calendar_composio_user_id || tenant.calendarComposioUserId;
        const durableAccount = tenant.gmail_account_id || tenant.gmailAccountId;
        if (durableOwner !== composioUserId || durableAccount !== connectedAccountId) return { decision: "provider_binding_invalid", row: null };
      }
      const requestedLeaseSeconds = input.leaseSeconds == null
        ? (input.leaseMs == null ? 120 : Number(input.leaseMs) / 1000)
        : Number(input.leaseSeconds);
      const leaseMs = Math.max(1, Math.min(3600, requestedLeaseSeconds)) * 1000;
      let row = travelBlocks.get(key);
      if (!row) {
        row = normalizeTravelRow({
          uid, event_key: eventKey, leg, status: "claimed", calendar_id: calendarId,
          analysis_key: input.analysisKey || input.analysis_key, payload_hash: payloadHash,
          marker, provider_event_id: providerEventId,
          composio_user_id: composioUserId, connected_account_id: connectedAccountId,
          claim_token: randomOpaque("travel_claim:", {}, 18),
          claim_worker_id: input.claimWorkerId || input.claim_worker_id || "mobile",
          claim_acquired_at: nowDate, lease_expires_at: new Date(now + leaseMs).toISOString(),
          attempt_count: 0, updated_at: nowDate,
        });
        travelBlocks.set(key, row);
        return { decision: "claimed", row, ...row };
      }
      if (row.status === "legacy_terminal") return { decision: "legacy_terminal", row, ...row };
      if (row.composioUserId !== composioUserId || row.connectedAccountId !== connectedAccountId) {
        return { decision: "provider_binding_invalid", row, ...row };
      }
      if (row.calendarId !== calendarId || row.payloadHash !== payloadHash || row.marker !== marker || row.providerEventId !== providerEventId) {
        return { decision: "analysis_conflict", row, ...row };
      }
      const lease = Date.parse(row.leaseExpiresAt || "");
      if ((row.status === "claimed" || row.status === "creating") && Number.isFinite(lease) && lease > now) {
        return { decision: "busy", row, ...row };
      }
      if (row.status === "claimed" || row.status === "creating") {
        row = normalizeTravelRow({ ...row, status: "claimed", claimToken: randomOpaque("travel_claim:", {}, 18), claimWorkerId: input.claimWorkerId || input.claim_worker_id || "mobile", claimAcquiredAt: nowDate, leaseExpiresAt: new Date(now + leaseMs).toISOString(), lastErrorCode: null, updatedAt: nowDate });
        travelBlocks.set(key, row);
        return { decision: "claimed", row, ...row };
      }
      return { decision: "reused", row, ...row };
    },
    async markTravelCreateStarted(input = {}) {
      const key = `${String(input.uid || "")}\u0000${String(input.eventKey || input.event_key || "")}\u0000${String(input.leg || "")}`;
      const row = travelBlocks.get(key);
      const now = input.now ? Date.parse(input.now) : memoryNow();
      const lease = row && Date.parse(row.leaseExpiresAt || "");
      if (!row || row.status !== "claimed" || row.claimToken !== (input.claimToken || input.claim_token) || !Number.isFinite(lease) || lease <= now) return { started: false, reason: "stale_token", row: row || null };
      const next = normalizeTravelRow({ ...row, status: "creating", createStartedAt: row.createStartedAt || new Date(now).toISOString(), attemptCount: Number(row.attemptCount || 0) + 1, updatedAt: new Date(now).toISOString() });
      travelBlocks.set(key, next);
      return { started: true, row: next, ...next };
    },
    async confirmTravelBlock(input = {}) {
      const key = `${String(input.uid || "")}\u0000${String(input.eventKey || input.event_key || "")}\u0000${String(input.leg || "")}`;
      const row = travelBlocks.get(key);
      const now = input.now ? Date.parse(input.now) : memoryNow();
      if (!row || row.claimToken !== (input.claimToken || input.claim_token) || !["claimed", "creating"].includes(row.status)) return { confirmed: false, reason: "stale_token", row: row || null };
      const next = normalizeTravelRow({ ...row, status: "confirmed", providerEtag: input.providerEtag || input.provider_etag || null, providerObservedAt: input.providerObservedAt || input.provider_observed_at || new Date(now).toISOString(), confirmedAt: row.confirmedAt || new Date(now).toISOString(), leaseExpiresAt: null, lastErrorCode: null, updatedAt: new Date(now).toISOString() });
      travelBlocks.set(key, next);
      return { confirmed: true, row: next, ...next };
    },
    async releaseTravelClaim(input = {}) {
      const key = `${String(input.uid || "")}\u0000${String(input.eventKey || input.event_key || "")}\u0000${String(input.leg || "")}`;
      const row = travelBlocks.get(key);
      const now = input.now ? Date.parse(input.now) : memoryNow();
      if (!row || row.claimToken !== (input.claimToken || input.claim_token) || !["claimed", "creating"].includes(row.status)) return { released: false, reason: "stale_token", row: row || null };
      const next = normalizeTravelRow({ ...row, leaseExpiresAt: new Date(now).toISOString(), lastErrorCode: input.errorCode || input.error_code || "provider_readback_failed", updatedAt: new Date(now).toISOString() });
      travelBlocks.set(key, next);
      return { released: true, row: next, ...next };
    },
    async blockTravelCollision(input = {}) {
      const key = `${String(input.uid || "")}\u0000${String(input.eventKey || input.event_key || "")}\u0000${String(input.leg || "")}`;
      const row = travelBlocks.get(key);
      const now = input.now ? Date.parse(input.now) : memoryNow();
      if (!row || row.claimToken !== (input.claimToken || input.claim_token) || !["claimed", "creating"].includes(row.status)) return { blocked: false, reason: "stale_token", row: row || null };
      const next = normalizeTravelRow({ ...row, status: "blocked_collision", leaseExpiresAt: null, lastErrorCode: input.errorCode || input.error_code || "provider_collision", updatedAt: new Date(now).toISOString() });
      travelBlocks.set(key, next);
      return { blocked: true, row: next, ...next };
    },
    async readTravelBlock(input = {}) {
      const key = `${String(input.uid || "")}\u0000${String(input.eventKey || input.event_key || "")}\u0000${String(input.leg || "")}`;
      const row = travelBlocks.get(key);
      return row ? normalizeTravelRow(row) : null;
    },
    async readRouteCache(scope, routeRequest) {
      const uid = scoped(scope);
      const key = scopedMemoryRouteKey(uid, mobileRouteCacheKey({ uid }, routeRequest));
      return routeCacheEntry(routeCache.get(key), memoryNow);
    },
    async writeRouteCache(scope, routeRequest, value) {
      const uid = scoped(scope);
      const key = scopedMemoryRouteKey(uid, mobileRouteCacheKey({ uid }, routeRequest));
      const computedAt = value && value.computedAt ? value.computedAt : new Date(memoryNow()).toISOString();
      routeCache.set(key, { route_result: value, computed_at: computedAt, ttl_secs: 600 });
      return { value, computedAt: Date.parse(computedAt) };
    },
    async createOAuthState(row) { states.set(row.stateHash, { ...row, composioUserId: row.composioUserId || null, connectedAccountId: row.connectedAccountId || null, authConfigId: row.authConfigId || null }); },
    async updateOAuthState(stateHash, patch) {
      const row = states.get(stateHash);
      if (!row) throw new MobileError("oauth_state_failed", "Calendar connection is temporarily unavailable.", 503, true);
      row.connectedAccountId = patch.connectedAccountId || null;
    },
    async claimOAuthState(hash, expected = {}) {
      const row = states.get(hash);
      if (!row || row.usedAt || (row.expiresAt && Date.parse(row.expiresAt) <= memoryNow())) return null;
      if (expected.uid !== undefined && row.uid && row.uid !== expected.uid) return null;
      if (expected.subject !== undefined && row.subject && expected.subject && row.subject !== expected.subject) return null;
      row.usedAt = nowIso();
      return { ...row };
    },
    async linkCalendarIdentity(value) {
      const key = `${String(value.provider || "google_calendar")}:${String(value.providerSubjectHash || "")}`;
      if (!value.providerSubjectHash || String(value.providerSubjectHash).length !== 64) throw new MobileError("oauth_identity_failed", "The Calendar identity could not be linked.", 503, true);
      const existing = calendarConnections.get(key);
      if (existing) {
        existing.composioUserId = value.composioUserId;
        existing.connectedAccountId = value.connectedAccountId;
        existing.authConfigId = value.authConfigId;
        existing.updatedAt = nowIso();
        const row = users.get(existing.uid);
        if (row) Object.assign(row, { calendar_status: "connected", calendar_provider: "composio_gcal", gmail_account_id: value.connectedAccountId, calendar_composio_user_id: value.composioUserId });
        return { uid: existing.uid, productLocale: row && row.product_locale || "en" };
      }
      const uid = String(value.uid || "");
      if (!/^lm_[A-Za-z0-9_-]+$/u.test(uid)) throw new MobileError("oauth_identity_failed", "The Calendar identity could not be linked.", 503, true);
      if (![...calendarConnections.values()].every((row) => row.uid !== uid)) throw new MobileError("oauth_identity_failed", "The Calendar identity could not be linked.", 503, true);
      const userRow = users.get(uid) || { uid, product_locale: value.productLocale || "en", calls_enabled: false };
      Object.assign(userRow, { calendar_status: "connected", calendar_provider: "composio_gcal", gmail_account_id: value.connectedAccountId, calendar_composio_user_id: value.composioUserId });
      users.set(uid, userRow);
      calendarConnections.set(key, {
        provider: value.provider || "google_calendar", providerSubjectHash: value.providerSubjectHash, uid,
        composioUserId: value.composioUserId, connectedAccountId: value.connectedAccountId, authConfigId: value.authConfigId,
        createdAt: nowIso(), updatedAt: nowIso(),
      });
      return { uid, productLocale: userRow.product_locale || "en" };
    },
    async createMobileSession(row) { sessions.set(row.sessionId, { ...row }); },
    async findAccessSession(hash) { return [...sessions.values()].find((row) => row.accessTokenHash === hash) || null; },
    async findRefreshSession(hash) { return [...sessions.values()].find((row) => row.refreshTokenHash === hash) || null; },
    async rotateRefreshSession(row, next) { if (row.rotatedAt || row.revokedAt) { for (const item of sessions.values()) if (item.familyId === row.familyId) item.revokedAt = nowIso(); return { replay: true }; } row.rotatedAt = nowIso(); sessions.set(next.sessionId, { ...next }); return { session: next }; },
    async revokeMobileSession(scope) { const row = sessions.get(scope.sessionId); if (row && row.uid === scoped(scope)) row.revokedAt = nowIso(); },
    async revokeAllSessions(scope) { const uid = scoped(scope); for (const row of sessions.values()) if (row.uid === uid) row.revokedAt = nowIso(); },
    async readIdempotency(scope, key) { return idempotency.get(`${scoped(scope)}:${key}`) || null; },
    async claimIdempotency(scope, key, value) { const id = `${scoped(scope)}:${key}`; if (idempotency.has(id)) return false; idempotency.set(id, { ...value }); return true; },
    async completeIdempotency(scope, key, value) { const id = `${scoped(scope)}:${key}`; idempotency.set(id, { ...idempotency.get(id), ...value }); },
    async reopenIdempotency(scope, key, value) {
      const id = `${scoped(scope)}:${key}`;
      const row = idempotency.get(id);
      if (!row || row.status !== "failed" || row.requestHash !== value.requestHash) return false;
      row.status = "pending"; row.result = null; row.error = null; row.statusCode = null;
      return true;
    },
    async appendOutbox(scope, row) {
      const uid = scoped(scope);
      const existing = (outbox.get(uid) || []).find((item) => item.id === row.id);
      if (existing) return { ...existing, __inserted: false };
      const item = { ...row, uid, sequence: ++sequence, createdAt: row.createdAt || nowIso() };
      if (!outbox.has(uid)) outbox.set(uid, []);
      outbox.get(uid).push(item);
      // In-memory storage mirrors the production transaction: the semantic
      // row and its pending dispatch job become visible together.
      mobilePushJobs.set(mobilePushKey(uid, item.id), {
        uid, messageId: item.id, status: "pending", attempts: 0,
        nextAttemptAt: memoryNow(), leaseExpiresAt: null, lastError: null,
        createdAt: item.createdAt, updatedAt: item.createdAt, completedAt: null,
      });
      return { ...item, __inserted: true };
    },
    async listOutbox(scope, after = 0, limit = 50) { return (outbox.get(scoped(scope)) || []).filter((row) => row.sequence > after).slice(0, limit).map((row) => ({ ...row })); },
    async readOutbox(scope, messageId) {
      const row = (outbox.get(scoped(scope)) || []).find((item) => item.id === messageId);
      return row ? { ...row } : null;
    },
    async readMobilePushJob(scope, messageId) {
      const row = mobilePushJobs.get(mobilePushKey(scoped(scope), messageId));
      return row ? { ...row } : null;
    },
    async listMobilePushJobs(scope, options2 = {}) {
      const uid = scope && scope.uid ? scoped(scope) : null;
      const now = mobilePushNow(options2.now === undefined ? memoryNow() : options2.now);
      const statuses = Array.isArray(options2.statuses) && options2.statuses.length ? new Set(options2.statuses) : new Set(["pending", "processing"]);
      return [...mobilePushJobs.values()]
        .filter((row) => (!uid || row.uid === uid) && statuses.has(row.status))
        .filter((row) => row.status === "pending" ? mobilePushNow(row.nextAttemptAt) <= now : (!row.leaseExpiresAt || mobilePushNow(row.leaseExpiresAt) <= now))
        .sort((a, b) => mobilePushNow(a.nextAttemptAt) - mobilePushNow(b.nextAttemptAt))
        .slice(0, Math.min(100, Math.max(1, Number(options2.limit || 20))))
        .map((row) => ({ ...row }));
    },
    async claimMobilePushJob(scope, messageId, options2 = {}) {
      const row = mobilePushJobs.get(mobilePushKey(scoped(scope), messageId));
      if (!row || row.status === "completed" || row.status === "failed") return null;
      const now = mobilePushNow(options2.now === undefined ? memoryNow() : options2.now);
      if (row.status === "pending" && mobilePushNow(row.nextAttemptAt) > now) return null;
      if (row.status === "processing" && row.leaseExpiresAt && mobilePushNow(row.leaseExpiresAt) > now) return null;
      row.status = "processing";
      row.attempts += 1;
      row.leaseExpiresAt = now + Math.max(1, Number(options2.leaseMs || MOBILE_PUSH_DEFAULT_LEASE_MS));
      row.updatedAt = new Date(now).toISOString();
      return { ...row };
    },
    async markMobilePushJobSuccess(scope, messageId, result = {}) {
      const row = mobilePushJobs.get(mobilePushKey(scoped(scope), messageId));
      if (!row) return null;
      row.status = "completed";
      row.result = result;
      row.completedAt = new Date(memoryNow()).toISOString();
      row.leaseExpiresAt = null;
      row.updatedAt = row.completedAt;
      return { ...row };
    },
    async markMobilePushJobFailure(scope, messageId, error, options2 = {}) {
      const row = mobilePushJobs.get(mobilePushKey(scoped(scope), messageId));
      if (!row) return null;
      const now = mobilePushNow(options2.now === undefined ? memoryNow() : options2.now);
      const attempts = Math.max(1, Number(row.attempts || options2.attempts || 1));
      const base = Math.max(1, Number(options2.backoffMs || MOBILE_PUSH_DEFAULT_BACKOFF_MS));
      row.status = attempts >= MOBILE_PUSH_MAX_ATTEMPTS ? "failed" : "pending";
      row.lastError = String(error && (error.code || error.reason || error.message) || "apns_push_failed");
      row.nextAttemptAt = now + base * (2 ** Math.max(0, attempts - 1));
      row.leaseExpiresAt = null;
      row.updatedAt = new Date(now).toISOString();
      return { ...row };
    },
    async createQuestion(scope, question) {
      const uid = scoped(scope);
      const key = `${uid}:${question.id}`;
      const existing = questions.get(key);
      if (existing) return { ...existing };
      const row = { ...question, uid, status: question.status || "open" };
      questions.set(key, row);
      return { ...row };
    },
    async claimOpenQuestion(scope, id, answer) {
      const uid = scoped(scope);
      const row = questions.get(`${uid}:${id}`);
      if (!row || row.status === "answered" || row.status === "stale") return null;
      if (row.status === "claimed" && row.answer !== answer) throw new MobileError("question_answer_conflict", "A different answer is already being applied.", 409);
      row.status = "claimed";
      row.answer = answer;
      row.claimedAt = row.claimedAt || nowIso();
      return { ...row };
    },
    async completeQuestionReply(scope, id, answer) {
      const uid = scoped(scope);
      const row = questions.get(`${uid}:${id}`);
      if (!row || row.status === "answered" || (row.status !== "claimed" && row.status !== "open")) return null;
      if (row.answer !== answer) throw new MobileError("question_answer_conflict", "A different answer is already being applied.", 409);
      row.status = "answered";
      row.answeredAt = nowIso();
      return { ...row };
    },
    async consumeOpenQuestion(scope, id, answer) { const uid = scoped(scope); const row = questions.get(`${uid}:${id}`); if (!row || row.status !== "open") return null; row.status = "answered"; row.answer = answer; return { ...row }; },
    async claimCallAttempt(scope, value) {
      const uid = scoped(scope);
      const timestamp = Date.parse(value.now || "");
      const day = Number.isNaN(timestamp)
        ? new Date(memoryNow()).toISOString().slice(0, 10)
        : new Date(timestamp).toISOString().slice(0, 10);
      const existing = [...calls.values()].filter((row) => row.uid === uid && row.day === day);
      if (existing.length >= callDailyUserLimit) return { rateLimited: true, reason: "daily_user_limit" };
      if (existing.some((row) => row.createdAt && Date.parse(value.now) - Date.parse(row.createdAt) < callCooldownMs)) return { rateLimited: true, reason: "cooldown" };
      if (existing.some((row) => row.idempotencyKey === value.idempotencyKey)) return { rateLimited: true, reason: "duplicate_request" };
      const current = callDayGuards.get(day) || 0;
      if (current >= callDailyGlobalLimit) return { rateLimited: true, reason: "daily_global_limit" };
      callDayGuards.set(day, current + 1);
      const attemptId = callAttemptIdFactory
        ? callAttemptIdFactory({ uid, day, idempotencyKey: value.idempotencyKey, sequence: calls.size + 1 })
        : `call:v1:${uid}:${calls.size + 1}`;
      const row = { attemptId, uid, day, status: "claimed", idempotencyKey: value.idempotencyKey, createdAt: value.now || nowIso() };
      calls.set(attemptId, row);
      return { ...row };
    },
    async finishCallAttempt(scope, value) { const row = calls.get(value.attemptId); if (row && row.uid === scoped(scope)) Object.assign(row, value); },
    async upsertDevice(scope, value) {
      const uid = scoped(scope);
      for (const [key, row] of devices) if (row.token === value.token && row.uid !== uid) devices.delete(key);
      const deviceId = value.deviceId || (deviceIdFactory && deviceIdFactory({ uid, value })) || `device:v1:${uid}:${value.token.slice(-8)}`;
      const row = { ...value, uid, deviceId };
      devices.set(value.token, row);
      return { ...row };
    },
    async deleteDevice(scope, token) {
      const uid = scoped(scope);
      const row = devices.get(token);
      if (row && row.uid === uid) devices.delete(token);
      return { deleted: true };
    },
    async listDevices(scope) {
      const uid = scoped(scope);
      return [...devices.values()].filter((row) => row.uid === uid).map((row) => ({ ...row }));
    },
    async removeDevice(scope, token) {
      const uid = scoped(scope);
      const row = devices.get(token);
      if (row && row.uid === uid) devices.delete(token);
      return { deleted: true };
    },
    async recordApnsResult(scope, input) {
      const result = normalizeApnsResult(scope, input);
      apnsResults.push({ ...result });
      return { ...result };
    },
    async readDeletionReceipt(scope, operationId) { const uid = scoped(scope); return deletionReceipts.get(`${uid}:${operationId}`) || null; },
    async readDeletionReceiptByCapability(capability, operationId) {
      const hash = sha256(capability);
      for (const receipt of deletionReceipts.values()) if (receipt.operationId === operationId && receipt.capabilityHash === hash) return { ...receipt };
      return null;
    },
    async writeDeletionReceipt(scope, receipt) { const uid = scoped(scope); deletionReceipts.set(`${uid}:${receipt.operationId}`, { ...receipt }); return receipt; },
    async finalizeAccountDeletion(scope, options2 = {}) {
      const uid = scoped(scope);
      if (!users.has(uid)) throw new MobileError("account_not_found", "Account not found.", 404);
      const completionNow = () => nowIso({ now: memoryNow });
      const receipt = {
        operationId: options2.operationId, status: "completed", completedAt: completionNow(),
        providerCleanup: options2.providerCleanup || [], capabilityHash: options2.capabilityHash,
      };
      for (const row of sessions.values()) if (row.uid === uid) row.revokedAt = completionNow();
      deletionReceipts.set(`${uid}:${receipt.operationId}`, { ...receipt });
      users.delete(uid);
      for (const key of sessions.keys()) if (sessions.get(key).uid === uid) sessions.delete(key);
      const preserve = options2.preserveIdempotencyKey ? `${uid}:${options2.preserveIdempotencyKey}` : null;
      for (const key of idempotency.keys()) if (key.startsWith(`${uid}:`) && key !== preserve) idempotency.delete(key);
      outbox.delete(uid);
      for (const key of questions.keys()) if (key.startsWith(`${uid}:`)) questions.delete(key);
      for (const key of devices.keys()) if (devices.get(key).uid === uid) devices.delete(key);
      for (const key of calls.keys()) if (calls.get(key).uid === uid) calls.delete(key);
      return { ...receipt };
    },
    async deleteAccount(scope, options2 = {}) {
      const uid = scoped(scope);
      users.delete(uid);
      for (const key of sessions.keys()) if (sessions.get(key).uid === uid) sessions.delete(key);
      const preserve = options2.preserveIdempotencyKey ? `${uid}:${options2.preserveIdempotencyKey}` : null;
      for (const key of idempotency.keys()) if (key.startsWith(`${uid}:`) && key !== preserve) idempotency.delete(key);
      outbox.delete(uid);
      for (const key of questions.keys()) if (key.startsWith(`${uid}:`)) questions.delete(key);
      for (const [key, row] of devices) if (row.uid === uid) devices.delete(key);
      for (const key of calls.keys()) if (calls.get(key).uid === uid) calls.delete(key);
      return { deleted: true };
    },
  };
}

module.exports = { createSupabaseMobileStore, createMemoryMobileStore, requireScope };
