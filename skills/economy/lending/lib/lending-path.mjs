// economy/lending/lib/lending-path.mjs — the single canonical statePath every loan-issuance lock
// acquisition and every loans.jsonl read/write must import and reuse (REQ-106/PROP-106d), mirroring
// anicca-agent-spawn's own CITIZENS_REGISTRY_PATH discipline. Colocated under this skill's own
// state/ directory (the same convention economy/ubi already uses for its own gojo-log.jsonl) — never
// spawn's children.jsonl, never ubi's colony-wallets.json.
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export const LOANS_LEDGER_PATH = path.join(__dirname, "..", "state", "loans.jsonl");
