// node:test — earn/run.sh identity resolution (REQ-001 / PROP-002, PROP-004, PROP-009, PROP-013).
// Full bash integration: spawns the REAL run.sh in EARN_MODE=discover (side-effect-free: only the
// P1 earn-guard check + one narrate line to a throwaway EARN_LEDGER), with a fully-controlled env
// (execFile's `env` option replaces the child's entire environment -- no ambient contamination from
// this test process itself). The resolved wallet address is read back from the narrate line's own
// `wallet` field (run.sh never prints the private key -- R5 discipline, unchanged).
import { test } from "node:test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFile, execFileSync } from "node:child_process";
import { promisify } from "node:util";
import { privateKeyToAccount } from "viem/accounts";

const run = promisify(execFile);
const RUN_SH = new URL("../run.sh", import.meta.url).pathname;

// Portability fix (converge follow-up, closes the PROP-002/PROP-013 test-fixture bug): every test
// below overrides HOME to a throwaway fixture dir for hermeticity (execFile's `env` option replaces
// the child's ENTIRE environment). run.sh's own wallet_addr() shells out to `python3 -c "...from
// eth_account import Account..."`; on machines where eth_account is installed via `pip install
// --user`, python3 resolves it through a HOME-keyed path (`site.getusersitepackages()`), so
// overriding HOME breaks that import with a swallowed (2>/dev/null) ModuleNotFoundError -- a test-
// fixture portability bug, NOT a production regression (production never overrides HOME). Fix: look
// up the REAL user site-packages dir once, under the REAL (unoverridden) HOME, and pass it through
// via PYTHONPATH to every fixture invocation below. This changes NOTHING about what is asserted --
// ANICCA_HOME/HOME/wallet fixtures stay exactly as isolated as before -- it only restores module
// resolution for the interpreter run.sh already spawns.
const PYTHON_USER_SITE = (() => {
  try {
    return execFileSync(
      "python3",
      ["-c", "import site; print(site.getusersitepackages())"],
      { encoding: "utf8" },
    ).trim();
  } catch {
    return "";
  }
})();

async function tmpDir(prefix) {
  return fs.mkdtemp(path.join(os.tmpdir(), prefix));
}

async function writeWalletJson(dir, privateKey) {
  await fs.mkdir(path.join(dir, ".automaton"), { recursive: true });
  await fs.writeFile(path.join(dir, ".automaton", "wallet.json"), JSON.stringify({ privateKey }));
}

async function writeContaminatingEnv(homeDir, key) {
  await fs.mkdir(path.join(homeDir, ".openclaw"), { recursive: true });
  await fs.writeFile(path.join(homeDir, ".openclaw", ".env"), `BLOCKRUN_WALLET_KEY=${key}\n`);
}

function addr(pk) {
  return privateKeyToAccount(pk).address.toLowerCase();
}

async function runDiscover(env) {
  const ledgerDir = await tmpDir("run-identity-ledger-");
  const ledger = path.join(ledgerDir, "earn-ledger.jsonl");
  const { stdout } = await run("bash", [RUN_SH], {
    env: {
      PATH: process.env.PATH,
      PYTHONPATH: PYTHON_USER_SITE,
      EARN_MODE: "discover",
      EARN_LEDGER: ledger,
      WAKE_ID: "test-wake",
      ...env,
    },
  });
  const raw = (await fs.readFile(ledger, "utf8")).trim().split("\n").filter(Boolean);
  const last = JSON.parse(raw[raw.length - 1]);
  return { wallet: last.wallet, stdout };
}

test("PROP-002: two fixture ANICCA_HOME wallet.json files resolve to two DIFFERENT addresses, even with a shared contaminating BLOCKRUN_WALLET_KEY in the sourced env", async () => {
  const home = await tmpDir("run-identity-home-");
  const pkA = "0x" + "1".repeat(64);
  const pkB = "0x" + "2".repeat(64);
  const pkContaminant = "0x" + "9".repeat(64);
  const aniccaHomeA = path.join(home, "instanceA");
  const aniccaHomeB = path.join(home, "instanceB");
  await writeWalletJson(aniccaHomeA, pkA);
  await writeWalletJson(aniccaHomeB, pkB);
  await writeContaminatingEnv(home, pkContaminant);

  const { wallet: walletA } = await runDiscover({ HOME: home, ANICCA_HOME: aniccaHomeA });
  const { wallet: walletB } = await runDiscover({ HOME: home, ANICCA_HOME: aniccaHomeB });

  assert.equal(walletA, addr(pkA));
  assert.equal(walletB, addr(pkB));
  assert.notEqual(walletA, walletB);
  assert.notEqual(walletA, addr(pkContaminant));
  assert.notEqual(walletB, addr(pkContaminant));
});

