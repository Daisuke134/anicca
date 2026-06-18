// Ensure every anicca (local or cloud) has a self-owned Solana wallet at
// $ANICCA_HOME/.automaton/solana.json — so people can fund it via Binance (SOL),
// and the funding daemon auto-swaps SOL->USDC. No human key, no deps (node crypto).
//
// Solana wallet = ed25519 keypair. address = base58(pubkey 32B). secret = 64B (seed||pub).

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

const home = process.env.ANICCA_HOME || process.env.HOME || '';
const file = path.join(home, '.automaton', 'solana.json');

const B58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';
function base58(buf) {
  const digits = [0];
  for (const byte of buf) {
    let carry = byte;
    for (let j = 0; j < digits.length; j++) {
      carry += digits[j] << 8;
      digits[j] = carry % 58;
      carry = (carry / 58) | 0;
    }
    while (carry) {
      digits.push(carry % 58);
      carry = (carry / 58) | 0;
    }
  }
  let out = '';
  for (const byte of buf) {
    if (byte === 0) out += '1';
    else break;
  }
  return out + digits.reverse().map((d) => B58[d]).join('');
}

if (fs.existsSync(file)) {
  const addr = JSON.parse(fs.readFileSync(file, 'utf8')).address;
  console.error('[local] Solana wallet preserved: ' + addr);
  process.exit(0);
}

const { publicKey, privateKey } = crypto.generateKeyPairSync('ed25519');
const pub = publicKey.export({ type: 'spki', format: 'der' }).subarray(-32); // last 32B = raw pubkey
const seed = privateKey.export({ type: 'pkcs8', format: 'der' }).subarray(-32); // last 32B = ed25519 seed
const secret = Buffer.concat([seed, pub]); // 64B Solana secret key
const address = base58(pub);

fs.mkdirSync(path.dirname(file), { recursive: true });
fs.writeFileSync(
  file,
  JSON.stringify({ address, secretKey: base58(secret), secretKeyBytes: [...secret] }, null, 2),
);
fs.chmodSync(file, 0o600);
console.error('[local] created self-owned Solana wallet ' + address);
