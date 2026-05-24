import fs from 'node:fs';
import path from 'node:path';

export function repoDir() {
  return path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
}

export function readJson(filePath) {
  const raw = fs.readFileSync(filePath, 'utf8');
  return JSON.parse(raw);
}

export function writeJson(filePath, value) {
  fs.writeFileSync(filePath, JSON.stringify(value, null, 2) + '\n', 'utf8');
}

export function normalizeHexAddress(addr) {
  if (typeof addr !== 'string') throw new Error('address must be a string');
  const a = addr.trim();
  if (!/^0x[0-9a-fA-F]{40}$/.test(a)) throw new Error(`invalid address: ${addr}`);
  return '0x' + a.slice(2).toLowerCase();
}

export function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    const v = argv[i];
    if (!v.startsWith('--')) continue;
    const key = v.slice(2);
    const next = argv[i + 1];
    if (next && !next.startsWith('--')) {
      out[key] = next;
      i++;
    } else {
      out[key] = true;
    }
  }
  return out;
}

export function parseUsdcAmountToBaseUnits(amountStr, decimals = 6) {
  // decimal string -> BigInt base units
  if (typeof amountStr !== 'string') throw new Error('amount must be a string');
  const s = amountStr.trim();
  if (!/^[0-9]+(\.[0-9]+)?$/.test(s)) throw new Error(`invalid amount: ${amountStr}`);
  const [whole, frac = ''] = s.split('.');
  const fracPadded = (frac + '0'.repeat(decimals)).slice(0, decimals);
  const base = BigInt(whole) * (10n ** BigInt(decimals)) + BigInt(fracPadded || '0');
  return base;
}

export function padTopicAddress(addr) {
  // addr is normalized 0x + 40 hex; topic is 32 bytes
  return '0x' + '0'.repeat(24 * 2) + addr.slice(2);
}

export function topicToAddress(topic) {
  if (typeof topic !== 'string' || !/^0x[0-9a-fA-F]{64}$/.test(topic)) return null;
  return '0x' + topic.slice(26 * 2).toLowerCase();
}

