import { fetch } from 'undici';

function requiredEnv(name) {
  const v = String(process.env[name] || '').trim();
  if (!v) throw new Error(`${name} is required`);
  return v;
}

export async function postMoltbookStatus({ status, visibility = 'public', dryRun: dryRunOpt } = {}) {
  const dryRun =
    dryRunOpt === true || String(process.env.MOLTBOOK_DRY_RUN || '').toLowerCase() === 'true';
  if (dryRun) {
    return { dryRun: true, statusId: null, url: null };
  }

  const baseUrl = requiredEnv('MOLTBOOK_BASE_URL').replace(/\/+$/, '');
  const token = requiredEnv('MOLTBOOK_ACCESS_TOKEN');

  const res = await fetch(`${baseUrl}/api/v1/statuses`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ status, visibility }),
  });

  if (!res.ok) {
    const body = await res.text().catch(() => '');
    const err = new Error(`Moltbook post failed (${res.status})`);
    err.details = body;
    throw err;
  }

  const json = await res.json();
  return { dryRun: false, statusId: json?.id || null, url: json?.url || null };
}

export default {
  postMoltbookStatus,
};

