import { query } from '../../lib/db.js';
import baseLogger from '../../utils/logger.js';
import { resolveProfileId, isUuid, ensureDeviceProfileId } from './userIdResolver.js';

const logger = baseLogger.withContext('MobileProfileService');

async function ensureProfileRow(userId, metadata = {}) {
  if (!isUuid(userId)) return false;
  await query(
    `insert into profiles (id, metadata, created_at, updated_at)
     values ($1::uuid, coalesce($2::jsonb, '{}'::jsonb), timezone('utc', now()), timezone('utc', now()))
     on conflict (id) do nothing`,
    [userId, JSON.stringify(metadata || {})]
  );
  return true;
}

/**
 * Get user profile by device ID
 * @param {string} deviceId - Device identifier
 * @returns {Promise<object|null>} Profile data or null if not found
 */
export async function getProfile(deviceId) {
  try {
    const result = await query(
      `SELECT mp.profile, mp.language, mp.user_id, mp.updated_at, 
              COALESCE(us.language, 'en') as user_settings_language
       FROM mobile_profiles mp
       LEFT JOIN user_settings us ON mp.user_id::uuid = us.user_id
       WHERE mp.device_id = $1`,
      [deviceId]
    );
    
    if (result.rows.length === 0) {
      return null;
    }
    
    const row = result.rows[0];
    return {
      profile: row.profile,
      language: row.language,
      userSettingsLanguage: row.user_settings_language,
      userId: row.user_id,
      updatedAt: row.updated_at
    };
  } catch (error) {
    logger.error('Failed to get profile', error);
    throw error;
  }
}

/**
 * Upsert user profile
 * @param {object} params - Parameters
 * @param {string} params.deviceId - Device identifier
 * @param {string} params.userId - User ID from auth
 * @param {object} params.profile - Profile data object
 * @param {string} params.language - Language code
 * @returns {Promise<void>}
 */
export async function upsertProfile({ deviceId, userId, profile, language }) {
  try {
    const incomingUserId = String(userId || '').trim();
    const incomingDeviceId = String(deviceId || '').trim();

    // Normalize to UUID-backed profile_id whenever possible.
    let effectiveUserId = incomingUserId;
    const resolvedUserId = await resolveProfileId(incomingUserId);
    if (resolvedUserId) {
      effectiveUserId = resolvedUserId;
    } else if (incomingDeviceId) {
      const ensured = await ensureDeviceProfileId(incomingDeviceId);
      if (ensured) effectiveUserId = ensured;
    }

    // Upsert mobile_profiles
    await query(
      `INSERT INTO mobile_profiles (device_id, user_id, profile, language, updated_at)
       VALUES ($1, $2, $3, $4, NOW())
       ON CONFLICT (device_id) 
       DO UPDATE SET 
         user_id = EXCLUDED.user_id,
         profile = EXCLUDED.profile,
         language = EXCLUDED.language,
         updated_at = NOW()`,
      [deviceId, effectiveUserId, JSON.stringify(profile), language]
    );
    
    // Update user_settings.language if preferredLanguage is provided
    if (language && (language === 'ja' || language === 'en') && isUuid(effectiveUserId)) {
      try {
        await ensureProfileRow(effectiveUserId, { source: 'mobile_profile' });
        await query(
          `INSERT INTO user_settings (user_id, language, updated_at)
           VALUES ($1::uuid, $2, NOW())
           ON CONFLICT (user_id)
           DO UPDATE SET
             language = EXCLUDED.language,
             updated_at = NOW()`,
          [effectiveUserId, language]
        );
      } catch (err) {
        // 23503 = foreign key violation (safety net)
        if (err.code === '23503') {
          logger.info('Skipping user_settings upsert: foreign key violation', { userId: effectiveUserId, deviceId });
        } else {
          throw err;
        }
      }
    }
    
    logger.info(`Profile upserted for device: ${deviceId}, language: ${language}`);

    // v0.3: traits/big5/nudge settings are authoritative in user_traits (uuid key).
    // We accept both legacy keys (idealTraits/problems/stickyModeEnabled) and new keys (ideals/struggles/big5/nudgeIntensity/stickyMode).
    const profileId = await resolveProfileId(effectiveUserId);
    if (profileId) {
      try {
        await ensureProfileRow(profileId, { source: 'traits_sync' });
        await upsertUserTraitsFromProfilePayload(profileId, profile);
      } catch (traitsError) {
        if (traitsError.code === '23503') {
          logger.info('Skipping user_traits upsert: foreign key violation', { profileId, deviceId });
        } else {
          throw traitsError;
        }
      }
    } else {
      // Non-uuid user_id can happen during migration; don't hard-fail profile upsert.
      logger.warn('Could not resolve profileId; user_traits sync skipped', { userId: effectiveUserId });
    }

    return { profileId: profileId || null };
  } catch (error) {
    logger.error('Failed to upsert profile', error);
    throw error;
  }
}

