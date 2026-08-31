# Lancers Storefront Canonical Offer Skill — Implementation Plan

## Goal

公式canonical listing `1338228`だけを、3.2/3.3の月次SNS content operations offerへ安全に揃え、同じ操作を
Mr.botのcanonical Lancers skillから再実行・検証できる状態にする。売上は保存件数ではなく、公式
`検索表示 → 閲覧 → 相談 → native monthly contract → PaymentReceipt`で判定する。

## Ponytail boundary

- 既存Chrome CDP、exact-SHA installer、application/report/work-sync、shared ledgerを再利用する。
- 新daemon、scheduler、DB、state、checkout、publisher abstractionを作らない。
- `1338229`〜`1338233`を変更しない。legacy repo外`listing_tick.py`を取り込まない。
- skill source 4 files（script約180 LOC、SKILL、JSON、PNG）＋installer/test 2変更。画像以外のproduction 100 LOC超は
  Playwright form/readbackという単一の外部作用境界のため許容し、helper/serviceへ分割しない。

## Task 1 — Canonical skill and product

Files:

- Create `skills/earn/lancers/SKILL.md`
- Create `skills/earn/lancers/products/monthly-sns-content-ops-v1.json`
- Create `skills/earn/lancers/assets/monthly-sns-content-ops-v1.png`

Write the exact product identity, target listing, title/subtitle, category/subcategory/industry/tags, three fixed plans,
description, exclusions, notice, and 16:9 image. The skill documents inspect/apply/readback commands and revenue truth.

## Task 2 — Bounded edit/readback command

File: `skills/earn/lancers/scripts/storefront_offer.py`

Implement `--inspect` and explicit `--apply`. Validate product and target, acquire the existing Lancers account lock, connect to
the existing CDP browser, verify `1338228` is self-canonical, fill the five official edit steps, upload the image, save once, and
read the public page back. Any route/field/count drift fails closed. Emit one sanitized JSON line. Never mutate another ID.

## Task 3 — Exact-release inclusion

Files:

- Modify `apps/lancers-revenue/scripts/install-local.sh`
- Modify `apps/lancers-revenue/tests/test_install_local.py`

Archive the SKILL, product, asset, and command into the immutable release. Verify byte identity and Python compilation through the
existing installer acceptance; do not add a fourth launchd owner.

## Task 4 — Real provider acceptance

1. Record hashes for application state, listing receipt, ledger, and all six public listing content projections.
2. Run exact-release `--inspect`; require logged-in target, self-canonical, and no mutation.
3. Run exact-release `--apply` once. This is the only provider mutation in the slice.
4. Require official save completion and public readback of title, subtitle, three plans, description, notice, image, canonical URL,
   and native spot/3-month/6-month routes.
5. Require other five content projections and all three runtime state hashes unchanged; require no orphan process.
6. Update the SSOT with deployed SHA, official evidence, funnel baseline, and the next single TODO; commit and push main.

## Failure boundary

If save completion occurs but public readback is incomplete, report `publication_uncertain` and do not save again. Reconcile by
read-only public/edit inspection. Search result propagation can take up to 24 hours and is monitored separately; it never triggers
a blind duplicate edit.

## Completion evidence

- Main/exact release: `ec8255263f7e4ba5c58afa03b11ef11444868f95`
- Apply/readback: `action=updated`, `aligned=true`, image present, prices ¥98k/¥198k/¥398k, delivery 30/30/30,
  native spot/3-month/6-month routes each present for all three plans.
- Idempotency: immediate second apply returned `action=unchanged`.
- Scope: `1338228` moved to its own content hash; `1338229`–`1338233` retained the old content hash and published state.
- Safety: application, ledger, and listing state hashes stayed unchanged; no new scheduler, DB, state, checkout, listing, archive,
  delete, or republish operation was added.
- Funnel: management counters remain zero immediately after the update; provider search propagation is observed for up to 24 hours.
