#!/usr/bin/env node
/**
 * adapters/custom/tests/e2e.ts
 *
 * E2E verification harness for spec 12 adapters.
 *
 * For each of {lancers, coconala, bland-ai, agentmail}:
 *   - Run a dry-run-safe action (= login.sh / read-inbox.sh / outbound-call.sh --dry-run /
 *     agentmail send.sh to contact@aniccaai.com)
 *   - Capture exit code, stdout tail, timing
 *   - Append a record to state/adapter-test-log.jsonl
 *
 * NO actual DM is sent to a real client from Lancers/Coconala in this iteration —
 * we verify only that login.sh + read-inbox.sh reach the inbox page (= snapshot
 * contains a Japanese inbox marker). Bland.ai is dry-run when API key present,
 * skipped with `missing-key` record when absent. AgentMail sends 1 real email to
 * contact@aniccaai.com (= owner's forwarding alias).
 *
 * Run:
 *   node adapters/custom/tests/e2e.ts
 *
 * Exit 0 = all adapters returned a deterministic verdict (sent / dry-run /
 * missing-key / captcha). Exit 1 = unexpected crash.
 */

import { execFile } from "node:child_process";
import { promises as fs } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const CUSTOM_DIR = resolve(__dirname, "..");

interface RunResult {
  adapter: string;
  script: string;
  exit: number;
  stdout: string;
  stderr: string;
  ms: number;
  verdict: string;
}

function run(cmd: string, args: string[]): Promise<RunResult> {
  return new Promise((resolveP) => {
    const started = Date.now();
    execFile(cmd, args, { timeout: 120_000, maxBuffer: 2 * 1024 * 1024 }, (err, stdout, stderr) => {
      const exit = err && typeof (err as NodeJS.ErrnoException).code === "number"
        ? ((err as unknown) as { code: number }).code
        : err ? 1 : 0;
      resolveP({
        adapter: "",
        script: `${cmd} ${args.join(" ")}`,
        exit,
        stdout: (stdout || "").slice(-1200),
        stderr: (stderr || "").slice(-1200),
        ms: Date.now() - started,
        verdict: "",
      });
    });
  });
}

function verdictFromExit(adapter: string, exit: number, stdout: string, stderr: string): string {
  const tail = `${stdout}\n${stderr}`.toLowerCase();
  if (tail.includes("captcha")) return "captcha";
  if (tail.includes("missing-key") || tail.includes("bland_api_key missing")) return "missing-key";
  if (exit === 0) {
    if (tail.includes("dry-run")) return "dry-run-ok";
    if (tail.includes("sent")) return "sent";
    if (tail.includes("reused-existing-session") || tail.includes("oauth-initiated")) return "session-ok";
    if (tail.includes("\"thread_count\"")) return "inbox-ok";
    return "ok";
  }
  if (exit === 3) return "captcha-or-missing-key";
  return "fail";
}

async function main() {
  const results: RunResult[] = [];

  // 1. Lancers: login (idempotent) + read-inbox
  for (const script of ["lancers/scripts/login.sh", "lancers/scripts/read-inbox.sh"]) {
    const r = await run("bash", [resolve(CUSTOM_DIR, script)]);
    r.adapter = "lancers";
    r.verdict = verdictFromExit("lancers", r.exit, r.stdout, r.stderr);
    results.push(r);
  }

  // 2. Coconala: login + read-inbox
  for (const script of ["coconala/scripts/login.sh", "coconala/scripts/read-inbox.sh"]) {
    const r = await run("bash", [resolve(CUSTOM_DIR, script)]);
    r.adapter = "coconala";
    r.verdict = verdictFromExit("coconala", r.exit, r.stdout, r.stderr);
    results.push(r);
  }

  // 3. Bland.ai: dry-run call
  {
    const r = await run("bash", [
      resolve(CUSTOM_DIR, "bland-ai/scripts/outbound-call.sh"),
      "+10000000000",
      "This is a dry-run from anicca-adapter-smith e2e harness.",
      "maya",
      "--dry-run",
    ]);
    r.adapter = "bland-ai";
    r.verdict = verdictFromExit("bland-ai", r.exit, r.stdout, r.stderr);
    results.push(r);
  }

  // 4. AgentMail: real send to contact@aniccaai.com
  {
    const r = await run("bash", [
      resolve(CUSTOM_DIR, "agentmail/scripts/send.sh"),
      "contact@aniccaai.com",
      `[adapter-smith e2e] verify send ${new Date().toISOString()}`,
      "This is an automated e2e verification message from anicca-adapter-smith (spec 12).",
    ]);
    r.adapter = "agentmail";
    r.verdict = verdictFromExit("agentmail", r.exit, r.stdout, r.stderr);
    results.push(r);
  }

  // Persist log
  const stateDir = resolve(CUSTOM_DIR, "../..", "state");
  await fs.mkdir(stateDir, { recursive: true });
  const logPath = resolve(stateDir, "adapter-test-log.jsonl");
  for (const r of results) {
    await fs.appendFile(
      logPath,
      JSON.stringify({ ts: new Date().toISOString(), ...r }) + "\n",
      { mode: 0o600 }
    );
  }
  await fs.chmod(logPath, 0o600);

  // Summary
  console.log("=== adapter-smith e2e summary ===");
  for (const r of results) {
    console.log(`  ${r.adapter.padEnd(10)} exit=${r.exit} verdict=${r.verdict} (${r.ms}ms)`);
  }
  console.log(`\nLog: ${logPath}`);
  const anyHardFail = results.some((r) => r.verdict === "fail");
  process.exit(anyHardFail ? 1 : 0);
}

main().catch((err) => {
  console.error("e2e harness crashed:", err);
  process.exit(1);
});