async function upsertUserTraitsFromProfilePayload(profileId, payload) {
  // Normalize old → new
  const ideals = Array.isArray(payload?.ideals) ? payload.ideals : Array.isArray(payload?.idealTraits) ? payload.idealTraits : [];
  const struggles = Array.isArray(payload?.struggles) ? payload.struggles : Array.isArray(payload?.problems) ? payload.problems : [];

  const nudgeIntensityRaw = String(payload?.nudgeIntensity || '').trim();
  const nudgeIntensity = ['quiet', 'normal', 'active'].includes(nudgeIntensityRaw) ? nudgeIntensityRaw : null;

  const stickyMode =
    typeof payload?.stickyMode === 'boolean'
      ? payload.stickyMode
      : typeof payload?.stickyModeEnabled === 'boolean'
        ? payload.stickyModeEnabled
        : typeof payload?.wakeStickyModeEnabled === 'boolean'
          ? payload.wakeStickyModeEnabled
          : null;

  const big5 = payload?.big5 && typeof payload.big5 === 'object' ? payload.big5 : null;
  const keywords = Array.isArray(payload?.keywords) ? payload.keywords : [];
  const summary = typeof payload?.summary === 'string' ? payload.summary : null;

  // Only write if something is present (avoid overwriting with empties during partial updates)
  const hasAny =
    (ideals && ideals.length > 0) ||
    (struggles && struggles.length > 0) ||
    big5 ||
    (keywords && keywords.length > 0) ||
    (summary != null) ||
    (nudgeIntensity != null) ||
    (stickyMode != null);

  if (!hasAny) return;

  await query(
    `insert into user_traits
       (user_id, ideals, struggles, big5, keywords, summary, nudge_intensity, sticky_mode, created_at, updated_at)
     values
       ($1::uuid,
        coalesce($2::text[], '{}'::text[]),
        coalesce($3::text[], '{}'::text[]),
        coalesce($4::jsonb, '{}'::jsonb),
        coalesce($5::text[], '{}'::text[]),
        coalesce($6::text, ''),
        coalesce($7::text, 'normal'),
        coalesce($8::boolean, false),
        timezone('utc', now()),
        timezone('utc', now()))
     on conflict (user_id)
     do update set
       ideals = case when array_length(excluded.ideals,1) is null then user_traits.ideals else excluded.ideals end,
       struggles = case when array_length(excluded.struggles,1) is null then user_traits.struggles else excluded.struggles end,
       big5 = case when excluded.big5 = '{}'::jsonb then user_traits.big5 else excluded.big5 end,
       keywords = case when array_length(excluded.keywords,1) is null then user_traits.keywords else excluded.keywords end,
       summary = case when excluded.summary = '' then user_traits.summary else excluded.summary end,
       nudge_intensity = coalesce(excluded.nudge_intensity, user_traits.nudge_intensity),
       sticky_mode = coalesce(excluded.sticky_mode, user_traits.sticky_mode),
       updated_at = timezone('utc', now())`,
    [
      profileId,
      ideals.length ? ideals : null,
      struggles.length ? struggles : null,
      big5 ? JSON.stringify(big5) : null,
      keywords.length ? keywords : null,
      summary ?? null,
      nudgeIntensity,
      stickyMode
    ]
  );
}

/**
 * Get profile by user ID (for sync across devices in future)
 * @param {string} userId - User ID
 * @returns {Promise<object|null>} Latest profile or null
 */
export async function getProfileByUserId(userId) {
  try {
    const result = await query(
      `SELECT mp.profile,
              mp.language,
              mp.updated_at,
              COALESCE(us.language, 'en') AS user_settings_language
       FROM mobile_profiles mp
       LEFT JOIN user_settings us ON mp.user_id::uuid = us.user_id
       WHERE mp.user_id = $1
       ORDER BY mp.updated_at DESC
       LIMIT 1`,
      [userId]
    );
    
    if (result.rows.length === 0) {
      return null;
    }
    
    const row = result.rows[0];
    return {
      profile: row.profile,
      language: row.language,
      userSettingsLanguage: row.user_settings_language,
      updatedAt: row.updated_at
    };
  } catch (error) {
    logger.error('Failed to get profile by user ID', error);
    throw error;
  }
}
