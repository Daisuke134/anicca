# Gate 15 Product Owner Telegram Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the three legacy aggregate Marketing Engine Telegram reporters with one deterministic, product-scoped Japanese owner-report system that renders and deduplicates action, checkpoint, product-daily, incident, experiment, and portfolio-weekly messages from canonical Marketing Engine ledgers.

**Architecture:** `owner_report.py` is a pure renderer plus append-only report/delivery store. It reads only `skills/earn/marketing-engine/state/`, derives a fact object before rendering Japanese text, and never lets an LLM invent numbers or decisions. `owner_report_cli.py` performs bounded sweeps and direct Bot API delivery; `install_gate15_launchagents.py` installs read-back-verifiable schedules without stopping unrelated Marketing Engine jobs.

**Tech Stack:** Python 3 standard library, `unittest`, JSONL, `fcntl`, direct `skills/_shared/telegram.py`, macOS launchd.

## Global Constraints

- Execution SSOT is `specs/27-MARKETING-ENGINE-END-TO-END.md`; Gate 15 is the only scope of this plan.
- Product IDs are exactly `aniccaios`, `honne`, `ebook-ja`, and `ebook-en`.
- Report kinds are exactly `action`, `checkpoint`, `product_daily`, `incident`, `experiment`, and `portfolio_weekly`.
- Owner-facing prose is deterministic natural Japanese. Internal IDs, provider names, hashes, and URLs remain unchanged in the confirmation block.
- Facts come only from canonical Marketing Engine JSONL state. Do not read `~/.openclaw/state/content-library` and do not invoke OpenClaw.
- A missing metric remains `null` and includes its source reason. Only a successful product-scoped query may render numeric zero.
- `not_mature` means `まだ判断できる時間ではありません`, `unavailable` means `取得できませんでした`, and `unknown` means `現在の証拠では分かりません`.
- Every action message includes the exact native post URL. A Postiz queue state, profile URL, process exit code, or publish token is not publication proof.
- Delivery is keyed by a deterministic message key. Equivalent replay sends zero additional Telegram messages; conflicting replay fails closed.
- Telegram transport is `TelegramClient.from_env().send_text(...)`; a receipt is successful only when it contains returned `message_ids`.
- Do not stop or modify publisher, metrics, intel, or business-outcome schedules in this task.
- All production-code behavior follows RED → observed expected failure → minimal GREEN → full relevant suite.

---

### Task 1: Canonical product-scoped Japanese owner reporting

**Files:**
- Create: `skills/earn/marketing-engine/report/owner_report.py`
- Create: `skills/earn/marketing-engine/report/owner_report_cli.py`
- Create: `skills/earn/marketing-engine/report/test_owner_report.py`
- Create: `skills/earn/marketing-engine/report/install_gate15_launchagents.py`
- Create: `skills/earn/marketing-engine/report/test_install_gate15_launchagents.py`
- Modify: `skills/earn/marketing-engine/test_direct_telegram_transport.py`
- Modify: `specs/27-MARKETING-ENGINE-END-TO-END.md`

**Interfaces:**
- `owner_report.load_jsonl(path: pathlib.Path) -> list[dict]`
- `owner_report.build_events(state_root: pathlib.Path, kind: str, *, product_id: str | None, as_of: datetime.datetime) -> list[dict]`
- `owner_report.render_japanese(event: dict) -> str`
- `owner_report.OwnerReportStore(report_path: pathlib.Path, delivery_path: pathlib.Path)` with `record(event)`, `delivery_for(message_key)`, and `record_delivery(message_key, receipt)`.
- `owner_report.deliver(event: dict, store: OwnerReportStore, send_text: Callable[[str], dict]) -> dict`; equivalent replay returns the first receipt without calling `send_text` again.
- `owner_report_cli.main(argv: list[str] | None = None) -> int` with `sweep --kind`, optional `--product-id`, `--state-root`, `--as-of`, and `--no-send`.
- `install_gate15_launchagents.build_plists(repo_root: pathlib.Path, home: pathlib.Path) -> dict[str, bytes]` returns exactly three plists: `ai.anicca.marketing-owner-events` every 900 seconds for action/checkpoint/incident/experiment sweeps, `ai.anicca.marketing-owner-daily` at 22:00 local for all four product-daily reports, and `ai.anicca.marketing-owner-weekly` Sunday at 21:00 local for the portfolio report.

- [ ] **Step 1: Write failing renderer and isolation tests**

In `test_owner_report.py`, create literal JSONL fixtures for all four products and all six report kinds. The tests must prove these observable behaviors:

```python
def test_action_names_product_and_contains_exact_native_url(): ...
def test_checkpoint_uses_exact_metric_values_and_natural_null_reason(): ...
def test_product_daily_never_borrows_another_products_money(): ...
def test_incident_names_failed_source_and_next_repair(): ...
def test_experiment_does_not_call_not_mature_winner_or_loser(): ...
def test_portfolio_weekly_contains_each_product_once(): ...
def test_rendered_numbers_equal_literal_fixture_facts(): ...
def test_openclaw_legacy_state_is_never_read(): ...
```

The hand-derived fixture must include one exact native URL, one measured social checkpoint, one missed checkpoint, Anicca MRR `20.73`, Honne MRR `0.0` with successful RevenueCat evidence, and unavailable ebook money with a named reason. Expectations are literal Japanese substrings and literal numbers; do not compute expected values with production helpers.

- [ ] **Step 2: Run the renderer tests and capture RED**

Run:

```bash
python3 -m unittest skills/earn/marketing-engine/report/test_owner_report.py -v
```

Expected: FAIL because `owner_report.py` does not exist or the required interfaces are absent. Record the command and relevant failure in the task report before writing production code.

