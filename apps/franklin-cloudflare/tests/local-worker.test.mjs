import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { rm } from "node:fs/promises";
import { test } from "node:test";
import { setTimeout as delay } from "node:timers/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const persistenceRoot = path.join(projectRoot, ".wrangler", "test-state");
const internalToken = "local-test-token";
const port = 8787;

function appendOutput(running, chunk) {
  running.output = `${running.output}${chunk}`.slice(-12000);
}

async function waitForExit(child, timeoutMs) {
  if (child.exitCode !== null) return;
  await Promise.race([once(child, "exit"), delay(timeoutMs)]);
}

function signalProcessGroup(child, signal) {
  if (child.exitCode !== null || !child.pid) return;
  child.kill(signal);
}

async function stopWorker(running) {
  if (!running) return;

  signalProcessGroup(running.child, "SIGTERM");
  await waitForExit(running.child, 5000);

  if (running.child.exitCode === null) {
    signalProcessGroup(running.child, "SIGKILL");
    await waitForExit(running.child, 2000);
  }

  if (running.child.exitCode === null) {
    throw new Error(`local Worker did not stop after SIGKILL: ${running.output}`);
  }
}

async function startWorker(port) {
  const wranglerEntrypoint = path.join(projectRoot, "node_modules", "wrangler", "bin", "wrangler.js");
  const running = {
    output: "",
    port,
    child: spawn(
      process.execPath,
      [
        wranglerEntrypoint,
        "dev",
        "--local",
        "--env",
        "local",
        "--port",
        String(port),
        "--persist-to",
        persistenceRoot,
        "--show-interactive-dev-session=false"
      ],
      {
        cwd: projectRoot,
        env: { ...process.env, CI: "1", WRANGLER_SEND_METRICS: "false" },
        stdio: ["ignore", "pipe", "pipe"]
      }
    )
  };

  running.child.stdout.on("data", (chunk) => appendOutput(running, chunk.toString()));
  running.child.stderr.on("data", (chunk) => appendOutput(running, chunk.toString()));

  const baseUrl = `http://localhost:${port}`;
  try {
    const deadline = Date.now() + 30000;
    while (Date.now() < deadline) {
      if (running.child.exitCode !== null) {
        throw new Error(`local Worker exited before readiness:\n${running.output}`);
      }

      try {
        const response = await fetch(`${baseUrl}/health`, {
          signal: AbortSignal.timeout(750)
        });
        if (response.status === 200) return running;
      } catch {
        // The local Worker is still booting.
      }

      await delay(250);
    }

    throw new Error(`local Worker did not become ready within 30s:\n${running.output}`);
  } catch (error) {
    await stopWorker(running).catch(() => undefined);
    throw error;
  }
}

async function restartWorker(running) {
  const port = running.port;
  await stopWorker(running);
  return startWorker(port);
}

async function requestJson(running, pathname, init) {
  const response = await fetch(`http://localhost:${running.port}${pathname}`, init);
  const body = await response.json();
  return { body, response };
}

test("Franklin local Worker vertical slice", async (t) => {
  await rm(persistenceRoot, { recursive: true, force: true });
  let running;

  try {
    running = await startWorker(port);

    await t.test("health is publicly readable", async () => {
      const { body, response } = await requestJson(running, "/health");
      assert.equal(response.status, 200);
      assert.deepEqual(body, { service: "franklin-cloudflare", status: "ok" });
    });

    await t.test("mutation without the internal bearer token is rejected", async () => {
      const { body, response } = await requestJson(running, "/internal/franklin/unauthorized/state", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ command: "must-not-apply" })
      });
      assert.equal(response.status, 401);
      assert.deepEqual(body, { error: "unauthorized" });
    });

    await t.test("named Franklin state persists across Worker restart", async () => {
      const initial = await requestJson(running, "/api/franklin/franklin-alpha/status");
      assert.equal(initial.response.status, 200);
      assert.equal(initial.body.franklinId, "franklin-alpha");
      assert.equal(initial.body.state.revision, 0);

      const mutation = await requestJson(running, "/internal/franklin/franklin-alpha/state", {
        method: "POST",
        headers: {
          authorization: `Bearer ${internalToken}`,
          "content-type": "application/json"
        },
        body: JSON.stringify({ command: "record-observation" })
      });
      assert.equal(mutation.response.status, 200);
      assert.equal(mutation.body.state.revision, 1);

      running = await restartWorker(running);
      const afterRestart = await requestJson(running, "/api/franklin/franklin-alpha/status");
      assert.equal(afterRestart.response.status, 200);
      assert.equal(afterRestart.body.state.revision, 1);
      assert.equal(afterRestart.body.state.lastCommand, "record-observation");
    });

    await t.test("Franklin A and B use isolated named Agent state", async () => {
      const mutation = await requestJson(running, "/internal/franklin/franklin-a/state", {
        method: "POST",
        headers: {
          authorization: `Bearer ${internalToken}`,
          "content-type": "application/json"
        },
        body: JSON.stringify({ command: "only-a" })
      });
      assert.equal(mutation.response.status, 200);

      const [franklinA, franklinB] = await Promise.all([
        requestJson(running, "/api/franklin/franklin-a/status"),
        requestJson(running, "/api/franklin/franklin-b/status")
      ]);
      assert.equal(franklinA.body.state.lastCommand, "only-a");
      assert.equal(franklinA.body.state.revision, 1);
      assert.equal(franklinB.body.state.lastCommand, null);
      assert.equal(franklinB.body.state.revision, 0);
    });
  } finally {
    await stopWorker(running);
  }
});
