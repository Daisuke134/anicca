// REQ-105: one-time bootstrap of CITIZENS_REGISTRY_PATH via a SINGLE atomic POSIX exclusive-create
// (fs.open(path, "wx"), O_CREAT|O_EXCL) — never a check-then-act "exists? then copy" pair. Mirrors
// economy/gig/lib/lock.mjs::tryCreateLockFile's own atomic-claim technique. If the exclusive-create
// fails with EEXIST (another racer already won, or a real REQ-305 append already happened), nothing
// is written — the seed content can never overwrite an already-diverged registry.
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

// REQ-105 (resolves FIND-901): the git-tracked seed template's real, on-disk location. Read
// exactly once, at bootstrap (below) -- NEVER written to by any runtime code path (PROP-105j).
export const CITIZENS_SEED_PATH = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
  "registry",
  "citizens.seed.json"
);

export async function bootstrapCitizensRegistry({ registryPath, seedContent }) {
  await fs.mkdir(path.dirname(registryPath), { recursive: true });
  let handle;
  try {
    handle = await fs.open(registryPath, "wx");
  } catch (e) {
    if (e && e.code === "EEXIST") return { created: false };
    throw e;
  }
  try {
    await handle.writeFile(seedContent);
  } finally {
    await handle.close();
  }
  return { created: true };
}

// REQ-105's real one-time-bootstrap caller: reads citizens.seed.json's verbatim content (a READ,
// never a write -- PROP-105j) and hands it to bootstrapCitizensRegistry, which alone performs the
// atomic exclusive-create against the durable registryPath (CITIZENS_REGISTRY_PATH in production).
export async function ensureCitizensRegistry({ registryPath, seedPath = CITIZENS_SEED_PATH } = {}) {
  const seedContent = await fs.readFile(seedPath, "utf8");
  return bootstrapCitizensRegistry({ registryPath, seedContent });
}
