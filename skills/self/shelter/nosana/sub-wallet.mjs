// sub-wallet.mjs — the S8 on-chain spend cap. Research-verified (2026-07-26, primary sources:
// nosana-ci/nosana-programs list.rs + solana-program/token processor.rs): the nosana-jobs `list`
// instruction constrains the NOS source to the PAYER'S OWN ATA, so SPL Approve delegation cannot
// cap a cloud key's spending. The cap is therefore the balance itself: a dedicated sub-wallet is
// funded with at most `nosCap` NOS + `solCap` SOL, and ONLY its secret ships to the cloud
// (S12). A leaked cloud key loses at most the cap — and unlike delegation, the SOL fee budget is
// capped too.
//
// This module deliberately generates a NEW keypair — the sanctioned exception to the repo's
// "never a new wallet" rule, because the entire point is that Franklin's canonical secret never
// leaves the Mac. The sub-wallet key is created once and then loaded forever after (never
// silently rotated: the cloud identity must stay stable across funding rounds).
//
// Money-safety (constraint 6, same as keypair.mjs): never logs or embeds secret material in
// errors. Funding movements are appended to nosana-subwallet-funding.jsonl before + after send
// (intent/settled), mirroring deploy.mjs's at-most-once ledger discipline.

import fs from "node:fs";
import path from "node:path";
import bs58 from "bs58";
import nacl from "tweetnacl";

import { NOS_MINT } from "./market.mjs";
import { DEFAULT_RPC_URL } from "./deploy.mjs";
import { DEFAULT_SOL_FEE_FLOOR } from "./spend-gate.mjs";
import { appendChild } from "../../spawn/lib/ledger.js";
import { resolveStateDir } from "../../spawn/lib/state-path.js";

// One current fixed market escrow (48 microunits/s × 7200s = 0.3456 NOS) plus the
// 0.34 NOS move-out reserve requires 0.6856 NOS before a safe post. 0.75 keeps
// a small rate-change margin while retaining a tightly bounded cloud-key exposure.
export const DEFAULT_NOS_CAP = 0.75;
export const DEFAULT_SOL_CAP = 0.005; // fee + rent budget for the cloud key
export const DEFAULT_USDC_CAP = 0.03; // BlockRun x402 budget (~2 gpt-5-mini calls at $0.011 each)
export const USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v";
export const SUBWALLET_FUNDING_LEDGER_BASENAME = "nosana-subwallet-funding.jsonl";

function isPositiveFinite(v) {
  return typeof v === "number" && Number.isFinite(v) && v > 0;
}

/**
 * Pure: should this funding request be allowed? Fail-closed on anything malformed. The cap is
 * checked against the sub-wallet's balance AFTER funding (existing balance counts toward the
 * cap), and the owner must keep its own SOL fee floor and enough NOS to send.
 */
