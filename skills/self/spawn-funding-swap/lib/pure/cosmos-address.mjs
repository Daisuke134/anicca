// spawn-funding-swap pure core — REQ-013 (sprint-2, real-clients). bech32Encode/deriveCosmosAddress:
// deterministic, no I/O (PROP-017's structural import-boundary guard) -- @noble/curves and @noble/hashes
// are pure cryptographic primitives (no fs/child_process/http/fetch), already a transitive dependency of
// viem (this feature's own package.json already depends on viem), so this adds no new dependency.
//
// WHY this exists (base-signer's real need, sprint-2): Skip API's `/v2/fungible/msgs` endpoint requires a
// real, checksummed bech32 address for EVERY Cosmos-SDK chain hop in a route's `chain_ids` (verified live
// 2026-07-11: a request omitting the noble-1/osmosis-1 intermediate addresses is rejected with "address_list
// field is missing required addresses ... [8453 noble-1 osmosis-1 akashnet-2]"). These addresses become the
// IBC-transfer `sender`/PFM `recover_address` fields for the automated multi-hop relay -- an address whose
// key we do NOT hold would make any relay-failure refund UNRECOVERABLE (real fund loss). Rather than invent
// a fresh, unbacked bech32 string, this module derives a REAL Cosmos-SDK address from the SAME EVM private
// key already resolved for Base signing, using the identical secp256k1-pubkey -> RIPEMD160(SHA256(pubkey))
// -> bech32(hrp) scheme every Cosmos SDK chain uses (the same "one key, many bech32 prefixes" technique
// wallets like Keplr rely on for EVM-compatible/secp256k1 Cosmos chains) -- so the SAME private key this
// process already controls for Base signing can also recover funds sent to these intermediate addresses.

const BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l";
const BECH32_GENERATOR = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3];

function bech32Polymod(values) {
  let chk = 1;
  for (const v of values) {
    const top = chk >> 25;
    chk = ((chk & 0x1ffffff) << 5) ^ v;
    for (let i = 0; i < 5; i++) {
      chk ^= (top >> i) & 1 ? BECH32_GENERATOR[i] : 0;
    }
  }
  return chk >>> 0;
}

function bech32HrpExpand(hrp) {
  const out = [];
  for (const ch of hrp) out.push(ch.charCodeAt(0) >> 5);
  out.push(0);
  for (const ch of hrp) out.push(ch.charCodeAt(0) & 31);
  return out;
}

function bech32CreateChecksum(hrp, data) {
  const values = bech32HrpExpand(hrp).concat(data, [0, 0, 0, 0, 0, 0]);
  const mod = bech32Polymod(values) ^ 1;
  const ret = [];
  for (let i = 0; i < 6; i++) ret.push((mod >> (5 * (5 - i))) & 31);
  return ret;
}

/**
 * bech32Encode — BIP-173 bech32 encoding (5-bit-group `data` + checksum, prefixed by `hrp`). Pure,
 * deterministic; throws on an empty/invalid hrp rather than silently producing a malformed address.
 * @param {string} hrp human-readable prefix (e.g. "noble", "osmo", "akash")
 * @param {number[]} data 5-bit groups (already converted via convertBits8to5)
 */
export function bech32Encode(hrp, data) {
  if (typeof hrp !== "string" || hrp.length === 0) throw new Error("bech32Encode: hrp must be a non-empty string");
  const checksum = bech32CreateChecksum(hrp, data);
  return hrp + "1" + data.concat(checksum).map((d) => BECH32_CHARSET[d]).join("");
}

/**
 * convertBits8to5 — repacks an array of 8-bit byte values into 5-bit groups (bech32's payload alphabet),
 * zero-padding the final group per BIP-173. Pure.
 * @param {Uint8Array | number[]} bytes
 * @returns {number[]}
 */
export function convertBits8to5(bytes) {
  let acc = 0;
  let bits = 0;
  const ret = [];
  const maxv = 31; // (1 << 5) - 1
  for (const value of bytes) {
    if (value < 0 || value > 255) throw new Error("convertBits8to5: byte out of range");
    acc = (acc << 8) | value;
    bits += 8;
    while (bits >= 5) {
      bits -= 5;
      ret.push((acc >> bits) & maxv);
    }
  }
  if (bits > 0) ret.push((acc << (5 - bits)) & maxv);
  return ret;
}

/**
 * deriveCosmosAddress — REQ-013: given a 20-byte secp256k1 pubkey-hash (RIPEMD160(SHA256(compressedPubkey)),
 * the standard Cosmos-SDK address scheme) and a chain's bech32 human-readable prefix, returns the bech32
 * address string. Pure; the actual hashing/pubkey derivation happens in the caller (real-clients/base-signer.mjs,
 * the effectful shell) so this module never itself touches key material generation, only encodes bytes
 * already provided to it.
 * @param {Uint8Array} pubkeyHash20 exactly 20 bytes
 * @param {string} hrp
 */
export function deriveCosmosAddress(pubkeyHash20, hrp) {
  if (!(pubkeyHash20 instanceof Uint8Array) || pubkeyHash20.length !== 20) {
    throw new Error("deriveCosmosAddress: pubkeyHash20 must be a 20-byte Uint8Array");
  }
  return bech32Encode(hrp, convertBits8to5(pubkeyHash20));
}
