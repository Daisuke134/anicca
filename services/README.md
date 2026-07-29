# services/

External OSS services that Life Manager orchestrates as **black-box workers**.
Runtime dependencies are fetched from pinned, integrity-checked public sources;
the repository has no git submodules and never searches adjacent local checkouts.

| Service | Version | Path | Purpose | Spec |
|---|---|---|---|---|
| Inbox Zero | optional integration, not a runtime dependency | external `elie222/inbox-zero` deployment | Optional Gmail Push + follow-up tracker. Life Manager's own mail adapters work without this checkout. | [upstream](https://github.com/elie222/inbox-zero) |
| facilitator | pinned `x402-rs/x402-rs@d439a91bda1caee486b0f841c4c6dd265fbee9df` | `services/facilitator/` | Self-host x402 gasless settlement using an integrity-checked cache. | [facilitator README](./facilitator/README.md) |

## How to start

```bash
cd services/facilitator
./start.sh
```

Inbox Zeroを選ぶ運用者はupstreamを独立deployする。Life Managerのclone内へ
checkoutする必要はなく、製品runtime・installer・testはそれに依存しない。

## Adding a new service

1. Pick OSS that does **one** thing well (do not vendor frameworks).
2. Commit/tagとarchive SHA-256を固定し、取得前検証を実装する。
3. License・由来・cache locationを文書化する。
4. Life Manager固有のadapterをこのrepo内に置く。
