// node:test — serve.mjs listen failure must be loud, not silent.
//
// WHY (2026-07-16, measured): app.listen(PORT, cb) had no 'error' handler, so a seller that lost the
// port race still printed {"x402_seller":"up"} and then exited 0. Measured side by side:
//   port 8499 (free)      -> {"x402_seller":"up"}  + stays alive (timeout 124)
//   port 8413 (taken)     -> {"x402_seller":"up"}  + exit 0 immediately
// Identical stdout, opposite reality. Everything downstream trusted that line: run.sh's UP check,
// the ledger's "x402 server: up" narrate, and launchd's exit code (0 = "clean exit", so KeepAlive
// respawned it forever without ever flagging a fault). A seller that cannot bind must fail loudly:
// nonzero exit + a diagnosable stderr line, so the crash loop is visible instead of self-reporting
// success 364 times in a row.
import { test } from "node:test";
import assert from "node:assert/strict";
import net from "node:net";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const run = promisify(execFile);
const SERVE = new URL("../serve.mjs", import.meta.url).pathname;

const serveEnv = (port) => ({
  PATH: process.env.PATH,
  HOME: process.env.HOME,
  X402_PORT: String(port),
  X402_PAYTO: "0x0000000000000000000000000000000000000001",
});

async function occupy(port) {
  const srv = net.createServer();
  await new Promise((resolve, reject) => {
    srv.once("error", reject);
    srv.listen(port, resolve);
  });
  return srv;
}

async function freePort() {
  const srv = net.createServer();
  await new Promise((r) => srv.listen(0, r));
  const { port } = srv.address();
  await new Promise((r) => srv.close(r));
  return port;
}

test("exits nonzero and says why when the port is already taken", async () => {
  const port = await freePort();
  const squatter = await occupy(port);
  try {
    const err = await run("node", [SERVE], { env: serveEnv(port), timeout: 15000 })
      .then(() => null, (e) => e);

    assert.ok(err, "serve.mjs must not exit 0 when it cannot bind");
    assert.notEqual(err.code, 0, `expected nonzero exit, got ${err.code}`);
    assert.match(err.stderr, /"x402_seller":"failed"/, "must announce the failure");
    assert.match(err.stderr, /EADDRINUSE/, "stderr must name the actual cause");
    // NOT asserted: the absence of "up" on stdout. Measured 2026-07-16 — node binds :: dual-stack, so
    // when a squatter holds only IPv4 the IPv6 bind SUCCEEDS (listening fires, "up" prints) and the
    // IPv4 half then fails (error fires). Both events are real; suppressing the stdout line would
    // mean second-guessing a listen that genuinely half-succeeded. The exit code is the trustworthy
    // signal, which is why this test pins that instead — and run.sh already probes with curl rather
    // than reading this line.
  } finally {
    await new Promise((r) => squatter.close(r));
  }
});

test("reports up and stays alive when the port is free", async () => {
  const port = await freePort();
  // A successful boot never exits, so the timeout firing IS the pass condition.
  const err = await run("node", [SERVE], { env: serveEnv(port), timeout: 6000 })
    .then(() => null, (e) => e);

  assert.ok(err, "a healthy seller must not exit on its own");
  assert.equal(err.killed, true, `expected the timeout to kill it, got exit ${err.code}`);
  assert.match(err.stdout, /"x402_seller":"up"/, "a healthy seller must announce itself");
});
