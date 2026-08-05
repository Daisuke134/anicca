# Native Product Checkpoint Binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind canonical publication identities to exactly one product through account-manifest integration IDs, generate the first product-bound native checkpoint, deliver its real Japanese Telegram report, and prove replay sends nothing.

**Architecture:** A new pure `identity/product_binding.py` module validates product/account registries and binds identity rows without I/O. `identity/publication_ledger.py` applies it to the full merged ledger before its existing atomic write; `measure/native_metrics.py` and `report/owner_report.py` retain their current strict product propagation and filtering contracts. Production apply preserves historical metric rows, records exact hashes/counts, delivers the missing checkpoint kind, and updates Spec 27 truthfully.

**Tech Stack:** Python 3 standard library, JSON/JSONL registries and ledgers, `unittest`, launchd, direct Telegram Bot API through the existing owner reporter.

## Global Constraints

- Product binding uses only exact `publisher_integration_id == integration_id`; never caption, display-name, handle, language, or fuzzy matching.
- One integration ID may map to only one product. Conflicts abort before any write.
- Existing rows bound to another product abort before any write.
- Unknown integrations remain `product_id=null` with `product_id_null_reason="account_manifest_integration_unmapped"`.
- Historical `state/post-metrics.jsonl` rows are append-only and MUST NOT be rewritten.
- Missing or unavailable metrics remain null with reasons; never substitute zero.
- A provider queue receipt is not a native publication. Every accepted checkpoint retains exact native ID and URL.
- No account promotes two products and no product borrows another product's metrics or revenue.
- Production sends use the existing direct Telegram client and require a real non-null message ID.
- An identical replay adds zero metric rows, zero owner-report rows, and zero Telegram sends.
- Gate 15 may close after the sixth real report kind; Gate 14 remains OPEN until native collection reaches its separate maturity/completeness conditions.
- Preserve unrelated dirty files and existing LaunchAgents. Only the existing owner-events job may be kickstarted for E2E verification.

---

### Task 1: Pure account-manifest product binder

**Files:**
- Create: `skills/earn/marketing-engine/identity/product_binding.py`
- Create: `skills/earn/marketing-engine/identity/test_product_binding.py`

**Interfaces:**
- Consumes: JSON product manifests with `product_id`; JSON account manifests with `account_id`, `product_id`, and nullable `publisher_integration_id`; publication rows with `integration_id` and optional existing binding fields.
- Produces: `load_product_ids(path: Path) -> set[str]`, `load_account_bindings(path: Path, product_ids: set[str]) -> dict[str, dict[str, str]]`, and `bind_product_ids(rows: list[dict], bindings: dict[str, dict[str, str]]) -> tuple[list[dict], dict]`.

- [ ] **Step 1: Write failing contract tests**

Add literal-fixture tests proving:

```python
def test_exact_integration_binds_account_and_product():
    bound, report = binding.bind_product_ids(
        [{"postiz_post_id": "p1", "integration_id": "i1"}],
        {"i1": {"account_id": "tiktok.obou_anicca", "product_id": "ebook-ja"}},
    )
    assert bound[0]["account_id"] == "tiktok.obou_anicca"
    assert bound[0]["product_id"] == "ebook-ja"
    assert bound[0]["product_id_null_reason"] is None
    assert bound[0]["product_binding_source"] == "account_manifest.publisher_integration_id"
    assert report == {"rows": 1, "bound": 1, "unmapped": 0, "already_bound": 0}

def test_unknown_integration_stays_null_with_reason():
    bound, report = binding.bind_product_ids(
        [{"postiz_post_id": "p1", "integration_id": "unknown"}], {}
    )
    assert bound[0]["product_id"] is None
    assert bound[0]["product_id_null_reason"] == "account_manifest_integration_unmapped"
    assert report["unmapped"] == 1
```

Also test duplicate integration/different product, unknown manifest product,
missing account/product IDs, conflicting existing row binding, same existing
binding, nullable manifest integration, input immutability, deterministic output,
and exact rerun equality.

- [ ] **Step 2: Run RED**

Run:

```bash
python3 -m unittest skills/earn/marketing-engine/identity/test_product_binding.py -v
```

Expected: FAIL because `product_binding.py` and its interfaces do not exist.

- [ ] **Step 3: Implement the minimal pure binder**

Use defensive copies. Registry loaders sort `*.json`, reject malformed objects,
verify account products against the product set, and reject only conflicting
duplicate integration mappings; two identical mappings are idempotent.

Core binding behavior:

