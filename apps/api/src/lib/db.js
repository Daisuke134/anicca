// pg is CommonJS. This project is ESM ("type": "module"), so use default import.
import pg from 'pg';
const { Pool } = pg;

let pool = null;

function getPool() {
  if (pool) return pool;

  const { DATABASE_URL } = process.env;
  if (!DATABASE_URL) {
    // Avoid throwing at import-time so unit tests that mock db usage can run.
    throw new Error('DATABASE_URL is not set');
  }

  pool = new Pool({
    connectionString: DATABASE_URL,
    max: 5,
    idleTimeoutMillis: 30_000,
  });
  return pool;
}

export async function query(text, params) {
  const client = await getPool().connect();
  try {
    return await client.query(text, params);
  } finally {
    client.release();
  }
}

export { pool };
