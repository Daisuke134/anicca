// REQ-105: one-time bootstrap of CITIZENS_REGISTRY_PATH via a SINGLE atomic POSIX exclusive-create
// (fs.open(path, "wx"), O_CREAT|O_EXCL) — never a check-then-act "exists? then copy" pair. Mirrors
// economy/gig/lib/lock.mjs::tryCreateLockFile's own atomic-claim technique. If the exclusive-create
// fails with EEXIST (another racer already won, or a real REQ-305 append already happened), nothing
// is written — the seed content can never overwrite an already-diverged registry.
import fs from "node:fs/promises";
import path from "node:path";

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
