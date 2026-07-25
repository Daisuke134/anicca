// github-store.mjs — the ONE real RemoteStateStore implementation (S4). Wired by default in
// bin/citizen-state; store.mjs's createLocalFsStore is the test double.
//
// Why a private git repo, not S3 or IPFS (verified live 2026-07-25, see the S4 report for the
// quoted Nosana-side evidence that no cross-job persistent volume exists to make this moot):
//   - This machine has NO S3-compatible credentials anywhere: no ~/.aws/{credentials,config}, no
//     AWS_ACCESS_KEY_ID/S3_BUCKET/R2/CLOUDFLARE_R2/B2/BACKBLAZE env vars, no `aws`/`rclone`/`mc`
//     binary installed. It has NO IPFS/Pinata/web3.storage/nft.storage credentials or a local
//     `ipfs` daemon either (binary not installed, no matching env vars, no config files anywhere
//     under the repo or home directory). Standing up either would mean signing up for and wiring a
//     brand-new provider — exactly what the task says not to do "without saying so." This says so.
//   - `gh` IS already authenticated on this machine (`gh auth status` -> logged in as Daisuke134,
//     `repo`+`gist` scopes) and plain `git` over https already works with this machine's stored
//     credentials with zero extra setup (verified live: `git clone
//     https://github.com/Daisuke134/anicca-monk-factory-state.git`, a PRIVATE repo, succeeded
//     unaided). A private git repo is also the account's OWN established convention for exactly
//     this problem: `Daisuke134/anicca-genesis` ("Hermes runtime state, crons, ledgers... auto-
//     updated") and `Daisuke134/anicca-monk-factory-state` (a private repo holding another
//     citizen's durable state) are both live precedents of "a private git repo is this account's
//     durable store for an agent's own runtime bookkeeping." `Daisuke134/franklin-shelter-state`
//     (private, created 2026-07-25, single `main` branch with one bootstrap commit) is the same
//     pattern, scoped to Franklin's Nosana shelter state specifically rather than mixed into a
//     code repo's own history.
//   - This module never touches a GitHub token directly — it shells out to plain `git` the same
//     way deploy.mjs shells out to the `nosana` CLI — so it introduces no new secret of its own on
//     top of what `gh auth login` already set up on this machine.
//
// Money-safety (hard rule): this store only ever receives the text callers hand it (ledger lines,
// the addresses-only wallet manifest) — it has no notion of what a Solana secret looks like and
// never reads `.solana-session`/`.automaton` itself. Nothing here can leak a private key, because
// nothing here is ever given one.
//
// Concurrency model: putTextWithMerge is plain-git optimistic concurrency. Each attempt fetches
// the branch, hands the CALLER's mergeFn the freshest remote text, commits, and pushes. If the
// push is rejected (another writer landed a commit in between), it re-fetches and re-invokes
// mergeFn with the NEW remote text and retries, up to maxPushRetries — so mergeFn's keep-or-drop
// decision (merge.mjs's mergeAppendOnly) is always made against current content, never a stale
// read, and a genuine race never silently loses a row (see merge.mjs's header).

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export const DEFAULT_STATE_REPO = "Daisuke134/franklin-shelter-state";
export const DEFAULT_STATE_BRANCH = "main";
const DEFAULT_MAX_PUSH_RETRIES = 5;

function git(gitBin, args, cwd) {
  return execFileSync(gitBin, args, { cwd, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
}

/**
 * @param {{repo?: string, branch?: string, remoteUrl?: string, gitBin?: string,
 *          maxPushRetries?: number, workDir?: string}} [opts]
 *   repo: "owner/name" on github.com — ignored if remoteUrl is given (remoteUrl exists so tests
 *     can point this at a local bare repo instead of hitting the network).
 *   workDir: directory to clone into; a fresh mkdtemp'd dir by default. Not cleaned up until
 *     close() — callers that create many short-lived stores should call close() when done.
 * @returns {import("./store.mjs").RemoteStateStore}
 */
export function createGithubGitStore({
  repo = DEFAULT_STATE_REPO,
  branch = DEFAULT_STATE_BRANCH,
  remoteUrl = `https://github.com/${repo}.git`,
  gitBin = "git",
  maxPushRetries = DEFAULT_MAX_PUSH_RETRIES,
  workDir,
} = {}) {
  const dir = workDir || fs.mkdtempSync(path.join(os.tmpdir(), "citizen-state-git-"));
  let cloned = false;

  function ensureClone() {
    if (cloned) return;
    if (!fs.existsSync(path.join(dir, ".git"))) {
      git(gitBin, ["clone", "--quiet", "--branch", branch, "--single-branch", remoteUrl, "."], dir);
    }
    cloned = true;
  }

  function syncToLatest() {
    ensureClone();
    git(gitBin, ["fetch", "--quiet", "origin", branch], dir);
    git(gitBin, ["checkout", "--quiet", branch], dir);
    git(gitBin, ["reset", "--quiet", "--hard", `origin/${branch}`], dir);
  }

  function readLocal(key) {
    try {
      return fs.readFileSync(path.join(dir, key), "utf8");
    } catch (e) {
      if (e && e.code === "ENOENT") return null;
      throw e;
    }
  }

  function writeLocal(key, text) {
    const p = path.join(dir, key);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, text);
  }

  const store = {
    async getText(key) {
      syncToLatest();
      return readLocal(key);
    },

    async putText(key, text) {
      return store.putTextWithMerge(key, async () => text);
    },

    async putTextWithMerge(key, mergeFn) {
      let lastErr;
      for (let attempt = 0; attempt < maxPushRetries; attempt += 1) {
        syncToLatest();
        const current = readLocal(key);
        const next = await mergeFn(current);
        if (next === current) {
          // mergeFn decided there is nothing new to write — no empty commit, no push.
          return next;
        }
        writeLocal(key, next);
        git(gitBin, ["add", "--", key], dir);
        git(
          gitBin,
          [
            "-c",
            "user.name=citizen-state",
            "-c",
            "user.email=citizen-state@local",
            "commit",
            "--quiet",
            "-m",
            `chore(state): sync ${key}`,
          ],
          dir,
        );
        try {
          git(gitBin, ["push", "--quiet", "origin", `HEAD:${branch}`], dir);
          return next;
        } catch (err) {
          lastErr = err;
          // Someone else pushed between our fetch and our push. Loop: syncToLatest() at the top
          // of the next iteration re-fetches and hard-resets, discarding our now-stale local
          // commit, and mergeFn runs again against the NEW remote content.
        }
      }
      throw new Error(
        `createGithubGitStore: putTextWithMerge(${key}) failed after ${maxPushRetries} attempts: ${(lastErr && lastErr.message) || lastErr}`,
      );
    },

    async close() {
      fs.rmSync(dir, { recursive: true, force: true });
    },
  };
  return store;
}