```python
mapping = bindings.get(str(row.get("integration_id") or ""))
if mapping is None:
    output["product_id"] = None
    output["product_id_null_reason"] = "account_manifest_integration_unmapped"
else:
    existing = output.get("product_id")
    if existing not in (None, mapping["product_id"]):
        raise ValueError("publication product binding conflict")
    output["account_id"] = mapping["account_id"]
    output["product_id"] = mapping["product_id"]
    output["product_id_null_reason"] = None
    output["product_binding_source"] = "account_manifest.publisher_integration_id"
```

- [ ] **Step 4: Run GREEN and identity regressions**

```bash
python3 -m unittest skills/earn/marketing-engine/identity/test_product_binding.py -v
python3 -m unittest skills/earn/marketing-engine/identity/test_publication_ledger.py -v
```

Expected: all tests PASS with no warnings or external calls.

- [ ] **Step 5: Commit**

```bash
git add skills/earn/marketing-engine/identity/product_binding.py \
  skills/earn/marketing-engine/identity/test_product_binding.py
git commit -m "feat(marketing): bind publication integrations to products"
```

---

### Task 2: Publication-ledger integration and downstream checkpoint contract

**Files:**
- Modify: `skills/earn/marketing-engine/identity/publication_ledger.py`
- Modify: `skills/earn/marketing-engine/identity/test_publication_ledger.py`
- Modify: `skills/earn/marketing-engine/measure/test_native_metrics.py`
- Modify: `skills/earn/marketing-engine/report/test_owner_report.py`

**Interfaces:**
- Consumes: Task 1's registry loaders and `bind_product_ids`; publication-ledger `existing + current` merged rows.
- Produces: a full atomic identity ledger whose mapped rows contain `account_id`, `product_id`, null reason, and binding source. Existing native-metric and owner-report APIs consume these fields unchanged.

- [ ] **Step 1: Write failing publication-ledger integration tests**

Add a temporary account/product registry and assert that the CLI/output path:

```python
merged = ledger.merge_rows([legacy_unbound], [current_unbound])
bound, report = ledger.bind_merged_rows(
    merged, product_registry=products_dir, account_registry=accounts_dir
)
self.assertEqual(bound[0]["product_id"], "ebook-ja")
self.assertEqual(report["bound"], 2)
```

The tests must prove the complete merged ledger is backfilled, an identical run
is byte-equivalent, an unmatched row stays null, and a conflict raises before
the output path changes. Test `--bind-existing-only` by executing `main([...])`
against an existing temporary output ledger and monkeypatching network helpers
to raise if called; the command must pass without calling them. Test the new CLI
defaults and temporary overrides through behavior, not by grepping source text.

- [ ] **Step 2: Write failing downstream propagation tests**

In `test_native_metrics.py`, give `publication()` exact binding fields and
assert a due or missed row preserves:

```python
self.assertEqual(row["product_id"], "ebook-ja")
self.assertIsNone(row["product_id_null_reason"])
self.assertEqual(row["native_post_id"], "native-1")
self.assertEqual(row["native_url"], "https://www.tiktok.com/@account/video/native-1")
```

In `test_owner_report.py`, append that metric plus matching identity, then assert
the checkpoint event is scoped only to `ebook-ja`, contains the native URL and
truthful metrics/reason, and produces the stable key
`checkpoint:ebook-ja:postiz:post-1:24`. A second build/delivery reuses the same
receipt and calls the sender once.

- [ ] **Step 3: Run RED**

```bash
python3 -m unittest \
  skills/earn/marketing-engine/identity/test_publication_ledger.py \
  skills/earn/marketing-engine/measure/test_native_metrics.py \
  skills/earn/marketing-engine/report/test_owner_report.py -v
```

Expected: FAIL because publication-ledger registry integration is absent and the
new end-to-end fixture assertions are not satisfied.

- [ ] **Step 4: Implement the minimal ledger integration**

Add CLI arguments:

```python
result.add_argument("--account-registry", type=Path,
                    default=root / "registry/accounts")
result.add_argument("--product-registry", type=Path,
                    default=root / "registry/products")
result.add_argument("--bind-existing-only", action="store_true")
```

Add `bind_merged_rows(...)` as the single adapter around Task 1:

```python
def bind_merged_rows(rows, *, product_registry: Path, account_registry: Path):
    products = load_product_ids(product_registry)
    bindings = load_account_bindings(account_registry, products)
    return bind_product_ids(rows, bindings)
```

In normal mode, call it after `merge_rows` and before
`validate_rows`/`atomic_write`. In `--bind-existing-only` mode, skip all provider
credential checks and network calls, bind `read_jsonl(args.output)`, validate,
atomically write the same path, and generate the report from those rows. Include
the deterministic binding summary in the report/stdout. Do not add fallback
inference to metrics or reporting.

- [ ] **Step 5: Run GREEN and the focused Gate 15 suite**

