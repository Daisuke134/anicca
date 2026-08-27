// node:test — confidential poster must be long-lived + detached (S13: post-and-exit strands the
// job at waiting-for-job-definition) and must carry --confidential --wait, never --api.
import { test } from "node:test";
import assert from "node:assert/strict";
import os from "node:os";
import path from "node:path";
import { spawnConfidentialPost } from "../confidential-post.mjs";

test("spawns detached nosana post with --confidential --wait, logs to file, no --api", () => {
  let seen = null;
  let unrefd = false;
  const fake = (cmd, args, opts) => {
    seen = { cmd, args, opts };
    return { pid: 4242, unref: () => { unrefd = true; } };
  };
  const out = spawnConfidentialPost({
    marketAddress: "M", keypairPath: "/k.json", jobDefFile: "/d.json", durationMinutes: 10,
    logPath: path.join(os.tmpdir(), "poster-test.log"), spawnImpl: fake,
  });
  assert.equal(out.pid, 4242);
  assert.equal(seen.cmd, "nosana");
  assert.ok(seen.args.includes("--confidential"));
  assert.equal(seen.args[seen.args.length - 1], "--wait");
  assert.equal(seen.args.includes("--api"), false);
  assert.equal(seen.opts.detached, true);
  assert.equal(unrefd, true);
});

test("refuses missing required params", () => {
  assert.throws(() => spawnConfidentialPost({ marketAddress: "M" }), /required/);
});

test("poster child gets the TTY shim via NODE_OPTIONS (moveCursor crash killed two live posters)", () => {
  let seen = null;
  const fake = (cmd, args, opts) => { seen = { cmd, args, opts }; return { pid: 1, unref() {} }; };
  spawnConfidentialPost({
    marketAddress: "M", keypairPath: "/k.json", jobDefFile: "/d.json", durationMinutes: 10,
    logPath: path.join(os.tmpdir(), "poster-test2.log"), spawnImpl: fake,
  });
  assert.match(seen.opts.env.NODE_OPTIONS, /--require .*tty-shim\.cjs/);
});
