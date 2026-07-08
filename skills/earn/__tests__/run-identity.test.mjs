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
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { privateKeyToAccount } from "viem/accounts";

const run = promisify(execFile);
const RUN_SH = new URL("../run.sh", import.meta.url).pathname;

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
    env: { PATH: process.env.PATH, EARN_MODE: "discover", EARN_LEDGER: ledger, WAKE_ID: "test-wake", ...env },
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
  const home = await tmpDir("run-identity-nowallet-");
  const aniccaHome = path.join(home, "no-wallet-instance");
  await fs.mkdir(aniccaHome, { recursive: true }); // exists, but no .automaton/wallet.json inside
  const ledgerDir = await tmpDir("run-identity-nowallet-ledger-");
  const ledger = path.join(ledgerDir, "earn-ledger.jsonl");
  const { stdout } = await run("bash", [RUN_SH], {
    env: { PATH: process.env.PATH, HOME: home, ANICCA_HOME: aniccaHome, EARN_MODE: "discover", EARN_LEDGER: ledger, WAKE_ID: "test-wake" },
  });
  assert.match(stdout, /P1 GUARD/);
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
