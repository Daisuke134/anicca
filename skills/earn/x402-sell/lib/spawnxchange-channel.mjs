import { parseSiweMessage } from 'viem/siwe';

const ADDRESS_RE = /^0x[0-9a-fA-F]{40}$/;

function reject(reason) {
  throw new Error(`SpawnXchange challenge rejected: ${reason}`);
}

export function validateSpawnxchangeChallenge({ message, expectedAddress, nowMs = Date.now() }) {
  if (typeof message !== 'string' || !message.length || message.length > 4096) reject('invalid message');
  if (!ADDRESS_RE.test(String(expectedAddress || ''))) reject('invalid expected address');
  if (!Number.isFinite(nowMs)) reject('invalid clock');
  let parsed;
  try { parsed = parseSiweMessage(message); } catch { reject('invalid SIWE'); }
  if (parsed.domain !== 'spawnxchange.com') reject('domain drift');
  if (String(parsed.address || '').toLowerCase() !== expectedAddress.toLowerCase()) reject('address drift');
  if (parsed.uri !== 'https://spawnxchange.com') reject('URI drift');
  if (parsed.version !== '1') reject('version drift');
  if (parsed.chainId !== 8453) reject('chain drift');
  if (parsed.statement !== 'Register on SpawnXchange') reject('statement drift');
  if (!/^[A-Za-z0-9]{8,}$/.test(String(parsed.nonce || ''))) reject('invalid nonce');

  const issuedAt = new Date(parsed.issuedAt).getTime();
  const expiration = new Date(parsed.expirationTime).getTime();
  if (!Number.isFinite(issuedAt) || issuedAt < nowMs - 60_000 || issuedAt > nowMs + 30_000) {
    reject('issued-at drift');
  }
  if (!Number.isFinite(expiration) || expiration <= nowMs || expiration > issuedAt + 10 * 60_000) {
    reject('expiration drift');
  }

  return {
    domain: parsed.domain,
    address: parsed.address.toLowerCase(),
    chainId: parsed.chainId,
    expirationTime: new Date(expiration).toISOString(),
  };
}
