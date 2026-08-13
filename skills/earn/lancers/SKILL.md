---
name: lancers
description: Use when operating, diagnosing, or extending the canonical Lancers acquisition, storefront, sales, fulfillment, finance, reporting, or revenue loop.
---

# Lancers Money Loop

Operate Lancers from the Life Manager exact-release source. Public/provider readback and durable receipts are truth; process health,
listing count, proposals, forecasts, and unpaid contracts are not revenue.

## Architecture

- Acquisition: `scripts/application_loop.py` discovers, qualifies, applies at most once per tick, and requires an official proposal ID.
- Storefront: `scripts/storefront_offer.py` inspects or aligns one existing canonical package. It never creates listings or edits a batch.
- Sales source: `scripts/work_sync.py` reads official boards and messages without sending.
- Reporting: `scripts/telegram_report.py` reports state changes from the canonical owners and ledger.
- Product: `products/monthly-sns-content-ops-v1.json` is the single offer definition. Its image is in `assets/`.

Do not add another scheduler, DB, state file, checkout, browser profile, or mutable runtime copy. Deploy only an immutable commit reachable
from `origin/main`. Preserve provider-native spot/3-month/6-month contract routes.

## Storefront commands

From an installed exact release:

```bash
python3 skills/earn/lancers/scripts/storefront_offer.py --inspect
python3 skills/earn/lancers/scripts/storefront_offer.py --apply
```

`--inspect` is read-only. `--apply` may update only the listing ID declared in the product JSON and saves at most once. If save succeeds
but readback is incomplete, reconcile with `--inspect`; never repeat a blind save. Product changes require updating the design SSOT first.

## Money truth

Follow one funnel: search impression → view → inquiry → official ContractReceipt → funded work → DeliveryReceipt → PaymentReceipt → bank
reconciliation → net MRR. Keep application and storefront as parallel acquisition entrances into the same sales, fulfillment, and finance
lanes. Never report gross package price or proposal value as earned money.
