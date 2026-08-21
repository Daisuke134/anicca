import assert from "node:assert/strict";
import { chmodSync, readFileSync, statSync } from "node:fs";
import { mkdtemp, writeFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { ensureWallet } from "../ensure-wallet.mjs";

test("ensureWallet creates one owner-only EVM wallet and is idempotent", async () => {
  const home = await mkdtemp(join(tmpdir(), "agent-economy-wallet-"));
  const first = await ensureWallet({ home });
  const walletPath = join(home, ".automaton", "wallet.json");
  const mode = statSync(walletPath).mode & 0o777;
  assert.equal(first.created, true);
  assert.match(first.address, /^0x[0-9a-fA-F]{40}$/u);
  assert.equal(mode, 0o600);

  const second = await ensureWallet({ home });
  assert.deepEqual(second, { address: first.address, path: walletPath, created: false });
  assert.equal(JSON.parse(readFileSync(walletPath, "utf8")).address, first.address);
});

test("ensureWallet rejects an existing malformed wallet instead of replacing it", async () => {
  const home = await mkdtemp(join(tmpdir(), "agent-economy-wallet-"));
  const dir = join(home, ".automaton");
  const walletPath = join(dir, "wallet.json");
  const { mkdir } = await import("node:fs/promises");
  await mkdir(dir, { recursive: true });
  await writeFile(walletPath, JSON.stringify({ address: "not-an-address", privateKey: "bad" }));
  chmodSync(walletPath, 0o600);
  await assert.rejects(() => ensureWallet({ home }), /wallet address|private key/u);
});

test("the stable symlink-style CLI path executes the main entrypoint", async () => {
  const home = await mkdtemp(join(tmpdir(), "agent-economy-wallet-cli-"));
  const result = spawnSync(process.execPath, [new URL("../ensure-wallet.mjs", import.meta.url).pathname], {
    encoding: "utf8",
    env: { ...process.env, ANICCA_HOME: home },
  });
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout.trim(), /^0x[0-9a-fA-F]{40}$/u);
});