```bash
PYTHONPATH=skills/earn/marketing-engine/report python3 -m unittest \
  skills/earn/marketing-engine/identity/test_product_binding.py \
  skills/earn/marketing-engine/identity/test_publication_ledger.py \
  skills/earn/marketing-engine/measure/test_native_metrics.py \
  skills/earn/marketing-engine/report/test_owner_report.py \
  skills/earn/marketing-engine/report/test_install_gate15_launchagents.py \
  skills/earn/marketing-engine/test_direct_telegram_transport.py -v
```

Expected: all tests PASS and no production state, Telegram, or launchd mutation.

- [ ] **Step 6: Commit**

```bash
git add skills/earn/marketing-engine/identity/publication_ledger.py \
  skills/earn/marketing-engine/identity/test_publication_ledger.py \
  skills/earn/marketing-engine/measure/test_native_metrics.py \
  skills/earn/marketing-engine/report/test_owner_report.py
git commit -m "feat(marketing): propagate product-bound checkpoints"
```

---

### Task 3: Canonical apply, real receipt, replay proof, and Spec 27 update

**Files:**
- Modify: `specs/27-MARKETING-ENGINE-END-TO-END.md`
- Runtime state only: `skills/earn/marketing-engine/state/publication-identity.jsonl`
- Append-only runtime state: `skills/earn/marketing-engine/state/post-metrics.jsonl`
- Append-only runtime state: `skills/earn/marketing-engine/state/owner-reports.jsonl`
- Append-only runtime state: `skills/earn/marketing-engine/state/owner-report-deliveries.jsonl`

**Interfaces:**
- Consumes: Tasks 1–2 on the canonical checkout, current account/product registries, existing native-metric collector, installed owner-events LaunchAgent.
- Produces: exact canonical product binding for the Gate 12 publication, at least one product-bound checkpoint event, real Telegram receipt(s), replay-zero evidence, and updated execution SSOT.

- [ ] **Step 1: Run a read-only production preflight**

Record current row counts and SHA-256 for the four state ledgers. Verify the
target Postiz/native/integration tuple and manifest mapping exactly. Run all
focused tests from Task 2 on the canonical commit. Stop if any tuple differs or
the identity/metric/report ledgers contain a conflicting existing key.

- [ ] **Step 2: Create a recoverable identity-ledger backup**

Use a timestamped directory under `/tmp`, copy only
`publication-identity.jsonl`, and record its SHA-256. Do not delete or rewrite
historical metric/report ledgers.

- [ ] **Step 3: Apply product binding through the real publication CLI**

Run `publication_ledger.py --bind-existing-only` with canonical registry,
output, and report paths. This migration performs no Postiz/Apify/TikTok
request. Read back the target:

```text
postiz_post_id=cmsaselv6070sqn0yp7oix7yd
integration_id=cmo5s4edx00vgn10ygnu34a0n
account_id=tiktok.obou_anicca
product_id=ebook-ja
native_post_id=7669159327655054613
native_post_url=https://www.tiktok.com/@obou_anicca/video/7669159327655054613
```

Validate all rows and run an identical binding replay. The second run must
produce the same row count and SHA-256.

- [ ] **Step 4: Collect the real product-bound checkpoint**

Run `measure/native_metrics.py collect` on canonical state. Verify historical
110 rows remain an exact byte prefix and every appended row has a new unique
`(publication_id, target_age_hours)` key, `product_id=ebook-ja`, exact native
ID/URL, and either real integer metrics or null values with explicit reasons.

- [ ] **Step 5: Deliver and verify the checkpoint report**

Kickstart only `ai.anicca.marketing-owner-events`. Wait until it exits. Require
`last exit code = 0`, a new `kind=checkpoint`, `product_id=ebook-ja` owner-report
row, and a terminal `delivered` receipt with non-null Telegram message ID.

- [ ] **Step 6: Prove identical replay sends nothing**

Repeat identity binding, metric collection, and checkpoint reporting. Verify
metric/report/delivery row counts and hashes do not change and no new Telegram
message ID appears.

- [ ] **Step 7: Update Spec 27 at the milestone**

Update the live status, Gate 15 ledger row, reporting As-Is/To-Be row, test
count, real message ID(s), exact state counts, and remaining execution step 1.
Mark Gate 15 DONE only if all six report kinds have real receipts and replay is
zero. Keep Gate 14 OPEN unless its independent maturity/completeness conditions
are actually met.

- [ ] **Step 8: Verify, commit, push, and Telegram milestone**

```bash
git diff --check -- specs/27-MARKETING-ENGINE-END-TO-END.md
git add specs/27-MARKETING-ENGINE-END-TO-END.md
git commit -m "docs(marketing): close Gate 15 checkpoint evidence"
git push origin feature/dist1-mcp-launchd
```

Send one natural-language Telegram milestone containing the real receipt IDs,
tests, replay result, exact remaining Gate 14 gap, and next SSOT item.
