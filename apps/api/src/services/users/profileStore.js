import { randomUUID } from 'crypto';

import { query } from '../../lib/db.js';

import baseLogger from '../../utils/logger.js';

const logger = baseLogger.withContext('ProfileStore');

export async function getOrCreateInternalUser({ appleUserId, email, displayName }) {
  const existing = await query(
    `SELECT id
       FROM profiles
      WHERE metadata->>'apple_user_id' = $1
      LIMIT 1`,
    [appleUserId]
  );
  if (existing.rows.length > 0) {
    return existing.rows[0].id;
  }

  const newId = randomUUID();
  const metadata = {
    apple_user_id: appleUserId,
    last_known_email: email ?? null,
    last_known_display_name: displayName ?? null
  };

  await query(
    `INSERT INTO profiles (id, email, metadata)
     VALUES ($1::uuid, $2, $3::jsonb)`,
    [newId, email, JSON.stringify(metadata)]
  );

  logger.info(`Created profile ${newId} for Apple user ${appleUserId}`);
  return newId;
}