export function evaluateFundingGate({
  requestNos,
  requestSol,
  requestUsdc,
  subNosBalance = 0,
  subSolBalance = 0,
  subUsdcBalance = 0,
  ownerNosBalance = 0,
  ownerSolBalance = 0,
  ownerUsdcBalance = 0,
  config = {},
} = {}) {
  const nosCap = config.nosCap ?? DEFAULT_NOS_CAP;
  const solCap = config.solCap ?? DEFAULT_SOL_CAP;
  const usdcCap = config.usdcCap ?? DEFAULT_USDC_CAP;
  const solFloor = config.solFeeFloor ?? DEFAULT_SOL_FEE_FLOOR;

  if (!isPositiveFinite(requestNos) && !isPositiveFinite(requestSol) && !isPositiveFinite(requestUsdc)) {
    return { allowed: false, reason: "nothing to fund: requestNos/requestSol/requestUsdc must include a positive finite amount" };
  }
  if (requestNos !== undefined && requestNos !== 0 && !isPositiveFinite(requestNos)) {
    return { allowed: false, reason: "requestNos must be a positive finite number (or 0 to skip the NOS leg)" };
  }
  if (requestSol !== undefined && requestSol !== 0 && !isPositiveFinite(requestSol)) {
    return { allowed: false, reason: "requestSol must be a positive finite number (or 0 to skip the SOL leg)" };
  }
  if (requestUsdc !== undefined && requestUsdc !== 0 && !isPositiveFinite(requestUsdc)) {
    return { allowed: false, reason: "requestUsdc must be a positive finite number (or 0 to skip the USDC leg)" };
  }
  const nos = isPositiveFinite(requestNos) ? requestNos : 0;
  const sol = isPositiveFinite(requestSol) ? requestSol : 0;
  const usdc = isPositiveFinite(requestUsdc) ? requestUsdc : 0;

  // A cap limits what we PUT IN. Checking a balance we are not adding to turns an unrelated
  // over-cap holding into a permanent freeze on every other asset — measured 2026-07-27: the
  // sub-wallet sat at 0.026 SOL against a 0.005 cap purely from Nosana escrow REFUNDS (nobody sent
  // it), and that blocked a NOS-only top-up, leaving the agent unable to pay rent while the SOL it
  // was being punished for sat there doing nothing. Refusing the NOS did not reduce the SOL
  // exposure by one lamport. So each cap is checked only for the asset actually being funded.
  if (nos > 0 && subNosBalance + nos > nosCap) {
    return {
      allowed: false,
      reason: `sub-wallet would hold ${(subNosBalance + nos).toFixed(6)} NOS, exceeding the NOS cap ${nosCap} — the cap IS the security boundary, refusing`,
    };
  }
  if (sol > 0 && subSolBalance + sol > solCap) {
    return {
      allowed: false,
      reason: `sub-wallet would hold ${(subSolBalance + sol).toFixed(6)} SOL, exceeding the SOL cap ${solCap} — refusing`,
    };
  }
  if (usdc > 0 && subUsdcBalance + usdc > usdcCap) {
    return {
      allowed: false,
      reason: `sub-wallet would hold ${(subUsdcBalance + usdc).toFixed(6)} USDC, exceeding the USDC cap ${usdcCap} — refusing`,
    };
  }
  if (ownerNosBalance < nos) {
    return { allowed: false, reason: `owner holds ${ownerNosBalance} NOS, cannot send ${nos}` };
  }
  if (ownerUsdcBalance < usdc) {
    return { allowed: false, reason: `owner holds ${ownerUsdcBalance} USDC, cannot send ${usdc}` };
  }
  if (ownerSolBalance - sol < solFloor) {
    return {
      allowed: false,
      reason: `owner SOL would drop to ${(ownerSolBalance - sol).toFixed(6)}, below the fee floor ${solFloor}`,
    };
  }
  // An asset can sit over its cap without this transfer causing it (refunds do this). Say so —
  // allowing the funding is right, hiding the breach is not.
  const overCap = [];
  if (subNosBalance > nosCap) overCap.push(`NOS ${subNosBalance.toFixed(6)} > ${nosCap}`);
  if (subSolBalance > solCap) overCap.push(`SOL ${subSolBalance.toFixed(6)} > ${solCap}`);
  if (subUsdcBalance > usdcCap) overCap.push(`USDC ${subUsdcBalance.toFixed(6)} > ${usdcCap}`);
  return {
    allowed: true,
    reason: "within sub-wallet caps and owner floors",
    nos,
    sol,
    usdc,
    ...(overCap.length ? { warning: `already over cap, not caused by this transfer: ${overCap.join("; ")}` } : {}),
  };
}

/**
 * Write the sub-wallet secret as the standard 64-byte JSON-array keypair file, 0600 in a 0700
 * dir (same discipline as keypair.mjs's materializeKeypairFile — duplicated deliberately: that
 * function is documented as Franklin's OWN identity materializer and this one must never be
 * confused with it).
 */
export function materializeSubWalletFile({ secretBytes, subWalletPath }) {
  if (!(secretBytes && secretBytes.length === 64)) {
    throw new Error("materializeSubWalletFile: secretBytes must be 64 bytes");
  }
  if (typeof subWalletPath !== "string" || subWalletPath.length === 0) {
    throw new Error("materializeSubWalletFile: subWalletPath is required");
  }
  const dir = path.dirname(subWalletPath);
  fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
  fs.chmodSync(dir, 0o700);
  fs.writeFileSync(subWalletPath, JSON.stringify(Array.from(secretBytes)), { mode: 0o600 });
  fs.chmodSync(subWalletPath, 0o600);
  return subWalletPath;
}

/**
 * Load-or-create the sub-wallet at $ANICCA_HOME/.automaton/nosana_subwallet_key.json. Created
 * exactly once; afterwards ALWAYS loads the same key (the cloud identity must not silently
 * rotate — a rotation would orphan the funded balance). Returns {address, keypairPath, created}.
 */
