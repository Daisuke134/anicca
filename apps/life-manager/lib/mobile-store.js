"use strict";

const { MobileError, nowIso, safeTimeZone } = require("./mobile-utils.js");

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
    const result = await request(`/rest/v1/${table}?${query.toString()}`, {}, "mobile_store_read_failed");
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
        select: "uid,name,phone,paid,home_address,calendar_provider,gmail_account_id,product_locale,calls_enabled,call_language,time_zone,calendar_status",
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
    async createOAuthState(row) {
      const body = {
        state_hash: row.stateHash,
        uid: row.uid || null,
        subject_hash: row.subject ? require("node:crypto").createHash("sha256").update(String(row.subject)).digest("hex") : null,
        provider: row.provider,
        redirect_uri: row.redirectUri || null,
        expires_at: row.expiresAt,
      };
      const result = await request("/rest/v1/lm_mobile_oauth_states", {
        method: "POST", headers: { "content-type": "application/json", Prefer: "return=minimal" }, body: JSON.stringify(body),
      }, "oauth_state_failed");
      if (result.conflict) throw new MobileError("oauth_state_failed", "Calendar connection is temporarily unavailable.", 503, true);
    },
    async claimOAuthState(stateHash, expected = {}) {
      const value = await rpc("claim_lm_mobile_oauth_state", {
        p_state_hash: stateHash, p_uid: expected.uid || null,
        p_subject_hash: expected.subject ? require("node:crypto").createHash("sha256").update(String(expected.subject)).digest("hex") : null,
      }, "oauth_state_failed");
      return asRow(value) || (value === true ? { stateHash } : null);
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
        select: "session_id,family_id,uid,product_locale,access_expires_at,refresh_expires_at,revoked_at,rotated_at",
        limit: "1",
      });
      return found[0] || null;
    },
    async findRefreshSession(refreshTokenHash) {
      const found = await rows("lm_mobile_sessions", {
        refresh_token_hash: `eq.${refreshTokenHash}`,
        select: "session_id,family_id,uid,product_locale,access_expires_at,refresh_expires_at,revoked_at,rotated_at",
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
        idempotency_key: `eq.${encodeFilter(key)}`, select: "request_hash,status,result,error,status_code", limit: "1",
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
          error: value.error || null, status_code: value.statusCode || null, updated_at: new Date().toISOString(),
        }),
      }, "idempotency_failed");
    },
    async appendOutbox(scope, row) {
      requireScope(scope);
      const result = await request("/rest/v1/lm_mobile_outbox", {
        method: "POST", headers: { "content-type": "application/json", Prefer: "return=representation" }, body: JSON.stringify({
          uid: scope.uid, id: row.id, key: row.key, type: row.type || null, args: row.args || {},
          user_content: row.userContent || null, question: row.question || null, route: row.route || null,
          created_at: row.createdAt || new Date().toISOString(), mutation_key: row.mutationKey || null,
        }),
      }, "outbox_write_failed");
      if (result.conflict) {
        const existing = await rows("lm_mobile_outbox", scopedParams(scope, {
          id: `eq.${encodeFilter(row.id)}`,
          limit: "1",
        }));
        return existing[0] || row;
      }
      return asRow(result.body) || row;
    },
    async listOutbox(scope, afterSequence = 0, limit = 50) {
      const found = await rows("lm_mobile_outbox", scopedParams(scope, {
        sequence: `gt.${Math.max(0, Number(afterSequence) || 0)}`, order: "sequence.asc", limit: String(Math.min(100, Math.max(1, limit))),
      }));
      return found;
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
      return asRow(result.body) || question;
    },
    async consumeOpenQuestion(scope, questionId, answer) {
      const value = await rpc("consume_lm_mobile_question", { p_uid: requireScope(scope).uid, p_question_id: questionId, p_answer: answer }, "question_reply_failed");
      return asRow(value) || (value === true ? { id: questionId, answer } : null);
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
      const result = await request("/rest/v1/lm_mobile_devices", {
        method: "POST", headers: { "content-type": "application/json", Prefer: "resolution=merge-duplicates,return=representation" }, body: JSON.stringify({ uid: requireScope(scope).uid, ...value }),
      }, "device_write_failed");
      return asRow(result.body) || value;
    },
    async deleteDevice(scope, token) {
      requireScope(scope);
      await request(`/rest/v1/lm_mobile_devices?uid=eq.${encodeFilter(scope.uid)}&token=eq.${encodeFilter(token)}`, { method: "DELETE", headers: { Prefer: "return=minimal" } }, "device_delete_failed");
      return { deleted: true };
    },
    async writeDeletionReceipt(scope, receipt) {
      const result = await request("/rest/v1/lm_mobile_deletion_receipts", {
        method: "POST", headers: { "content-type": "application/json", Prefer: "resolution=merge-duplicates,return=representation" }, body: JSON.stringify({ uid: requireScope(scope).uid, ...receipt }),
      }, "deletion_receipt_failed");
      return asRow(result.body) || receipt;
    },
    async readDeletionReceipt(scope, operationId) {
      const found = await rows("lm_mobile_deletion_receipts", scopedParams(scope, {
        operation_id: `eq.${encodeFilter(operationId)}`,
        select: "operation_id,status,completed_at,provider_cleanup",
        limit: "1",
      }));
      return found[0] || null;
    },
    async deleteAccount(scope) {
      return rpc("delete_lm_mobile_account", { p_uid: requireScope(scope).uid }, "account_delete_failed");
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
    _users: users, _sessions: sessions, _states: states, _idempotency: idempotency, _outbox: outbox, _questions: questions, _devices: devices, _calls: calls, _deletionReceipts: deletionReceipts,
    async readUser(scope) { const row = user(scope); return row ? { ...row } : null; },
    async patchUser(scope, patch, options2 = {}) { const row = user(scope, options2.expectedUid); if (!row) throw new MobileError("account_not_found", "Account not found.", 404); Object.assign(row, patch); return { ...row }; },
    async readAnalysisState(scope) { const row = user(scope); return row && row.analysisState ? { ...row.analysisState } : { status: "idle" }; },
    async writeAnalysisState(scope, state) { const row = user(scope); if (!row) throw new MobileError("account_not_found", "Account not found.", 404); row.analysisState = { ...state, updatedAt: state.updatedAt || nowIso() }; return { ...row.analysisState }; },
    async createOAuthState(row) { states.set(row.stateHash, { ...row }); },
    async claimOAuthState(hash, expected = {}) { const row = states.get(hash); if (!row || row.usedAt || (row.uid && expected.uid && row.uid !== expected.uid)) return null; row.usedAt = nowIso(); return { ...row }; },
    async createMobileSession(row) { sessions.set(row.sessionId, { ...row }); },
    async findAccessSession(hash) { return [...sessions.values()].find((row) => row.accessTokenHash === hash) || null; },
    async findRefreshSession(hash) { return [...sessions.values()].find((row) => row.refreshTokenHash === hash) || null; },
    async rotateRefreshSession(row, next) { if (row.rotatedAt || row.revokedAt) { for (const item of sessions.values()) if (item.familyId === row.familyId) item.revokedAt = nowIso(); return { replay: true }; } row.rotatedAt = nowIso(); sessions.set(next.sessionId, { ...next }); return { session: next }; },
    async revokeMobileSession(scope) { const row = sessions.get(scope.sessionId); if (row && row.uid === scoped(scope)) row.revokedAt = nowIso(); },
    async revokeAllSessions(scope) { const uid = scoped(scope); for (const row of sessions.values()) if (row.uid === uid) row.revokedAt = nowIso(); },
    async readIdempotency(scope, key) { return idempotency.get(`${scoped(scope)}:${key}`) || null; },
    async claimIdempotency(scope, key, value) { const id = `${scoped(scope)}:${key}`; if (idempotency.has(id)) return false; idempotency.set(id, { ...value }); return true; },
    async completeIdempotency(scope, key, value) { const id = `${scoped(scope)}:${key}`; idempotency.set(id, { ...idempotency.get(id), ...value }); },
    async appendOutbox(scope, row) {
      const uid = scoped(scope);
      const existing = (outbox.get(uid) || []).find((item) => item.id === row.id);
      if (existing) return { ...existing };
      const item = { ...row, uid, sequence: ++sequence, createdAt: row.createdAt || nowIso() };
      if (!outbox.has(uid)) outbox.set(uid, []);
      outbox.get(uid).push(item);
      return { ...item };
    },
    async listOutbox(scope, after = 0, limit = 50) { return (outbox.get(scoped(scope)) || []).filter((row) => row.sequence > after).slice(0, limit).map((row) => ({ ...row })); },
    async createQuestion(scope, question) { const uid = scoped(scope); const row = { ...question, uid, status: "open" }; questions.set(`${uid}:${row.id}`, row); return { ...row }; },
    async consumeOpenQuestion(scope, id, answer) { const uid = scoped(scope); const row = questions.get(`${uid}:${id}`); if (!row || row.status !== "open") return null; row.status = "answered"; row.answer = answer; return { ...row }; },
    async claimCallAttempt(scope, value) { const uid = scoped(scope); const day = String(value.now || "").slice(0, 10); const existing = [...calls.values()].filter((row) => row.uid === uid && row.day === day); if (existing.length >= 5) return { rateLimited: true, reason: "daily_user_limit" }; if (existing.some((row) => row.createdAt && Date.parse(value.now) - Date.parse(row.createdAt) < 10 * 60 * 1000)) return { rateLimited: true, reason: "cooldown" }; const attemptId = `call:v1:${uid}:${calls.size + 1}`; const row = { attemptId, uid, day, status: "claimed", idempotencyKey: value.idempotencyKey, createdAt: value.now || nowIso() }; calls.set(attemptId, row); return { ...row }; },
    async finishCallAttempt(scope, value) { const row = calls.get(value.attemptId); if (row && row.uid === scoped(scope)) Object.assign(row, value); },
    async upsertDevice(scope, value) { const uid = scoped(scope); const row = { ...value, uid, deviceId: value.deviceId || `device:v1:${uid}:${value.token.slice(-8)}` }; devices.set(`${uid}:${value.token}`, row); return { ...row }; },
    async deleteDevice(scope, token) { devices.delete(`${scoped(scope)}:${token}`); return { deleted: true }; },
    async readDeletionReceipt(scope, operationId) { const uid = scoped(scope); return deletionReceipts.get(`${uid}:${operationId}`) || null; },
    async writeDeletionReceipt(scope, receipt) { const uid = scoped(scope); deletionReceipts.set(`${uid}:${receipt.operationId}`, { ...receipt }); return receipt; },
    async deleteAccount(scope) {
      const uid = scoped(scope);
      users.delete(uid);
      for (const key of sessions.keys()) if (sessions.get(key).uid === uid) sessions.delete(key);
      outbox.delete(uid);
      for (const key of questions.keys()) if (key.startsWith(`${uid}:`)) questions.delete(key);
      for (const key of devices.keys()) if (key.startsWith(`${uid}:`)) devices.delete(key);
      for (const key of calls.keys()) if (calls.get(key).uid === uid) calls.delete(key);
      return { deleted: true };
    },
  };
}

module.exports = { createSupabaseMobileStore, createMemoryMobileStore, requireScope };