test("PROP-004: automaton's REAL resolution (ANICCA_HOME unset, default $HOME/.anicca) is UNCHANGED after REQ-001", async (t) => {
  const realWalletPath = path.join(os.homedir(), ".automaton", "wallet.json");
  let real;
  try {
    real = JSON.parse(await fs.readFile(realWalletPath, "utf8"));
  } catch {
    t.skip("~/.automaton/wallet.json not present on this machine -- skipping the real-machine regression check");
    return;
  }
  const pk = real.privateKey.startsWith("0x") ? real.privateKey : `0x${real.privateKey}`;
  const { wallet } = await runDiscover({ HOME: os.homedir() });
  assert.equal(wallet, addr(pk));
  assert.equal(wallet, "0xb9dd3b67921b354c656523d6851537988f31dd56");
});

test("PROP-009: unresolvable identity (no wallet.json anywhere) -> earn-guard HALTs, wake exits 0, zero ledger lines", async () => {
  // NOTE (converge follow-up): earn/run.sh now HALTs earlier than the old "P1 GUARD" cumulative-net
  // line for this exact case -- resolve-identity.mjs returns empty, so run.sh's own SIGNKEY check
  // (run.sh:47-50) fires first, before the P1 GUARD check is ever reached. Confirmed by reading
  // run.sh directly. The assertion below is updated to match the ACTUAL current HALT log line --
  // it still proves the same thing PROP-009 requires (fail-closed HALT, exit 0, zero strategy
  // branches run, zero ledger lines), just at its real (earlier, more specific) HALT point.
  const home = await tmpDir("run-identity-nowallet-");
  const aniccaHome = path.join(home, "no-wallet-instance");
  await fs.mkdir(aniccaHome, { recursive: true }); // exists, but no .automaton/wallet.json inside
  const ledgerDir = await tmpDir("run-identity-nowallet-ledger-");
  const ledger = path.join(ledgerDir, "earn-ledger.jsonl");
  const { stdout } = await run("bash", [RUN_SH], {
    env: {
      PATH: process.env.PATH,
      PYTHONPATH: PYTHON_USER_SITE,
      HOME: home,
      ANICCA_HOME: aniccaHome,
      EARN_MODE: "discover",
      EARN_LEDGER: ledger,
      WAKE_ID: "test-wake",
    },
  });
  assert.match(stdout, /no signing key resolved for this instance.*HALT \(fail-closed\)/);
  await assert.rejects(fs.readFile(ledger, "utf8")); // never created -- zero lines recorded
});

test("PROP-013: ANICCA_EVM_PRIVATE_KEY set in the ambient parent env (NOT sourced from any .env file) never reaches earn/run.sh's own resolve-identity.mjs evm invocation", async () => {
  const home = await tmpDir("run-identity-leak-");
  const pkA = "0x" + "5".repeat(64);
  const pkLeaked = "0x" + "6".repeat(64);
  const aniccaHome = path.join(home, "instance-leak-test");
  await writeWalletJson(aniccaHome, pkA);
  const { wallet } = await runDiscover({ HOME: home, ANICCA_HOME: aniccaHome, ANICCA_EVM_PRIVATE_KEY: pkLeaked });
  assert.equal(wallet, addr(pkA));
  assert.notEqual(wallet, addr(pkLeaked));
});

