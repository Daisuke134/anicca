// proof.mjs — the container's economic proof-of-life (S7, zero-secret redesign): an EPHEMERAL
// keypair generated inside the container (never funded, never a secret worth protecting) signs a
// message binding a live Solana blockhash + Franklin's own real, publicly-read treasury balance
// and recomputed runway. This is the evidence channel this feature relies on — NOT the exposed
// HTTP endpoint (documented dead in every attempt so far across two different nodes: always 503,
// "x-frp-service-state: loading" — see ../job-definition.mjs's incident header and
// tenant/README.md), and NOT an x402 paid-inference call or a funded/custodied identity (rejected
// by design in this second pass: a container whose job definition is published to public IPFS
// forever cannot safely hold a spending key — see tenant/README.md's "Trust boundary" section for
// the live-verified evidence and the delegated-spend alternative considered for later).
//
// Why a signed, runtime-bound challenge is still convincing even with an unfunded ephemeral key:
// a blockhash is public and unpredictable in advance (Solana produces a new one roughly every
// 400ms, each valid for only a couple of minutes), so a signature over {THIS ephemeral address,
// THIS blockhash, THIS treasury balance, THIS recomputed runway, THIS timestamp} could only have
// been produced by code that (a) generated a fresh keypair, (b) queried a live RPC + the public
// jobs API at approximately the reported timestamp, and (c) actually did the runway arithmetic —
// none of which could be faked by something running outside the job, before the job existed, or
// by a job whose container never actually executed the described steps. What it does NOT prove is
// custody of any funded identity — see tenant/README.md for the explicit claim boundary.
//
// Deliberately self-contained (zero relative imports outside this directory) so it can be bundled
// by tenant/build-bundle.mjs alongside public-job-state.mjs and the real, reused
// ../renew/survival-drive.mjs without pulling in anything that touches a secret.

/**
 * Pure: the exact message the container signs. A fixed field order and explicit `|`-joined format
 * (never JSON.stringify of an object — object key order is not something a verifier should have to
 * depend on) so any outside verifier can reconstruct byte-for-byte the same message from the
 * reported fields and independently check the signature with only tweetnacl + the reported
 * ephemeral public address — no code from this repo required to verify.
 *
 * @param {{ephemeralAddress: string, blockhash: string, treasuryAddress: string,
 *          treasurySolLamports: number, treasuryNosBalance: number, nosPerHour: number|null,
 *          runwayHours: number|null, rateSource: string, ts: number}} opts
 * @returns {string}
 */
export function buildChallengeMessage({
  ephemeralAddress,
  blockhash,
  treasuryAddress,
  treasurySolLamports,
  treasuryNosBalance,
  nosPerHour,
  runwayHours,
  rateSource,
  ts,
}) {
  for (const [key, value] of Object.entries({ ephemeralAddress, blockhash, treasuryAddress, rateSource })) {
    if (typeof value !== "string" || value.length === 0) {
      throw new Error(`buildChallengeMessage: ${key} must be a non-empty string`);
    }
  }
  for (const [key, value] of Object.entries({ treasurySolLamports, treasuryNosBalance, ts })) {
    if (typeof value !== "number" || !Number.isFinite(value)) {
      throw new Error(`buildChallengeMessage: ${key} must be a finite number`);
    }
  }
  for (const [key, value] of Object.entries({ nosPerHour, runwayHours })) {
    if (value !== null && (typeof value !== "number" || !Number.isFinite(value))) {
      throw new Error(`buildChallengeMessage: ${key} must be a finite number or null`);
    }
  }
  const nosPerHourStr = nosPerHour === null ? "null" : String(nosPerHour);
  const runwayHoursStr = runwayHours === null ? "null" : String(runwayHours);
  return (
    `nosana-tenant-proof-of-life-v2|ephemeralAddress=${ephemeralAddress}|blockhash=${blockhash}|` +
    `treasuryAddress=${treasuryAddress}|treasurySolLamports=${treasurySolLamports}|` +
    `treasuryNosBalance=${treasuryNosBalance}|nosPerHour=${nosPerHourStr}|runwayHours=${runwayHoursStr}|` +
    `rateSource=${rateSource}|ts=${ts}`
  );
}

/**
 * Sign `message` (UTF-8) with an ephemeral keypair's raw ed25519 secret key bytes. `signImpl`
 * defaults to tweetnacl's `nacl.sign.detached` — injected so most tests never need real key
 * material to exercise the plumbing, though __tests__/proof.test.mjs ALSO runs this against a
 * real generated keypair and the real tweetnacl verify function, to prove the sign/verify round
 * trip genuinely works — not just that a function was called.
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
 * really verifies against the claimed ephemeral address.
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
