// ledger-files.mjs — the exact set of local ledger files this persistence layer round-trips (S4),
// and the remote key each maps to under franklin-shelter-state's `nosana/` prefix.
//
// Filenames here are literal strings, deliberately NOT imported from deploy.mjs / acquire-nos.mjs
// / executor.mjs — persistence/ owns only this directory (S4 task brief), so this list must be
// kept in sync BY HAND if one of those ever renames its ledger file. Current source of each:
//   shelter-cost.jsonl            deploy.mjs:348 (append/read via spawn/lib/shelter-cost-ledger.js)
//   nosana-renewal-intents.jsonl  renew/executor.mjs:314
//   nosana-funding-intents.jsonl  funding/acquire-nos.mjs:979
//   nosana-funding.jsonl          funding/acquire-nos.mjs:980
//   nosana-deploy-intents.jsonl   deploy.mjs:348
//
// The S4 brief names four round-trip categories — "the wallet manifest, the shelter cost ledger,
// the renewal intent ledger, and the funding ledgers" — and nosana-deploy-intents.jsonl is
// deliberately included as a FIFTH file beyond that literal list. Disclosed reason: it is the
// pre/post-send intent log deploy.mjs itself writes for every deploy attempt, and shelter-
// cost.jsonl's own correction rows (appendShelterCostCorrection) reference deploy-intents rows'
// exact ts/jobAddress when documenting a reconciled mistake — losing it would leave the shelter-
// cost audit trail referencing rows that no longer exist anywhere. It is part of "the audit trail"
// the S4 brief's intro explicitly says a rebuild must not lose.

export const LEDGER_SPECS = [
  { localFileName: "shelter-cost.jsonl", remoteKey: "nosana/shelter-cost.jsonl" },
  { localFileName: "nosana-renewal-intents.jsonl", remoteKey: "nosana/nosana-renewal-intents.jsonl" },
  { localFileName: "nosana-funding-intents.jsonl", remoteKey: "nosana/nosana-funding-intents.jsonl" },
  { localFileName: "nosana-funding.jsonl", remoteKey: "nosana/nosana-funding.jsonl" },
  { localFileName: "nosana-deploy-intents.jsonl", remoteKey: "nosana/nosana-deploy-intents.jsonl" },
];

export const WALLET_MANIFEST_LOCAL_FILE_NAME = "wallet-manifest.json";
export const WALLET_MANIFEST_REMOTE_KEY = "nosana/wallet-manifest.json";