test("PROP-014 (gh #986): flat legacy layout -- $ANICCA_HOME/wallet.json with a snake_case private_key field (no .automaton/ dir at all) still resolves, matching pre-EQUALIZE instances like founder-loop's ~/.anicca-founder", async () => {
  const home = await tmpDir("run-identity-flatlegacy-");
  const pk = "0x" + "3".repeat(64);
  const aniccaHome = path.join(home, "flat-legacy-instance");
  await fs.mkdir(aniccaHome, { recursive: true });
  await fs.writeFile(path.join(aniccaHome, "wallet.json"), JSON.stringify({ private_key: pk }));
  const { wallet } = await runDiscover({ HOME: home, ANICCA_HOME: aniccaHome });
  assert.equal(wallet, addr(pk));
});

test("PROP-014b: .automaton/wallet.json wins over a flat legacy wallet.json when both exist for the same instance", async () => {
  const home = await tmpDir("run-identity-flatlegacy-precedence-");
  const pkAutomaton = "0x" + "4".repeat(64);
  const pkFlat = "0x" + "8".repeat(64);
  const aniccaHome = path.join(home, "both-layouts-instance");
  await writeWalletJson(aniccaHome, pkAutomaton);
  await fs.writeFile(path.join(aniccaHome, "wallet.json"), JSON.stringify({ private_key: pkFlat }));
  const { wallet } = await runDiscover({ HOME: home, ANICCA_HOME: aniccaHome });
  assert.equal(wallet, addr(pkAutomaton));
  assert.notEqual(wallet, addr(pkFlat));
});

test("PROP-003: earn/run.sh never writes a raw private-key-shaped string (0x + 64 hex) to stdout or stderr during a full run", async () => {
  // Format check, not judgment (verification-architecture.md:75): a fixture wallet whose private
  // key is KNOWN drives a real discover-mode pass (identity resolution -> P1 earn-guard check ->
  // narrate-line record, the same full path PROP-002 exercises), and the test asserts the raw key
  // never appears verbatim in either stream. run.sh only ever exports the key into $PKVAR for a
  // child process's OWN environment (never echoed) and only prints the DERIVED ADDRESS (via
  // wallet_addr()) into the ledger JSON / narrate line -- this test proves that discipline holds
  // for the full captured process output, not just the one field PROP-002 reads back.
  const home = await tmpDir("run-identity-prop3-");
  const pk = "0x" + "7".repeat(64);
  const aniccaHome = path.join(home, "prop3-instance");
  await writeWalletJson(aniccaHome, pk);
  const ledgerDir = await tmpDir("run-identity-prop3-ledger-");
  const ledger = path.join(ledgerDir, "earn-ledger.jsonl");
  const KEY_SHAPE = /0x[0-9a-fA-F]{64}/;

  // Sanity check FIRST: the fixture key itself must match the pattern we assert against, proving
  // the regex is a real detector and not vacuously non-matching.
  assert.match(pk, KEY_SHAPE);

  let stdout = "";
  let stderr = "";
  try {
    const res = await run("bash", [RUN_SH], {
      env: {
        PATH: process.env.PATH,
        PYTHONPATH: PYTHON_USER_SITE,
        HOME: home,
        ANICCA_HOME: aniccaHome,
        EARN_MODE: "discover",
        EARN_LEDGER: ledger,
        WAKE_ID: "test-wake",
      },
    });
    stdout = res.stdout;
    stderr = res.stderr;
  } catch (err) {
    // Even on a non-zero exit, still assert on whatever the process did print -- a crash must not
    // become a loophole for a leaked key to escape this check.
    stdout = err.stdout || "";
    stderr = err.stderr || "";
  }

  assert.doesNotMatch(stdout, KEY_SHAPE, `raw key-shaped string found in stdout: ${stdout}`);
  assert.doesNotMatch(stderr, KEY_SHAPE, `raw key-shaped string found in stderr: ${stderr}`);

  // Confirm the run actually reached a real resolution (not a trivial early HALT that would make
  // the above pass vacuously) -- the narrate line must carry the DERIVED address, proving the key
  // was resolved and used, not just absent because nothing happened.
  const raw = (await fs.readFile(ledger, "utf8")).trim().split("\n").filter(Boolean);
  assert.equal(raw.length, 1);
  const last = JSON.parse(raw[raw.length - 1]);
  assert.equal(last.wallet, addr(pk));
});
