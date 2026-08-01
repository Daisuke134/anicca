import assert from "node:assert/strict";
import test from "node:test";
import { execFile } from "node:child_process";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);
const script = new URL("../scripts/startup-context/export-openclaw.mjs", import.meta.url);

test("OpenClaw export writes only the allowlisted current Life Manager kit", async () => {
  const root = await mkdtemp(join(tmpdir(), "life-manager-export-"));
  const target = join(root, "life-manager-current");

  try {
    await execFileAsync(process.execPath, [script.pathname, "--target", target]);
    const manifest = JSON.parse(await readFile(join(target, "export-manifest.json"), "utf8"));
    assert.equal(manifest.protected_path, "submitted/**");
    assert.deepEqual(
      manifest.files.map(({ file }) => file).sort(),
      ["README.md", "answers.en.md", "answers.ja.md", "assets.json", "deck.md", "one-pager.md"],
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("OpenClaw export refuses submitted history targets", async () => {
  const root = await mkdtemp(join(tmpdir(), "life-manager-export-"));
  const target = join(root, "submitted", "life-manager-current");

  try {
    await assert.rejects(
      execFileAsync(process.execPath, [script.pathname, "--target", target]),
      /submitted history is immutable/i,
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
