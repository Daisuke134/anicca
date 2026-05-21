import crypto from 'crypto';
import { pool } from '../../lib/db.js';

function hash(token) {
  return crypto.createHash('sha256').update(token).digest('hex');
}

export async function upsertRefreshToken({ userId, token, deviceId, ttlDays = 30, userAgent = null }) {
  const client = await pool.connect();
  try {
    const tokenHash = hash(token);
    const expiresAt = new Date(Date.now() + ttlDays * 24 * 60 * 60 * 1000);
    await client.query(
      `INSERT INTO refresh_tokens (user_id, token_hash, device_id, user_agent, expires_at)
       VALUES ($1::uuid, $2, $3, $4, $5)
       ON CONFLICT DO NOTHING`,
      [userId, tokenHash, deviceId, userAgent, expiresAt]
    );
  } finally {
    client.release();
  }
}

export async function findValidTokenRow(token) {
  const tokenHash = hash(token);
  const { rows } = await pool.query(
    `SELECT * FROM refresh_tokens
     WHERE token_hash = $1
       AND revoked_at IS NULL
       AND expires_at > now()
     LIMIT 1`,
    [tokenHash]
  );
  return rows[0] || null;
}

export async function rotateToken(oldRow, newToken, meta = {}) {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    // revoke old
    await client.query(
      `UPDATE refresh_tokens SET revoked_at = now(), last_used_at = now() WHERE id = $1`,
      [oldRow.id]
    );
    // insert new
    const tokenHash = hash(newToken);
    const expiresAt = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000);
    await client.query(
      `INSERT INTO refresh_tokens (user_id, token_hash, device_id, user_agent, expires_at, rotated_from)
       VALUES ($1::uuid, $2, $3, $4, $5, $6)`,
      [oldRow.user_id, tokenHash, meta.deviceId || oldRow.device_id, meta.userAgent || oldRow.user_agent, expiresAt, oldRow.id]
    );
    await client.query('COMMIT');
  } catch (e) {
    await client.query('ROLLBACK');
    throw e;
  } finally {
    client.release();
  }
}

export async function markReuseAndRevokeAll(userId) {
  await pool.query(
    `UPDATE refresh_tokens
     SET reuse_detected = TRUE, revoked_at = now()
     WHERE user_id = $1::uuid AND revoked_at IS NULL`,
    [userId]
  );
}

export async function revokeByToken(refreshToken) {
  const row = await findValidTokenRow(refreshToken);
  if (!row) return;
  await pool.query(`UPDATE refresh_tokens SET revoked_at = now() WHERE id = $1`, [row.id]);
}

export async function revokeAllRefreshTokensForUser(userId) {
  await pool.query(`UPDATE refresh_tokens SET revoked_at = now() WHERE user_id = $1::uuid AND revoked_at IS NULL`, [userId]);
}












