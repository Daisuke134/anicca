// proof.mjs — the tenant's economic proof-of-life: a real balance read plus a signature the
// tenant identity produces AT RUNTIME over data (a Solana blockhash fetched at the moment the job
// runs) that could not have been known before the job started. This is the evidence channel this
// feature relies on — NOT the exposed HTTP endpoint (documented dead in every attempt so far
// across two different nodes: always 503, "x-frp-service-state: loading" — see
// ../job-definition.mjs's incident header and tenant/README.md), and NOT an x402 paid-inference
// call (not exercised this pass: the tenant wallet was never funded by this executor — see
// tenant/README.md's "What was NOT executed" section for why).
//
// Why a signed, runtime-bound challenge is convincing: a blockhash is public and unpredictable in
// advance (Solana produces a new one roughly every 400ms and each one is only valid for a couple of
// minutes), so a signature over {address, THIS blockhash, THIS balance, THIS run number, THIS
// timestamp} could only have been produced by code that (a) held the tenant's private key and
// (b) actually queried a live RPC endpoint at approximately the reported timestamp — neither fact
// could be faked by something running outside the job, before the job existed, or by a job whose
// container never actually executed the described steps.
//
// Deliberately self-contained (see derive-address.mjs's header for why tenant/'s in-job code never
// reaches outside this directory).

/**
 * Pure: the exact message the tenant signs. A fixed field order and explicit `|`-joined format
 * (never JSON.stringify of an object — object key order is not something a verifier should have to
 * depend on) so any outside verifier can reconstruct byte-for-byte the same message from the
 * reported fields and independently check the signature with only tweetnacl + the reported public
 * address — no code from this repo required to verify.
 *
 * @param {{address: string, blockhash: string, solLamports: number, nosBalance: number,
 *          runNumber: number, ts: number}} opts
 * @returns {string}
 */
export function buildChallengeMessage({ address, blockhash, solLamports, nosBalance, runNumber, ts }) {
  for (const [key, value] of Object.entries({ address, blockhash })) {
    if (typeof value !== "string" || value.length === 0) {
      throw new Error(`buildChallengeMessage: ${key} must be a non-empty string`);
    }
  }
  for (const [key, value] of Object.entries({ solLamports, nosBalance, runNumber, ts })) {
    if (typeof value !== "number" || !Number.isFinite(value)) {
      throw new Error(`buildChallengeMessage: ${key} must be a finite number`);
    }
  }
  return `nosana-tenant-proof-of-life|address=${address}|blockhash=${blockhash}|solLamports=${solLamports}|nosBalance=${nosBalance}|runNumber=${runNumber}|ts=${ts}`;
}

/**
 * Sign `message` (UTF-8) with the tenant's raw ed25519 secret key bytes (the same 64-byte layout
 * derive-address.mjs's deriveAddressFromSecret decodes). `signImpl` defaults to tweetnacl's
 * `nacl.sign.detached` — injected so most tests never need real key material to exercise the
 * plumbing, though __tests__/proof.test.mjs ALSO runs this against a real generated keypair and the
 * real tweetnacl verify function, to prove the sign/verify round trip genuinely works — not just
 * that a function was called.
 *
 * @param {{message: string, secretKeyBytes: Uint8Array, signImpl?: Function}} opts
 * @returns {Promise<Uint8Array>}
 */
export async function signChallenge({ message, secretKeyBytes, signImpl }) {
  if (typeof message !== "string" || message.length === 0) {
    throw new Error("signChallenge: message is required");
  }
  if (!(secretKeyBytes instanceof Uint8Array) || secretKeyBytes.length !== 64) {
    throw new Error("signChallenge: secretKeyBytes must be a 64-byte Uint8Array");
  }
  const sign = signImpl || (await import("tweetnacl")).default.sign.detached;
  const messageBytes = new TextEncoder().encode(message);
  return sign(messageBytes, secretKeyBytes);
}

/**
 * Verify a reported {message, signature, publicKey} triple. Exists so tests (and any outside
 * auditor, with just this one function plus tweetnacl) can prove the signature over the message
 * really verifies against the claimed tenant address.
 *
 * @param {{message: string, signatureBytes: Uint8Array, publicKeyBytes: Uint8Array, verifyImpl?: Function}} opts
 * @returns {Promise<boolean>}
 */
export async function verifyChallengeSignature({ message, signatureBytes, publicKeyBytes, verifyImpl }) {
  if (typeof message !== "string" || message.length === 0) {
    throw new Error("verifyChallengeSignature: message is required");
  }
  const verify = verifyImpl || (await import("tweetnacl")).default.sign.detached.verify;
  const messageBytes = new TextEncoder().encode(message);
  return Boolean(verify(messageBytes, signatureBytes, publicKeyBytes));
}

/**
 * Pure, informational only (never gates a decision — contrast ../renew/cost.mjs's stricter
 * fail-closed style, which decides real spend): hours of runway a NOS balance buys at a given burn
 * rate. Returns null (not a throw) when the rate is unknown/non-positive — an informational report
 * field being "unknown" is honest; a spend gate treating "unknown" as "zero cost, proceed" would
 * not be, which is why this is intentionally NOT reused as a gate anywhere.
 *
 * @param {{nosBalance: number, nosPerHourBurnRate: number|null|undefined}} opts
 * @returns {number|null}
 */
export function computeRunwayHoursInformational({ nosBalance, nosPerHourBurnRate }) {
  if (typeof nosBalance !== "number" || !Number.isFinite(nosBalance) || nosBalance < 0) return null;
  if (typeof nosPerHourBurnRate !== "number" || !Number.isFinite(nosPerHourBurnRate) || nosPerHourBurnRate <= 0) return null;
  return nosBalance / nosPerHourBurnRate;
}
