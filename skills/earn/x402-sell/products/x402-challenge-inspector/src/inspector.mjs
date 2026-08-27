const ADDRESS_RE = /^0x[0-9a-fA-F]{40}$/;
const NETWORK_RE = /^eip155:[1-9][0-9]{0,9}$/;
const AMOUNT_RE = /^[1-9][0-9]{0,30}$/;
const MAX_INPUT_BYTES = 64 * 1024;

function reject(reason) {
  throw new Error(`invalid x402 challenge: ${reason}`);
}

function decode(input) {
  if (input && typeof input === 'object' && !Array.isArray(input)) return input;
  if (typeof input !== 'string') reject('expected object, JSON, or Base64 string');
  const value = input.trim();
  if (!value.length || Buffer.byteLength(value) > MAX_INPUT_BYTES) reject('input size');
  let json = value;
  if (!value.startsWith('{')) {
    if (!/^[A-Za-z0-9+/=_-]+$/.test(value)) reject('invalid Base64');
    const standard = value.replace(/-/g, '+').replace(/_/g, '/');
    try { json = Buffer.from(standard, 'base64').toString('utf8'); } catch { reject('invalid Base64'); }
  }
  if (Buffer.byteLength(json) > MAX_INPUT_BYTES) reject('decoded size');
  try { return JSON.parse(json); } catch { reject('invalid JSON'); }
}

export function inspectX402Challenge(input) {
  const body = decode(input);
  if (!body || typeof body !== 'object' || Array.isArray(body)) reject('root shape');
  if (body.x402Version !== 2) reject('version');
  if (!Array.isArray(body.accepts) || body.accepts.length < 1 || body.accepts.length > 20) {
    reject('accepts shape');
  }
  const seen = new Set();
  const accepts = body.accepts.map((requirement) => {
    if (!requirement || typeof requirement !== 'object' || Array.isArray(requirement)) reject('requirement shape');
    if (requirement.scheme !== 'exact') reject('scheme');
    if (!NETWORK_RE.test(String(requirement.network || ''))) reject('network');
    if (!AMOUNT_RE.test(String(requirement.amount || ''))) reject('amount');
    if (!ADDRESS_RE.test(String(requirement.asset || ''))) reject('asset');
    if (!ADDRESS_RE.test(String(requirement.payTo || ''))) reject('payTo');
    if (!Number.isInteger(requirement.maxTimeoutSeconds)
        || requirement.maxTimeoutSeconds < 1 || requirement.maxTimeoutSeconds > 86_400) {
      reject('timeout');
    }
    const safe = {
      scheme: requirement.scheme,
      network: requirement.network,
      amount: requirement.amount,
      asset: requirement.asset.toLowerCase(),
      payTo: requirement.payTo.toLowerCase(),
      maxTimeoutSeconds: requirement.maxTimeoutSeconds,
    };
    const key = JSON.stringify(safe);
    if (seen.has(key)) reject('duplicate requirement');
    seen.add(key);
    return safe;
  });
  return { x402Version: 2, accepts };
}
