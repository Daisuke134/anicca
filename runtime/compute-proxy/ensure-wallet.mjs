// ensure-wallet.mjs — create/read one per-instance EVM identity without funding or broadcasting.
import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { generatePrivateKey, privateKeyToAccount } from "viem/accounts";

const KEY_RE = /^0x[0-9a-fA-F]{64}$/u;
const ADDRESS_RE = /^0x[0-9a-fA-F]{40}$/u;

function walletPath(home) {
  if (typeof home !== "string" || home.length === 0) throw new Error("ANICCA_HOME is required");
  return path.join(home, ".automaton", "wallet.json");
}

async function readAndValidate(file) {
  let wallet;
  try {
    wallet = JSON.parse(await fs.readFile(file, "utf8"));
  } catch (error) {
    if (error?.code === "ENOENT") throw error;
    throw new Error("wallet file is not valid JSON");
  }
  if (!KEY_RE.test(String(wallet?.privateKey || ""))) throw new Error("wallet private key is invalid");
  const derived = privateKeyToAccount(wallet.privateKey).address;
  if (wallet.address !== undefined && (!ADDRESS_RE.test(String(wallet.address)) || wallet.address.toLowerCase() !== derived.toLowerCase())) {
    throw new Error("wallet address does not match private key");
  }
  return derived;
}

export async function ensureWallet({ home, generatePrivateKeyImpl = generatePrivateKey } = {}) {
  const file = walletPath(home);
  try {
    const address = await readAndValidate(file);
    await fs.chmod(file, 0o600);
    return { address, path: file, created: false };
  } catch (error) {
    if (error?.code !== "ENOENT") throw error;
  }

  await fs.mkdir(path.dirname(file), { recursive: true, mode: 0o700 });
  const privateKey = generatePrivateKeyImpl();
  if (!KEY_RE.test(String(privateKey))) throw new Error("wallet generator returned an invalid private key");
  const address = privateKeyToAccount(privateKey).address;
  const body = `${JSON.stringify({ privateKey, address }, null, 2)}\n`;
  try {
    const handle = await fs.open(file, "wx", 0o600);
    try { await handle.writeFile(body, "utf8"); } finally { await handle.close(); }
    await fs.chmod(file, 0o600);
    return { address, path: file, created: true };
  } catch (error) {
    if (error?.code !== "EEXIST") throw error;
    const existing = await readAndValidate(file);
    await fs.chmod(file, 0o600);
    return { address: existing, path: file, created: false };
  }
}

const isMain = process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1]);
if (isMain) {
  ensureWallet({ home: process.env.ANICCA_HOME || process.env.HOME && path.join(process.env.HOME, ".anicca") })
    .then(({ address }) => process.stdout.write(`${address}\n`))
    .catch((error) => { process.stderr.write(`ensure-wallet: ${error.message}\n`); process.exitCode = 1; });
}
