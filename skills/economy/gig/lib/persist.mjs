// economy/gig/lib/persist.mjs — thin fs read/write for the gig board's JSON state file. Kept separate
// from store.mjs (pure transitions) so store.mjs stays testable with zero fs/network (coding-style.md
// "many small files, high cohesion"). Fail-closed on read: a missing file is a fresh board, not a crash;
// a corrupt file IS a crash (we never silently discard real gig data).
import { promises as fs } from "node:fs";
import path from "node:path";
import { emptyState } from "./store.mjs";

export async function loadState(statePath) {
  try {
    const raw = await fs.readFile(statePath, "utf8");
    return JSON.parse(raw);
  } catch (e) {
    if (e.code === "ENOENT") return emptyState();
    throw e;
  }
}

export async function saveState(statePath, state) {
  await fs.mkdir(path.dirname(statePath), { recursive: true });
  await fs.writeFile(statePath, JSON.stringify(state, null, 2) + "\n");
}
