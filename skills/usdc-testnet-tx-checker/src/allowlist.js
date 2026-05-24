import path from 'node:path';
import { normalizeHexAddress, parseArgs, readJson, repoDir, writeJson } from './util.js';

function loadAllowlistPath() {
  return path.join(repoDir(), 'allowlist.json');
}

function loadAllowlist() {
  const p = loadAllowlistPath();
  return { path: p, data: readJson(p) };
}

function cmdAdd(args) {
  const addr = normalizeHexAddress(args.address);
  const { path: p, data } = loadAllowlist();
  const set = new Set((data.allowedRecipients || []).map(normalizeHexAddress));
  set.add(addr);
  data.allowedRecipients = Array.from(set.values()).sort();
  writeJson(p, data);
  console.log(JSON.stringify({ ok: true, added: addr, total: data.allowedRecipients.length }));
}

function cmdList() {
  const { data } = loadAllowlist();
  console.log(JSON.stringify({ ok: true, allowedRecipients: data.allowedRecipients || [] }, null, 2));
}

function main() {
  const sub = process.argv[2];
  const args = parseArgs(process.argv.slice(3));

  if (sub === 'add') return cmdAdd(args);
  if (sub === 'list') return cmdList();

  console.error('Usage: node src/allowlist.js <add|list> [--address 0x...]');
  process.exit(2);
}

main();