- [ ] **Step 3: Implement the minimal canonical renderer**

Implement the interfaces above. Every event must contain these exact top-level fields before rendering or persistence:

```python
{
    "schema_version": "marketing.owner-report.v1",
    "message_key": "<kind-specific deterministic key>",
    "kind": "<one of six kinds>",
    "product_id": "<product or null for portfolio_weekly>",
    "as_of": "<RFC3339 UTC>",
    "facts": {"<only canonical values and source reasons>"},
    "evidence_refs": ["<canonical state path/key>"],
}
```

Validate product and kind allowlists. Use one immutable account/product relationship from the canonical publication rows; reject cross-product facts. Put human explanation first and append a compact `確認情報` block containing message key, product, native URL when applicable, and evidence references. Do not call an LLM.

- [ ] **Step 4: Run the renderer tests and capture GREEN**

Run the same focused command. Expected: all renderer and product-isolation tests PASS with no warning output.

- [ ] **Step 5: Write failing append-only replay and transport tests**

Add these behavior tests using a temporary directory and a recording sender:

```python
def test_equivalent_replay_records_and_sends_once(): ...
def test_conflicting_same_message_key_fails_closed(): ...
def test_delivery_requires_real_message_ids(): ...
def test_cli_no_send_records_report_without_delivery(): ...
```

Extend `test_direct_telegram_transport.py` so `owner_report_cli.py` is included in the direct-client contract.

- [ ] **Step 6: Run replay/transport tests and capture RED**

Run:

```bash
python3 -m unittest \
  skills/earn/marketing-engine/report/test_owner_report.py \
  skills/earn/marketing-engine/test_direct_telegram_transport.py -v
```

Expected: the new replay/delivery or CLI assertions FAIL for the missing behavior.

- [ ] **Step 7: Implement append-only storage, CLI sweeps, and delivery**

Use `fcntl` locking and canonical sorted JSON for `owner-reports.jsonl` and `owner-report-deliveries.jsonl`. Record the validated event before attempting delivery. `delivery_unknown` must not be blindly retried; record an explicit unknown delivery state. Confirmed failure returns nonzero. A delivered receipt without at least one non-null `message_id` fails closed.

- [ ] **Step 8: Run replay/transport tests and capture GREEN**

Run the Step 6 command. Expected: all tests PASS; identical CLI replay makes zero sender calls after the first recorded receipt.

- [ ] **Step 9: Write failing launchd schedule tests**

In `test_install_gate15_launchagents.py`, assert exact labels, intervals, calendar times, canonical repository paths, `owner_report_cli.py` arguments, writable log paths outside `.openclaw`, and absence of the strings `openclaw`, `daily_report.py`, `weekly_review.py`, and `notify_posts.py` in generated plists. Also assert plan mode reports create/update/no-change without writing.

- [ ] **Step 10: Run schedule tests and capture RED**

Run:

```bash
python3 -m unittest skills/earn/marketing-engine/report/test_install_gate15_launchagents.py -v
```

Expected: FAIL because the installer does not exist.

- [ ] **Step 11: Implement the installer and pass schedule tests**

Implement `--plan` and `--apply`. Writes use a temporary file plus atomic rename. `--apply` installs only the three new owner-report plists, bootstraps/kickstarts only those labels, and read-backs loaded definitions. It must not unload or edit legacy jobs; legacy removal belongs to Gate 16 cutover after shadow evidence.

- [ ] **Step 12: Run the full relevant suite**

Run:

```bash
python3 -m unittest \
  skills/earn/marketing-engine/report/test_owner_report.py \
  skills/earn/marketing-engine/report/test_install_gate15_launchagents.py \
  skills/earn/marketing-engine/report/test_run_contract.py \
  skills/earn/marketing-engine/report/test_run_with_contract.py \
  skills/earn/marketing-engine/report/test_runner_report.py \
  skills/earn/marketing-engine/report/test_scheduled_runner.py \
  skills/earn/marketing-engine/test_direct_telegram_transport.py -v
```

Expected: zero failures and zero errors.

- [ ] **Step 13: Perform non-mutating production probes**

Run `owner_report_cli.py sweep --no-send` once for each of the six kinds against the real canonical state. Verify every active product appears where required, every rendered number matches its source row, the action report contains an exact native URL, and absent data uses a natural reason rather than numeric zero.

- [ ] **Step 14: Install and read back the three schedules**

Run installer `--plan`, inspect the exact diff, then run `--apply`. Verify `launchctl print gui/$(id -u)/<label>` for all three labels and confirm their resolved program arguments point at this repository and canonical state.

- [ ] **Step 15: Perform real Telegram E2E and replay verification**

Run one real event sweep, one real product-daily report for each of the four products, and one real portfolio-weekly report. Capture returned Telegram `message_ids` in evidence. Repeat the identical commands and verify zero additional Bot sends and unchanged delivery-row count.

- [ ] **Step 16: Update the execution SSOT from evidence**

Update Gate 15 in `specs/27-MARKETING-ENGINE-END-TO-END.md` with exact test counts, canonical report/delivery row counts, schedule read-back results, real Telegram message IDs, replay results, and any honest remaining gap. Mark Gate 15 complete only if all six report kinds have a real receipt and ledger equality is proven; otherwise leave it OPEN with the exact missing evidence. Move the active build lane to native social measurement only after Gate 15 is complete.

- [ ] **Step 17: Commit and push**

Stage only files owned by this task and commit:

```bash
git commit -m "feat(marketing): add product-scoped owner reports"
git push origin HEAD
```

The task report must include RED and GREEN output, live schedule labels, Telegram message IDs, replay delivery counts, changed files, commit SHA, and concerns.