export function ensureSubWallet({ env = process.env, home } = {}) {
  const effectiveHome = home ?? env.ANICCA_HOME;
  if (!effectiveHome) {
    throw new Error("ensureSubWallet: ANICCA_HOME (or an explicit home) is required");
  }
  const keypairPath = path.join(effectiveHome, ".automaton", "nosana_subwallet_key.json");
  if (fs.existsSync(keypairPath)) {
    let secretBytes;
    try {
      secretBytes = Uint8Array.from(JSON.parse(fs.readFileSync(keypairPath, "utf8")));
    } catch {
      throw new Error("ensureSubWallet: existing sub-wallet file is unreadable or not a JSON byte array — refusing to overwrite; inspect it manually");
    }
    if (secretBytes.length !== 64) {
      throw new Error("ensureSubWallet: existing sub-wallet file is malformed (not 64 bytes) — refusing to overwrite; inspect it manually");
    }
    const address = bs58.encode(secretBytes.subarray(32));
    return { address, keypairPath, created: false };
  }
  const kp = nacl.sign.keyPair();
  materializeSubWalletFile({ secretBytes: kp.secretKey, subWalletPath: keypairPath });
  return { address: bs58.encode(kp.publicKey), keypairPath, created: true };
}

/**
 * Known-accepted TOCTOU: balances are read, gated, then sent in separate steps — a concurrent
 * funder could push the sub-wallet past cap between read and send. Accepted because this repo is
 * the single funding path (one operator, one ledger) and every movement is journaled; revisit if
 * funding ever becomes multi-process.
 *
 * Live funding: gate on REAL balances, then move SOL (SystemProgram.transfer) and NOS (SPL
 * transfer, creating the sub ATA if needed) from Franklin's wallet to the sub-wallet. Records
 * intent BEFORE sending and settled rows (with tx signatures) after confirmation — at-most-once
 * discipline mirrors deploy.mjs. Dry by default: pass live:true to actually send.
 *
 * All I/O injectable for tests; real defaults for production.
 */
