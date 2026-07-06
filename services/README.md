# services/

External OSS services that Anicca orchestrates as **black-box workers**.
Each lives as a git submodule (or vendored fork) and is consumed by
`anicca-oss/runtime/` graphs via the adapters in `anicca-oss/adapters/`.

| Service | Version | Path | Purpose | Spec |
|---|---|---|---|---|
| inbox-zero | submodule pin `main@2026-06-03` (`elie222/inbox-zero`) | `services/inbox-zero/` | Gmail Push trigger + Reply Zero follow-up tracker + AI rule engine. The "missing piece" in the inbox responder loop. | `specs/08-INBOX-RESPONDER-LOOP.md` |
| facilitator | submodule pin `v2.0.1` (`x402-rs/x402-rs`) | `services/facilitator/` | Self-host x402 gasless-settlement facilitator (own signer key + public RPC, zero Coinbase/CDP). The gig marketplace's payment heart (P2.1). | `services/facilitator/README.md` |

## How to start

```bash
git submodule update --init --recursive
cd services/inbox-zero && pnpm install   # see inbox-zero AGENTS.md
cd services/facilitator && ./start.sh    # see services/facilitator/README.md
```

Inbox Zero is a Next.js + Postgres app — it requires its own `.env`
(Gmail OAuth client + DB URL). See `services/inbox-zero/SETUP_PENDING.md`
for the manual steps Dais must complete (OAuth consent, Pub/Sub topic,
Postgres provisioning).

## Adding a new service

1. Pick OSS that does **one** thing well (do not vendor frameworks).
2. `git submodule add --depth 1 <url> services/<name>`.
3. Add a row to the table above + a short "how to start" block.
4. Wire the adapter under `anicca-oss/adapters/` (Composio first, custom only if no Composio integration exists).
