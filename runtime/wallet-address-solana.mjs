// Prints THIS Anicca instance's Solana wallet address (base58 public key), derived in-process
// from the exact secret skills/earn/lib/resolve-identity.mjs::resolveSolanaSecret resolves for
// THIS instance's own ANICCA_HOME (REQ-001). Mirrors runtime/wallet-address.mjs's EVM CLI
// convention: derive, never bare-grep, print ONLY the derived public address to stdout.
//
// Fail-closed (REQ-001 edge cases, PROP-012): a missing/empty/unresolvable secret, or a resolved
// secret that is cryptographically malformed (invalid base58, or valid base58 decoding to the
// wrong byte length for a Solana secret key) is CAUGHT here, not left to crash the daemon — this
// prints nothing to stdout, logs a WARNING to stderr, and exits 0. The WARNING never includes the
// raw secret material (REQ-006/PROP-008): only a static, non-secret-derived message is logged.
import { Keypair } from '@solana/web3.js';
import bs58 from 'bs58';
import { resolveSolanaSecret } from '../skills/earn/lib/resolve-identity.mjs';

function warn(message) {
  process.stderr.write(`[wallet-address-solana] WARNING: ${message}\n`);
}

const secret = resolveSolanaSecret({});
if (!secret) {
  warn('no Solana secret resolved for this instance (missing/empty .solana-session or unresolvable ANICCA_HOME) — leaving ANICCA_WALLET_ADDRESS unset');
} else {
  try {
    const decoded = bs58.decode(secret);
    const keypair = Keypair.fromSecretKey(decoded);
    process.stdout.write(`${keypair.publicKey.toBase58()}\n`);
  } catch {
    // Deliberately does NOT interpolate `secret`/the caught error's message into this log line —
    // both may echo the raw malformed input back (REQ-006/PROP-008: never leak secret material).
    warn('resolved secret is not a valid Solana secret key (malformed base58 or wrong byte length) — leaving ANICCA_WALLET_ADDRESS unset');
  }
}
