import { chmodSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { randomUUID } from 'node:crypto';

import { verifyThe402Webhook } from './the402-channel.mjs';

const STATUSES = ['pending', 'processing', 'completed', 'dead'];

function reject(reason) {
  throw new Error(`the402 inbox rejected: ${reason}`);
}

function validateEvent({ eventId, type, payload, receivedAtMs }) {
  if (typeof eventId !== 'string' || !/^[A-Za-z0-9_.:-]{1,256}$/.test(eventId)) {
    reject('invalid event id');
  }
  if (typeof type !== 'string' || !/^[A-Za-z0-9_.:-]{1,64}$/.test(type)) {
    reject('invalid event type');
  }
  if (!Number.isSafeInteger(receivedAtMs) || receivedAtMs < 0) reject('invalid received time');
  let payloadJson;
  try { payloadJson = JSON.stringify(payload); }
  catch { reject('payload is not serializable'); }
  if (typeof payloadJson !== 'string' || Buffer.byteLength(payloadJson) > 1_048_576) {
    reject('invalid payload size');
  }
  return { eventId, type, payloadJson, receivedAtMs };
}

function validateTime(value, name) {
  if (!Number.isSafeInteger(value) || value < 0) reject(`invalid ${name}`);
  return value;
}

function validateLeaseToken(value) {
  if (typeof value !== 'string' || !/^[A-Za-z0-9-]{1,128}$/.test(value)) {
    reject('invalid lease token');
  }
  return value;
}

export function openThe402Inbox(dbPath) {
  if (typeof dbPath !== 'string' || !dbPath.length) reject('missing database path');
  if (dbPath !== ':memory:') mkdirSync(dirname(dbPath), { recursive: true, mode: 0o700 });

  const db = new DatabaseSync(dbPath, { timeout: 5_000 });
  if (dbPath !== ':memory:') chmodSync(dbPath, 0o600);
  db.exec(`
    PRAGMA journal_mode = WAL;
    PRAGMA synchronous = FULL;
    PRAGMA foreign_keys = ON;
    CREATE TABLE IF NOT EXISTS webhook_events (
      event_id TEXT PRIMARY KEY,
      event_type TEXT NOT NULL,
      payload_json TEXT NOT NULL,
      status TEXT NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'dead')),
      attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
      received_at_ms INTEGER NOT NULL CHECK (received_at_ms >= 0),
      available_at_ms INTEGER NOT NULL CHECK (available_at_ms >= 0),
      lease_until_ms INTEGER,
      lease_token TEXT,
      completed_at_ms INTEGER,
      last_error_code TEXT,
      updated_at_ms INTEGER NOT NULL CHECK (updated_at_ms >= 0)
    );
    CREATE INDEX IF NOT EXISTS webhook_events_ready
      ON webhook_events(status, available_at_ms, received_at_ms);
  `);

  const insert = db.prepare(`
    INSERT INTO webhook_events (
      event_id, event_type, payload_json, status, received_at_ms, available_at_ms, updated_at_ms
    ) VALUES (?, ?, ?, 'pending', ?, ?, ?)
    ON CONFLICT(event_id) DO NOTHING
  `);
  const findStatus = db.prepare('SELECT status FROM webhook_events WHERE event_id = ?');
  const countByStatus = db.prepare('SELECT status, COUNT(*) AS count FROM webhook_events GROUP BY status');
  const nextReady = db.prepare(`
    SELECT event_id, event_type, payload_json, attempts
    FROM webhook_events
    WHERE (status = 'pending' AND available_at_ms <= ?)
       OR (status = 'processing' AND lease_until_ms <= ?)
    ORDER BY received_at_ms, event_id
    LIMIT 1
  `);
  const claim = db.prepare(`
    UPDATE webhook_events
    SET status = 'processing', attempts = attempts + 1,
        lease_until_ms = ?, lease_token = ?, updated_at_ms = ?
    WHERE event_id = ?
  `);
  const complete = db.prepare(`
    UPDATE webhook_events
    SET status = 'completed', completed_at_ms = ?, lease_until_ms = NULL,
        lease_token = NULL, updated_at_ms = ?
    WHERE event_id = ? AND status = 'processing' AND lease_token = ?
  `);
  const activeLease = db.prepare(`
    SELECT attempts FROM webhook_events
    WHERE event_id = ? AND status = 'processing' AND lease_token = ?
  `);
  const retry = db.prepare(`
    UPDATE webhook_events
    SET status = 'pending', available_at_ms = ?, lease_until_ms = NULL,
        lease_token = NULL, last_error_code = ?, updated_at_ms = ?
    WHERE event_id = ? AND status = 'processing' AND lease_token = ?
  `);
  const deadLetter = db.prepare(`
    UPDATE webhook_events
    SET status = 'dead', lease_until_ms = NULL, lease_token = NULL,
        last_error_code = ?, updated_at_ms = ?
    WHERE event_id = ? AND status = 'processing' AND lease_token = ?
  `);
  const auditEvent = db.prepare(`
    SELECT event_id, event_type, status, attempts, received_at_ms,
           available_at_ms, lease_until_ms, completed_at_ms, last_error_code
    FROM webhook_events WHERE event_id = ?
  `);

  function inImmediateTransaction(run) {
    db.exec('BEGIN IMMEDIATE');
    try {
      const value = run();
      db.exec('COMMIT');
      return value;
    } catch (error) {
      db.exec('ROLLBACK');
      throw error;
    }
  }

  return {
    enqueue(event) {
      const valid = validateEvent(event);
      const write = insert.run(
        valid.eventId,
        valid.type,
        valid.payloadJson,
        valid.receivedAtMs,
        valid.receivedAtMs,
        valid.receivedAtMs,
      );
      const duplicate = Number(write.changes) === 0;
      const row = findStatus.get(valid.eventId);
      return { accepted: true, duplicate, eventId: valid.eventId, status: row.status };
    },

    claimNext({ nowMs, leaseMs = 30_000 }) {
      validateTime(nowMs, 'claim time');
      if (!Number.isSafeInteger(leaseMs) || leaseMs <= 0 || leaseMs > 86_400_000) {
        reject('invalid lease duration');
      }
      return inImmediateTransaction(() => {
        const row = nextReady.get(nowMs, nowMs);
        if (!row) return null;
        const leaseToken = randomUUID();
        const leaseUntilMs = nowMs + leaseMs;
        claim.run(leaseUntilMs, leaseToken, nowMs, row.event_id);
        return {
          eventId: row.event_id,
          type: row.event_type,
          payload: JSON.parse(row.payload_json),
          attempt: Number(row.attempts) + 1,
          leaseToken,
          leaseUntilMs,
        };
      });
    },

    complete({ eventId, leaseToken, nowMs }) {
      if (typeof eventId !== 'string' || !eventId.length) reject('invalid event id');
      validateLeaseToken(leaseToken);
      validateTime(nowMs, 'completion time');
      const write = complete.run(nowMs, nowMs, eventId, leaseToken);
      return { completed: Number(write.changes) === 1, eventId };
    },

    fail({ eventId, leaseToken, nowMs, retryDelayMs, maxAttempts, errorCode }) {
      if (typeof eventId !== 'string' || !eventId.length) reject('invalid event id');
      validateLeaseToken(leaseToken);
      validateTime(nowMs, 'failure time');
      if (!Number.isSafeInteger(retryDelayMs) || retryDelayMs < 0 || retryDelayMs > 86_400_000) {
        reject('invalid retry delay');
      }
      if (!Number.isSafeInteger(maxAttempts) || maxAttempts < 1 || maxAttempts > 100) {
        reject('invalid attempt cap');
      }
      if (typeof errorCode !== 'string' || !/^[A-Za-z0-9_.:-]{1,64}$/.test(errorCode)) {
        reject('invalid error code');
      }
      return inImmediateTransaction(() => {
        const row = activeLease.get(eventId, leaseToken);
        if (!row) return { updated: false, eventId, status: null, availableAtMs: null };
        if (Number(row.attempts) >= maxAttempts) {
          deadLetter.run(errorCode, nowMs, eventId, leaseToken);
          return { updated: true, eventId, status: 'dead', availableAtMs: null };
        }
        const availableAtMs = nowMs + retryDelayMs;
        if (!Number.isSafeInteger(availableAtMs)) reject('retry time overflow');
        retry.run(availableAtMs, errorCode, nowMs, eventId, leaseToken);
        return { updated: true, eventId, status: 'pending', availableAtMs };
      });
    },

    audit(eventId) {
      if (typeof eventId !== 'string' || !eventId.length) reject('invalid event id');
      const row = auditEvent.get(eventId);
      if (!row) return null;
      return {
        eventId: row.event_id,
        type: row.event_type,
        status: row.status,
        attempts: Number(row.attempts),
        receivedAtMs: Number(row.received_at_ms),
        availableAtMs: row.status === 'pending' ? Number(row.available_at_ms) : null,
        leaseUntilMs: row.lease_until_ms === null ? null : Number(row.lease_until_ms),
        completedAtMs: row.completed_at_ms === null ? null : Number(row.completed_at_ms),
        lastErrorCode: row.last_error_code,
      };
    },

    stats() {
      const result = Object.fromEntries(STATUSES.map((status) => [status, 0]));
      let total = 0;
      for (const row of countByStatus.all()) {
        const count = Number(row.count);
        result[row.status] = count;
        total += count;
      }
      return { total, ...result };
    },

    close() { db.close(); },
  };
}

export function acceptThe402Webhook({
  inbox,
  rawBody,
  headers,
  apiKey,
  webhookSecret,
  nowMs = Date.now(),
}) {
  if (!inbox || typeof inbox.enqueue !== 'function') reject('missing durable inbox');
  const verified = verifyThe402Webhook({
    rawBody,
    headers,
    apiKey,
    webhookSecret,
    nowMs,
  });
  const write = inbox.enqueue({
    eventId: verified.eventId,
    type: verified.type,
    payload: verified.payload,
    receivedAtMs: nowMs,
  });
  return {
    ok: true,
    accepted: true,
    duplicate: write.duplicate,
    type: verified.type,
    eventId: verified.eventId,
    status: write.status,
  };
}
