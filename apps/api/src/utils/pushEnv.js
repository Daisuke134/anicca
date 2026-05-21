// Shared environment parsing for APNs / push delivery.
// We treat the Railway (or explicit) env key as a single source of truth.

export function getRawPushEnv() {
  return (
    process.env.PUSH_ENV ||
    process.env.APNS_ENV ||
    process.env.RAILWAY_ENVIRONMENT_NAME ||
    process.env.RAILWAY_ENVIRONMENT ||
    ''
  );
}

export function parsePushEnv(raw) {
  const v = String(raw || '').toLowerCase();
  if (v.includes('staging')) return 'staging';
  if (v.includes('prod')) return 'prod';
  if (v === 'production') return 'prod';
  if (v === 'staging') return 'staging';
  if (v === 'prod') return 'prod';
  return 'dev';
}

export function getPushEnv() {
  return parsePushEnv(getRawPushEnv());
}

