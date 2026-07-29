// REQ-103/105: durable, out-of-git-tree location for citizens.json + the coordinator host's real
// $HOME. Both are Effectful Shell (built from resolveStateDir/os.homedir() real reads), never Pure
// Core (resolves FIND-1002's mislabeling) — a module built entirely from two effectful primitives
// cannot itself be a zero-I/O computation.
import os from "node:os";
import path from "node:path";
import { resolveStateDir } from "./state-path.js";

// Computed exactly once at module-load time via Node's os.homedir() (never process.env.HOME read ad
// hoc, never a hardcoded literal) — REQ-403's live-audit script imports and reuses this SAME constant.
export const COORDINATOR_HOME = os.homedir();

// REUSES resolveStateDir({env, home}) unmodified — the SAME mechanism run.sh already uses for
// children.jsonl's own durable location — never a literal path inside the the canonical checkout git working tree.
// Computed inside a try/catch so that resolveStateDir's own fail-closed throw (e.g. HOME resolves
// under /tmp) never blocks importing THIS module for an unrelated purpose (e.g. reading
// COORDINATOR_HOME alone) — a real caller that then tries to use `undefined` as a filesystem path
// fails immediately at first use, so the "never silently touch a tmp-rooted path" guarantee still
// holds, just deferred from import-time to first-use.
let citizensRegistryPath;
try {
  citizensRegistryPath = path.join(resolveStateDir({}), "citizens.json");
} catch {
  citizensRegistryPath = undefined;
}
export const CITIZENS_REGISTRY_PATH = citizensRegistryPath;
