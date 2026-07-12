/**
 * wallets.mjs — ONE file tells an instance every wallet it owns.
 *
 * Why this exists (2026-07-12, measured): the truth about an instance's wallets was scattered
 * across four places — ANICCA_WALLET_ADDRESS (one address), an ANICCA_EXTRA_WALLETS JSON blob
 * hand-written into a plist, a constant hardcoded inside redeem.py, and docs/WALLETS.md for
 * humans. Nothing reconciled them. The loop therefore believed claude-p held $1.95 when it
 * actually held $18: its Polymarket deposit wallet was invisible to every reader. Believing it
 * was broke, it hid its own earning skills from itself and picked `narrate` 235 of 300 wakes.
 *
 * The fix is the one every serious registry uses: a single declarative manifest that every
 * component reads, and nothing else. Same shape as hyperlane-registry's per-chain addresses.yaml.
 * The anti-pattern we are leaving behind is real and shipping elsewhere too — elizaOS's
 * plugin-polymarket resolves ONE wallet through a four-deep env fallback chain
 * (POLYMARKET_WALLET_ADDRESS -> POLYMARKET_ADDRESS -> STEWARD_EVM_ADDRESS -> ELIZA_MANAGED_...).
 * See docs/loop-engineering/35-wallet-manifest-bp.md for the sources.
 *
 * PUBLIC ADDRESSES ONLY. A private key never appears in the manifest — only a `keyRef` naming
 * where the key lives ("env:FOO", "file:~/x/wallet.json"). Turnkey/MetaMask state the rule
 * plainly: "The agent never touches the private key. It receives signatures, not keys."
 *
 * Location: $ANICCA_HOME/wallets.json — one file per instance, so an instance can only ever
 * read its own wallets, and a new instance declares itself by writing one file.
 */
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

/** Chains we know how to read a balance from (net-worth.mjs). */
export const KNOWN_CHAINS = ['base', 'polygon', 'solana', 'hyperliquid', 'arbitrum', 'ethereum'];

/**
 * Pure: validate + normalize a manifest object into the wallet list the rest of the system uses.
 * Unknown chains and malformed rows are dropped (fail-closed on the row, not on the file — one
 * bad row must never blind an instance to the wallets it CAN read).
 *
 * @param {unknown} raw - parsed wallets.json
 * @returns {{ instance: string|null, wallets: Array<{id:string,chain:string,venue:string,address:string,label:string,keyRef:string|null}> }}
 */
export function parseWalletManifest(raw) {
  const empty = { instance: null, wallets: [] };
  if (!raw || typeof raw !== 'object') return empty;
  const list = Array.isArray(raw.wallets) ? raw.wallets : [];
  const wallets = [];
  for (const w of list) {
    if (!w || typeof w !== 'object') continue;
    const chain = String(w.chain || '').toLowerCase();
    const address = String(w.address || '').trim();
    if (!chain || !address) continue;
    if (!KNOWN_CHAINS.includes(chain)) continue;
    // A key must never be inlined. If someone pastes one in, drop it rather than propagate it.
    if (typeof w.privateKey === 'string' || typeof w.secretKey === 'string') continue;
    wallets.push({
      id: String(w.id || `${chain}-${address.slice(0, 8)}`),
      chain,
      venue: String(w.venue || chain).toLowerCase(),
      address,
      label: String(w.label || w.id || chain),
      keyRef: typeof w.keyRef === 'string' ? w.keyRef : null,
    });
  }
  return {
    instance: typeof raw.instance === 'string' ? raw.instance : null,
    wallets,
  };
}

/**
 * Effectful: read $ANICCA_HOME/wallets.json. Returns an empty manifest when absent or unreadable —
 * callers fall back to their previous behaviour, so adding this file can only ever ADD sight.
 *
 * @param {string} aniccaHome
 * @param {(p: string) => string} [readFileImpl] - injectable for tests (no fs in unit tests)
 */
export function loadWalletManifest(aniccaHome, readFileImpl) {
  if (!aniccaHome) return { instance: null, wallets: [] };
  const read = readFileImpl || ((p) => readFileSync(p, 'utf8'));
  try {
    return parseWalletManifest(JSON.parse(read(join(aniccaHome, 'wallets.json'))));
  } catch {
    return { instance: null, wallets: [] };
  }
}

/**
 * Pure: the wallets a given venue can actually spend from.
 * `venue` is what a skill knows about itself ("polymarket", "solana", "hyperliquid") — the whole
 * point is that a skill asks "which of MY wallets can I spend at MY venue" instead of every
 * component re-deriving that answer from a different env var.
 */
export function walletsForVenue(manifest, venue) {
  const v = String(venue || '').toLowerCase();
  return (manifest?.wallets || []).filter((w) => w.venue === v);
}

/** Pure: the single address a venue spends from, or null. */
export function addressForVenue(manifest, venue) {
  const hits = walletsForVenue(manifest, venue);
  return hits.length > 0 ? hits[0].address : null;
}
