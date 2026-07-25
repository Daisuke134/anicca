// node:test — github-store.mjs: exercises REAL git mechanics (clone/fetch/commit/push) against a
// local bare repo standing in for GitHub — `remoteUrl` exists precisely so these tests never touch
// the network or the real Daisuke134/franklin-shelter-state repo, while still proving the actual
// git plumbing (not a mock of it) works, including a genuine two-writer push race.
import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { createGithubGitStore } from "../github-store.mjs";

function git(args, cwd) {
  return execFileSync("git", args, { cwd, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
}

/** A bare local repo with one commit on `main` — mirrors the real franklin-shelter-state repo's
 * actual bootstrap state (created once, out of band, with an initial commit) so this store's code
 * never has to special-case "repo has zero commits". */
function makeBareRemoteWithInitialCommit() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "citizen-state-bare-test-"));
  const bareDir = path.join(root, "remote.git");
  git(["init", "--quiet", "--bare", "--initial-branch=main", bareDir]);
  const seedDir = path.join(root, "seed");
  fs.mkdirSync(seedDir);
  git(["init", "--quiet", "-b", "main", seedDir]);
  git(["-c", "user.name=t", "-c", "user.email=t@t", "commit", "--quiet", "--allow-empty", "-m", "init"], seedDir);
  git(["remote", "add", "origin", bareDir], seedDir);
  git(["push", "--quiet", "origin", "main"], seedDir);
  return { remoteUrl: bareDir, cleanup: () => fs.rmSync(root, { recursive: true, force: true }) };
}

test("createGithubGitStore: getText returns null for a key that has never been written", async () => {
  const { remoteUrl, cleanup } = makeBareRemoteWithInitialCommit();
  try {
    const store = createGithubGitStore({ remoteUrl, branch: "main" });
    assert.equal(await store.getText("nosana/does-not-exist.jsonl"), null);
    await store.close();
  } finally {
    cleanup();
  }
});

test("createGithubGitStore: putText pushes to the real remote — a fresh store instance sees it", async () => {
  const { remoteUrl, cleanup } = makeBareRemoteWithInitialCommit();
  try {
    const writer = createGithubGitStore({ remoteUrl, branch: "main" });
    await writer.putText("nosana/wallet-manifest.json", '{"solanaAddress":"ABC"}\n');
    await writer.close();

    const reader = createGithubGitStore({ remoteUrl, branch: "main" });
    assert.equal(await reader.getText("nosana/wallet-manifest.json"), '{"solanaAddress":"ABC"}\n');
    await reader.close();
  } finally {
    cleanup();
  }
});

function commitCount(remoteUrl) {
  const checkDir = fs.mkdtempSync(path.join(os.tmpdir(), "citizen-state-check-"));
  git(["clone", "--quiet", remoteUrl, checkDir], undefined);
  const out = git(["log", "--oneline", "main"], checkDir);
  fs.rmSync(checkDir, { recursive: true, force: true });
  return out.trim().split("\n").filter(Boolean).length;
}

test("createGithubGitStore: putText with unchanged content pushes no new commit (no-op skip)", async () => {
  const { remoteUrl, cleanup } = makeBareRemoteWithInitialCommit();
  try {
    const store = createGithubGitStore({ remoteUrl, branch: "main" });
    await store.putText("k.txt", "same\n");
    const countAfterFirstWrite = commitCount(remoteUrl);
    await store.putText("k.txt", "same\n"); // identical text — mergeFn returns next === current
    const countAfterSecondWrite = commitCount(remoteUrl);
    await store.close();
    assert.equal(countAfterSecondWrite, countAfterFirstWrite, "identical content must not create a second commit");
  } finally {
    cleanup();
  }
});

test("createGithubGitStore: putTextWithMerge retries and re-merges when another writer pushes in between — neither writer's row is lost", async () => {
  const { remoteUrl, cleanup } = makeBareRemoteWithInitialCommit();
  try {
    const storeA = createGithubGitStore({ remoteUrl, branch: "main" });
    const storeB = createGithubGitStore({ remoteUrl, branch: "main" });
    let mergeFnCalls = 0;

    const result = await storeA.putTextWithMerge("k.txt", async (current) => {
      mergeFnCalls += 1;
      if (mergeFnCalls === 1) {
        // Land storeB's commit BETWEEN storeA's fetch (already done, above) and storeA's push
        // (about to happen after this callback returns) — a genuine race, not a simulated one.
        await storeB.putText("k.txt", "B\n");
      }
      return `${current || ""}A\n`;
    });

    assert.equal(mergeFnCalls, 2, "first attempt must have raced and lost, forcing a real retry");
    assert.equal(result, "B\nA\n", "the retry re-merged against B's committed content — B's row was not dropped");

    const reader = createGithubGitStore({ remoteUrl, branch: "main" });
    assert.equal(await reader.getText("k.txt"), "B\nA\n", "the remote reflects BOTH writers' rows, not just the last pusher's");

    await Promise.all([storeA.close(), storeB.close(), reader.close()]);
  } finally {
    cleanup();
  }
});
