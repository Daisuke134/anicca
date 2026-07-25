// snapshot.mjs — push local ledger state + a fresh wallet manifest to the remote store (S4:
// "read/write of agent state to a durable remote store"). Every I/O boundary (the store, the
// state dir, the clock) is an injected parameter with a real default, same discipline as
// deploy.mjs/executor.mjs — `bin/citizen-state snapshot` is the thin entrypoint that calls this
// with real defaults (the real store from github-store.mjs).
//
// `--dry` (the CLI's default) computes and reports everything below WITHOUT calling
// store.putText/putTextWithMerge — i.e. without any network I/O or remote mutation.
//
// Idempotence: re-running snapshotState with nothing new locally always resolves
// `next === current` inside putTextWithMerge (merge.mjs's mergeAppendOnly returns toAppend=[] when
// there is nothing new), so the store's own no-op-skip-push path is taken — safe to run on a
// schedule.

import path from "node:path";

import { readRawLines } from "./lines.mjs";
import { mergeAppendOnly } from "./merge.mjs";
import { LEDGER_SPECS, WALLET_MANIFEST_REMOTE_KEY } from "./ledger-files.mjs";
import { buildWalletManifest } from "./wallet-manifest.mjs";
import { resolveStateDir } from "../../../spawn/lib/state-path.js";

/**
 * @param {{store: import("./store.mjs").RemoteStateStore, stateDir?: string,
 *          env?: Record<string,string>, home?: string, dryRun?: boolean}} opts
 */
export async function snapshotState({
  store,
  stateDir = resolveStateDir(),
  env = process.env,
  home = env.ANICCA_HOME,
  dryRun = true,
} = {}) {
  if (!store) throw new Error("snapshotState: store is required");

  const ledgerResults = [];
  for (const spec of LEDGER_SPECS) {
    const localFile = path.join(stateDir, spec.localFileName);
    const localLines = readRawLines(localFile);
    const remoteTextBefore = await store.getText(spec.remoteKey);
    const remoteLinesBefore = remoteTextBefore ? remoteTextBefore.split("\n").map((l) => l.trim()).filter(Boolean) : [];
    const { toAppend } = mergeAppendOnly(remoteLinesBefore, localLines);

    const result = {
      localFileName: spec.localFileName,
      remoteKey: spec.remoteKey,
      localCount: localLines.length,
      remoteCountBefore: remoteLinesBefore.length,
      addedToRemote: toAppend.length,
    };

    if (!dryRun) {
      const committedText = await store.putTextWithMerge(spec.remoteKey, (currentRemoteText) => {
        const currentRemoteLines = currentRemoteText
          ? currentRemoteText.split("\n").map((l) => l.trim()).filter(Boolean)
          : [];
        const { merged } = mergeAppendOnly(currentRemoteLines, localLines);
        return merged.length ? merged.join("\n") + "\n" : "";
      });
      result.remoteCountAfter = committedText ? committedText.split("\n").map((l) => l.trim()).filter(Boolean).length : 0;
    }
    ledgerResults.push(result);
  }

  let manifest = null;
  let manifestError = null;
  try {
    manifest = buildWalletManifest({ env, home });
    if (!dryRun) {
      await store.putText(WALLET_MANIFEST_REMOTE_KEY, JSON.stringify(manifest, null, 2) + "\n");
    }
  } catch (e) {
    manifestError = (e && e.message) || String(e);
  }

  return { dryRun, ledgerResults, manifest, manifestError };
}
