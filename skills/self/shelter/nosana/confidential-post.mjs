// confidential-post.mjs — S13's hard-won lesson turned into code: a confidential job's
// definition is served PEER-TO-PEER by the posting process itself (public IPFS carries only a
// stub), so the poster MUST outlive the node's claim — a post-and-exit poster strands the job at
// `waiting-for-job-definition` (observed live 2026-07-26, job HsUW6Spd…). This module spawns
// `nosana job post --confidential --wait` as a DETACHED child logging to a file, and leaves
// address discovery to the same authoritative reconciliation deploy.mjs uses.
//
// Money-safety: argv contains paths and addresses only — the secret rides inside the definition
// file's env, which itself exists only on this machine and in the p2p channel.

import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { buildPostArgs } from "./deploy.mjs";

// TTY shim preloaded into the child (see shim/tty-shim.cjs): @nosana/cli crashes on piped
// stdout at its post-display step, killing the p2p definition server the confidential job
// depends on. Observed live twice; the shim no-ops the TTY calls.
const TTY_SHIM_PATH = path.join(path.dirname(fileURLToPath(import.meta.url)), "shim", "tty-shim.cjs");

/**
 * Spawn the long-lived confidential poster. Returns {pid, args}. The child is detached +
 * unref'd: it survives this process and keeps serving the definition for the whole lease
 * (kill it later via the recorded pid — that is S14's "stop the Mac-side process" lever).
 */
export function spawnConfidentialPost({
  marketAddress,
  keypairPath,
  jobDefFile,
  durationMinutes,
  network = "mainnet",
  logPath,
  spawnImpl = spawn,
} = {}) {
  if (!marketAddress || !keypairPath || !jobDefFile || !durationMinutes || !logPath) {
    throw new Error("spawnConfidentialPost: marketAddress, keypairPath, jobDefFile, durationMinutes, logPath are all required");
  }
  const args = [
    ...buildPostArgs({ marketAddress, keypairPath, jobDefFile, durationMinutes, network, confidential: true }),
    "--wait",
  ];
  const fd = fs.openSync(logPath, "a");
  const child = spawnImpl("nosana", args, {
    detached: true,
    stdio: ["ignore", fd, fd],
    env: { ...process.env, NODE_OPTIONS: `${process.env.NODE_OPTIONS || ""} --require ${TTY_SHIM_PATH}`.trim() },
  });
  if (child && typeof child.unref === "function") child.unref();
  fs.closeSync(fd); // the child holds its own copy of the fd — parent's copy leaks otherwise
  return { pid: child.pid, args };
}
