// restore.mjs — pull remote ledger state + the wallet manifest back onto local disk (S4: "a fresh
// job restores the same agent identity, balances view, and ledgers that the previous job had").
// Uses merge.mjs's mergeAppendOnly at the RAW LINE level, never parse+re-serialize, so a
// from-empty restore reproduces the pre-destruction file's bytes exactly (see merge.mjs's header
// for why byte-fidelity matters here and how it's achieved).
//
// `targetStateDir` defaults to `stateDir` (restore-in-place — the normal "fresh job, empty
// ~/.hermes/state, pull everything down" case) but can be pointed at a different, clean directory
// — that is exactly what the S4 verification bar's round-trip proof needs: restore into a fresh
// location while the ORIGINAL (renamed-aside, never deleted) state dir still exists untouched.
//
// Idempotence: appending is keyed by merge.mjs's dedupeKeyForRow against whatever is ALREADY in
// targetStateDir — restoring twice against the same remote content always appends nothing the
// second time (never duplicates a row, never double-counts a settled cost).

import fs from "node:fs";
import path from "node:path";

import { readRawLines } from "./lines.mjs";
import { mergeAppendOnly } from "./merge.mjs";
import { LEDGER_SPECS, WALLET_MANIFEST_LOCAL_FILE_NAME, WALLET_MANIFEST_REMOTE_KEY } from "./ledger-files.mjs";
import { resolveLocalSolanaAddress } from "./wallet-manifest.mjs";
import { resolveStateDir } from "../../../spawn/lib/state-path.js";

/**
 * @param {{store: import("./store.mjs").RemoteStateStore, stateDir?: string,
 *          targetStateDir?: string, env?: Record<string,string>, home?: string,
 *          dryRun?: boolean}} opts
 */
export async function restoreState({
  store,
  stateDir = resolveStateDir(),
  targetStateDir = stateDir,
  env = process.env,
  home = env.ANICCA_HOME,
  dryRun = true,
} = {}) {
  if (!store) throw new Error("restoreState: store is required");

  const ledgerResults = [];
  for (const spec of LEDGER_SPECS) {
    const localFile = path.join(targetStateDir, spec.localFileName);
    const localLines = readRawLines(localFile);
    const remoteText = await store.getText(spec.remoteKey);
    const remoteLines = remoteText ? remoteText.split("\n").map((l) => l.trim()).filter(Boolean) : [];
    const { toAppend } = mergeAppendOnly(localLines, remoteLines);

    const result = {
      localFileName: spec.localFileName,
      remoteKey: spec.remoteKey,
      localCountBefore: localLines.length,
      remoteCount: remoteLines.length,
      appended: toAppend.length,
    };

    if (!dryRun && toAppend.length > 0) {
      fs.mkdirSync(path.dirname(localFile), { recursive: true });
      fs.appendFileSync(localFile, toAppend.join("\n") + "\n");
    }
    ledgerResults.push(result);
  }

  const manifestText = await store.getText(WALLET_MANIFEST_REMOTE_KEY);
  const remoteManifest = manifestText ? JSON.parse(manifestText) : null;
  let restoredManifestPath = null;
  if (!dryRun && manifestText) {
    restoredManifestPath = path.join(targetStateDir, WALLET_MANIFEST_LOCAL_FILE_NAME);
    fs.mkdirSync(path.dirname(restoredManifestPath), { recursive: true });
    fs.writeFileSync(restoredManifestPath, manifestText);
  }

  const locallyResolvedAddress = resolveLocalSolanaAddress({ env, home });
  const addressesMatch = Boolean(
    remoteManifest && locallyResolvedAddress && remoteManifest.solanaAddress === locallyResolvedAddress,
  );

  return { dryRun, ledgerResults, remoteManifest, locallyResolvedAddress, addressesMatch, restoredManifestPath };
}