export async function fundSubWallet({
  env = process.env,
  live = false,
  requestNos,
  requestSol,
  requestUsdc,
  rpcUrl = env.NOSANA_RPC_URL || env.SOLANA_RPC_URL || DEFAULT_RPC_URL,
  config = {},
  web3 = null,
  splToken = null,
  connection = null,
  ownerKeypair = null,
  appendImpl = null,
  now = () => Date.now(),
  log = (line) => process.stdout.write(`[citizen-subwallet] ${line}\n`),
} = {}) {
  const w3 = web3 || (await import("@solana/web3.js"));
  const spl = splToken || (await import("@solana/spl-token"));

  // Identities: Franklin's own key (owner, from the canonical resolver via keypair.mjs) and the
  // load-or-create sub-wallet.
  const { ensureNosanaKeypair } = await import("./keypair.mjs");
  const owner = ownerKeypair
    ? ownerKeypair
    : w3.Keypair.fromSecretKey(Uint8Array.from(JSON.parse(fs.readFileSync(ensureNosanaKeypair({ env }).keypairPath, "utf8"))));
  const sub = ensureSubWallet({ env });
  log(`owner ${owner.publicKey.toBase58()} -> sub-wallet ${sub.address}${sub.created ? " (created)" : ""}`);

  const conn = connection || new w3.Connection(rpcUrl, "confirmed");
  const nosMint = new w3.PublicKey(NOS_MINT);
  const usdcMint = new w3.PublicKey(USDC_MINT);
  const subPub = new w3.PublicKey(sub.address);

  // Real balances for the gate.
  const ownerSol = (await conn.getBalance(owner.publicKey)) / w3.LAMPORTS_PER_SOL;
  const subSol = (await conn.getBalance(subPub)) / w3.LAMPORTS_PER_SOL;
  async function tokenBalanceOf(ownerPub, mint) {
    const resp = await conn.getParsedTokenAccountsByOwner(ownerPub, { mint });
    if (!resp || !Array.isArray(resp.value) || resp.value.length === 0) return 0;
    const amount = resp.value[0].account.data.parsed.info.tokenAmount.uiAmount;
    return typeof amount === "number" ? amount : 0;
  }
  const ownerNos = await tokenBalanceOf(owner.publicKey, nosMint);
  const subNos = await tokenBalanceOf(subPub, nosMint);
  const ownerUsdc = await tokenBalanceOf(owner.publicKey, usdcMint);
  const subUsdc = await tokenBalanceOf(subPub, usdcMint);
  log(`balances: owner ${ownerSol} SOL / ${ownerNos} NOS, sub ${subSol} SOL / ${subNos} NOS`);

  const gate = evaluateFundingGate({
    requestNos,
    requestSol,
    requestUsdc,
    subNosBalance: subNos,
    subSolBalance: subSol,
    subUsdcBalance: subUsdc,
    ownerNosBalance: ownerNos,
    ownerSolBalance: ownerSol,
    ownerUsdcBalance: ownerUsdc,
    config: {
      nosCap: Number(env.NOSANA_SUBWALLET_NOS_CAP || config.nosCap || DEFAULT_NOS_CAP),
      solCap: Number(env.NOSANA_SUBWALLET_SOL_CAP || config.solCap || DEFAULT_SOL_CAP),
      usdcCap: Number(env.NOSANA_SUBWALLET_USDC_CAP || config.usdcCap || DEFAULT_USDC_CAP),
      solFeeFloor: config.solFeeFloor,
    },
  });
  log(`funding gate: ${gate.allowed ? "ALLOWED" : "REFUSED"} — ${gate.reason}`);

  // `ok` mirrors `sent` so a caller reading the common field cannot mistake a completed transfer
  // for a failure. A money rail whose success field is unguessable is a double-spend waiting for a
  // retry loop — measured 2026-07-27: tx aYGEcC5k moved 0.473 NOS and the caller reported "failed".
  const result = { owner: owner.publicKey.toBase58(), sub: sub.address, gate, sent: false, ok: false, signatures: {} };
  if (!gate.allowed) return result;
  if (!live) {
    log(`(dry) would send ${gate.sol} SOL + ${gate.nos} NOS + ${gate.usdc} USDC to ${sub.address}. Stopping before any transfer.`);
    return result;
  }

  const append =
    appendImpl || ((entry) => appendChild(path.join(resolveStateDir({ env }), SUBWALLET_FUNDING_LEDGER_BASENAME), entry));
  const ts = now() / 1000;
  append({ kind: "subwallet-funding", status: "intent", ts, from: result.owner, to: sub.address, nos: gate.nos, sol: gate.sol, usdc: gate.usdc });

  if (gate.sol > 0) {
    const tx = new w3.Transaction().add(
      w3.SystemProgram.transfer({
        fromPubkey: owner.publicKey,
        toPubkey: subPub,
        lamports: Math.round(gate.sol * w3.LAMPORTS_PER_SOL),
      }),
    );
    const sig = await w3.sendAndConfirmTransaction(conn, tx, [owner]);
    result.signatures.sol = sig;
    log(`SOL leg confirmed: ${sig}`);
  }
  if (gate.nos > 0) {
    const ownerAta = await spl.getOrCreateAssociatedTokenAccount(conn, owner, nosMint, owner.publicKey);
    const subAta = await spl.getOrCreateAssociatedTokenAccount(conn, owner, nosMint, subPub);
    // NOS has 6 decimals (uiAmount observed live: 2.452925 over raw ledger units).
    const raw = BigInt(Math.round(gate.nos * 1_000_000));
    const sig = await spl.transfer(conn, owner, ownerAta.address, subAta.address, owner, raw);
    result.signatures.nos = sig;
    log(`NOS leg confirmed: ${sig}`);
  }
  if (gate.usdc > 0) {
    const ownerAta = await spl.getOrCreateAssociatedTokenAccount(conn, owner, usdcMint, owner.publicKey);
    const subAta = await spl.getOrCreateAssociatedTokenAccount(conn, owner, usdcMint, subPub);
    // USDC has 6 decimals.
    const raw = BigInt(Math.round(gate.usdc * 1_000_000));
    const sig = await spl.transfer(conn, owner, ownerAta.address, subAta.address, owner, raw);
    result.signatures.usdc = sig;
    log(`USDC leg confirmed: ${sig}`);
  }

  append({ kind: "subwallet-funding", status: "settled", ts: now() / 1000, from: result.owner, to: sub.address, nos: gate.nos, sol: gate.sol, usdc: gate.usdc, signatures: result.signatures });
  result.sent = true;
  result.ok = true;
  return result;
}
