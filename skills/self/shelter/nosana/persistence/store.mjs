// store.mjs — the RemoteStateStore interface (S4), plus the ONE test-double implementation.
//
// Interface (duck-typed, no class — matches this repo's plain-function style throughout
// skills/self/shelter/nosana/):
//   getText(key)                    -> Promise<string|null>  // null = object does not exist yet
//   putText(key, text)              -> Promise<void>         // unconditional overwrite
//   putTextWithMerge(key, mergeFn)  -> Promise<string>        // optimistic-concurrency write;
//     mergeFn(currentRemoteTextOrNull) -> Promise<string>|string is invoked with the FRESHEST
//     remote text available and must return the full text to commit. Implementations that can
//     race (a real remote) MUST re-invoke mergeFn with newly-fetched text on any detected race —
//     never resolve a race by silently keeping only one side's write (spec: "do not silently pick
//     one side"). Implementations that cannot race (this file's local one; a single process) may
//     just call it once.
//   close()                         -> Promise<void>          // optional; best-effort cleanup.
//
// This file holds ONLY the injectable local-filesystem double used by every unit test in this
// directory (and by any caller that wants zero network I/O). The one REAL implementation lives in
// ./github-store.mjs — see that file's header for why a private git repo (not S3/IPFS) is what is
// actually wired, and bin/citizen-state for how it is selected by default.
//
// Row-level merge/dedupe decisions never happen here — see merge.mjs. This file only moves bytes
// in and out of a key/value-shaped remote.

import fs from "node:fs";
import path from "node:path";

function resolvePath(rootDir, key) {
  if (typeof key !== "string" || key.length === 0 || key.includes("..")) {
    throw new Error(`createLocalFsStore: invalid key ${JSON.stringify(key)}`);
  }
  return path.join(rootDir, key);
}

/**
 * @param {{rootDir: string}} opts - directory that stands in for "the remote" in tests.
 * @returns {import("./store.mjs").RemoteStateStore}
 */
export function createLocalFsStore({ rootDir }) {
  if (typeof rootDir !== "string" || rootDir.length === 0) {
    throw new Error("createLocalFsStore: rootDir is required");
  }

  const store = {
    async getText(key) {
      try {
        return fs.readFileSync(resolvePath(rootDir, key), "utf8");
      } catch (e) {
        if (e && e.code === "ENOENT") return null;
        throw e;
      }
    },
    async putText(key, text) {
      const p = resolvePath(rootDir, key);
      fs.mkdirSync(path.dirname(p), { recursive: true });
      fs.writeFileSync(p, text);
    },
    async putTextWithMerge(key, mergeFn) {
      // No real concurrency inside a single Node process against a plain directory — one
      // read-merge-write is sufficient (unlike github-store.mjs, which must retry against a
      // remote that other processes can push to between its own fetch and push).
      const current = await store.getText(key);
      const next = await mergeFn(current);
      await store.putText(key, next);
      return next;
    },
    async close() {},
  };
  return store;
}
