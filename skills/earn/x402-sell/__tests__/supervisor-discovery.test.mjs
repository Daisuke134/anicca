import { test } from "node:test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const run = promisify(execFile);
const RUN_SH = new URL("../../run.sh", import.meta.url).pathname;
const REAL_NODE = process.execPath;
const GUI_UID = typeof process.getuid === "function" ? process.getuid() : 501;

async function executable(file, body) {
  await fs.writeFile(file, body, { mode: 0o755 });
}

test("an isolated agent HOME reuses an existing launchd supervisor instead of creating a second seller", async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "x402-supervisor-"));
  const home = path.join(root, "isolated-home");
  const aniccaHome = path.join(home, ".franklin2-home", ".blockrun");
  const fakeBin = path.join(root, "bin");
  const trace = path.join(root, "launchctl.trace");
  const health = path.join(root, "seller-up");
  const ledger = path.join(root, "earn-ledger.jsonl");
  await fs.mkdir(path.join(aniccaHome, ".automaton"), { recursive: true });
  await fs.mkdir(fakeBin, { recursive: true });
  await fs.writeFile(
    path.join(aniccaHome, ".automaton", "wallet.json"),
    JSON.stringify({ privateKey: `0x${"1".repeat(64)}` }),
  );

  await executable(path.join(fakeBin, "launchctl"), `#!/bin/bash
printf '%s\\n' "$*" >> "$TRACE"
case "$1" in
  print) exit 0 ;;
  kickstart) touch "$HEALTH"; exit 0 ;;
  bootstrap) touch "$HEALTH"; exit 0 ;;
esac
exit 1
`);
  await executable(path.join(fakeBin, "curl"), `#!/bin/bash
if [ -f "$HEALTH" ]; then printf '%s\\n' '{}'; exit 0; fi
exit 7
`);
  await executable(path.join(fakeBin, "sleep"), "#!/bin/bash\nexit 0\n");
  await executable(path.join(fakeBin, "node"), `#!/bin/bash
case "$1" in
  *store-ensure-register.mjs) printf '%s\\n' '{"registered":true}'; exit 0 ;;
esac
exec "$REAL_NODE" "$@"
`);

  const { stdout } = await run("bash", [RUN_SH], {
    env: {
      PATH: `${fakeBin}:${process.env.PATH}`,
      HOME: home,
      ANICCA_HOME: aniccaHome,
      EARN_MODE: "execute",
      EARN_STRATEGY: "x402",
      EARN_LEDGER: ledger,
      X402_PUBLIC_URL: "https://seller.example",
      TRACE: trace,
      HEALTH: health,
      REAL_NODE,
      WAKE_ID: "supervisor-test",
    },
    maxBuffer: 1024 * 1024,
  });

  const calls = (await fs.readFile(trace, "utf8")).trim().split("\n");
  assert.match(stdout, /kickstarting existing job ai\.anicca\.x402-franklin2/);
  assert.equal(
    calls.some((line) => line === `print gui/${GUI_UID}/ai.anicca.x402-franklin2`),
    true,
    "the process namespace, not isolated HOME, must decide whether the supervisor exists",
  );
  assert.equal(
    calls.some((line) => line.startsWith(`kickstart -k gui/${GUI_UID}/ai.anicca.x402-franklin2`)),
    true,
  );
  assert.equal(calls.some((line) => line.startsWith("bootstrap ")), false);
  await assert.rejects(
    fs.access(path.join(home, "Library", "LaunchAgents", "ai.anicca.x402-seller-8413.plist")),
  );
});
