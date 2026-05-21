import { query } from '../../lib/db.js';
import baseLogger from '../../utils/logger.js';
import crypto from 'crypto';

const logger = baseLogger.withContext('UserIdResolver');

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function isUuid(value) {
  return UUID_RE.test(String(value || ''));
}

/**
 * Resolve incoming userId (uuid or apple_user_id) into profiles.id (uuid string).
 * Returns null if not resolvable.
 */
export async function resolveProfileId(userId) {
  const raw = String(userId || '').trim();
  if (!raw) return null;
  if (isUuid(raw)) {
    // UUID文字列でも profiles 実在確認を行い、孤立IDのまま進まないようにする。
    try {
      const exists = await query(
        `select 1
           from profiles
          where id = $1::uuid
          limit 1`,
        [raw]
      );
      if (exists.rows.length > 0) return raw;
    } catch (e) {
      logger.warn('Failed to verify profileId existence by uuid', e);
    }
  }

  // Fallback: match profiles.metadata.apple_user_id
  try {
    const r = await query(
      `select id
         from profiles
        where metadata->>'apple_user_id' = $1
        limit 1`,
      [raw]
    );
    return r.rows?.[0]?.id ? String(r.rows[0].id) : null;
  } catch (e) {
    logger.warn('Failed to resolve profileId from profiles.metadata', e);
  }

  // Fallback: if the incoming identifier is actually a device id, and we've mapped it
  // to a UUID-backed profile via mobile_profiles, return that UUID.
  try {
    const r2 = await query(
      `select user_id
         from mobile_profiles
        where device_id = $1
        limit 1`,
      [raw]
    );
    const mapped = r2.rows?.[0]?.user_id ? String(r2.rows[0].user_id) : null;
    return mapped && isUuid(mapped) ? mapped : null;
  } catch (e2) {
    logger.warn('Failed to resolve profileId from mobile_profiles.device_id', e2);
    return null;
  }
}

/**
 * Ensure we have a UUID-backed profile for this device id.
 * Returns the profile UUID (string) or null.
 */
export async function ensureDeviceProfileId(deviceId) {
  const d = String(deviceId || '').trim();
  if (!d) return null;

  // If already mapped, reuse.
  try {
    const r = await query(
      `select user_id
         from mobile_profiles
        where device_id = $1
        limit 1`,
      [d]
    );
    const existing = r.rows?.[0]?.user_id ? String(r.rows[0].user_id) : null;
    if (existing && isUuid(existing)) {
      // Ensure profiles row exists (idempotent).
      await query(
        `insert into profiles (id, metadata, created_at, updated_at)
         values ($1::uuid, '{}'::jsonb, timezone('utc', now()), timezone('utc', now()))
         on conflict (id) do nothing`,
        [existing]
      );
      return existing;
    }
  } catch (e) {
    logger.warn('Failed reading mobile_profiles for device mapping', e);
  }

  const newId = crypto.randomUUID();
  try {
    await query(
      `insert into profiles (id, metadata, created_at, updated_at)
       values ($1::uuid,
               jsonb_build_object('source','device','device_id',$2::text),
               timezone('utc', now()),
               timezone('utc', now()))
       on conflict (id) do nothing`,
      [newId, d]
    );

    // Preserve existing profile/language for the device by only updating user_id.
    await query(
      `insert into mobile_profiles (device_id, user_id, updated_at, created_at)
       values ($1, $2, timezone('utc', now()), timezone('utc', now()))
       on conflict (device_id)
       do update set user_id = excluded.user_id,
                     updated_at = timezone('utc', now())`,
      [d, newId]
    );

    return newId;
  } catch (e2) {
    logger.warn('Failed ensuring device profile id', e2);
    return null;
  }
}








