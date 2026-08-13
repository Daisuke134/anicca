# Capafy Japanese Owner Reporter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing Capafy goal monitor render and deliver one truthful, period-keyed Japanese owner report for hourly, morning, daily-close, and business-event runs.

**Architecture:** Keep the canonical company projection as the only business-fact source. Add one deterministic Python boundary that validates a report envelope, derives a Japanese message and delivery key, and atomically records a bounded delivery history; the existing shell monitor supplies current/previous projections and sends the returned body through the existing Telegram sender. No LLM, new daemon, database, or duplicate reporting pipeline is introduced.

**Tech Stack:** Python 3 standard library, Bash, JSON, pytest, existing `capafy_event_projection.py`, existing Telegram sender.

## Global Constraints

- Source remains under `skills/earn/capafy-marketing`; runtime files under `~/.openclaw` are not source SSOT.
- One canonical projection supplies money, freshness, Builder, Marketer, repair, and public URLs.
- Output is natural Japanese and never exposes raw enums, stack traces, private paths, credentials, or literal template tokens.
- `hourly`, `morning`, and `daily_close` deliver at most once per period key even if an event report is delivered between retries; identical business content must not suppress a later period.
- `event` delivery keys use the immutable event identity and event reason, so the same event retries once while distinct sale, publish, repair-close, and unresolved events remain distinct.
- Zero-dollar orders remain commercially unknown; the report never calls them trials or subscriptions.
- Delivery state writes atomically and retains the most recent 256 successful keys; a failed Telegram send records nothing.
- Existing English `capafy_outcome.py render` and public dashboard contracts remain backward compatible.
- Production code soft target: two files and at most 100 net new lines; keep validation tables/data compact, and let tests exceed this only for the seven required golden states.

---

### Task 1: Deterministic Japanese report and period-keyed delivery

**Files:**
- Create: `skills/earn/capafy-marketing/scripts/capafy_owner_report.py`
- Modify: `skills/earn/capafy-marketing/capafy-goal-monitor.sh`
- Modify: `skills/earn/capafy-marketing/tests/test_capafy_goal_monitor_report.py`

**Interfaces:**
- Consumes: a JSON envelope with `schema_version`, `report_kind`, `period_key`, `company_state`, `previous_company_state`, and optional `event_reason`.
- Produces: `render` stdout as Japanese plain text; `delivery-key` stdout as a stable non-secret key; `delivered` exit `0` when that key already exists and exit `1` otherwise; `record-delivery --message-id N` atomically appends one successful record to the bounded state.
- Environment used by the shell: `CAPAFY_REPORT_KIND` (`hourly|morning|daily_close|event`) and optional `CAPAFY_REPORT_PERIOD_KEY`. An unset kind defaults to `morning`; default keys are JST `YYYY-MM-DDTHH` for hourly, `YYYY-MM-DD` for morning/daily close, and `<event_reason>:<last_event_id>` for event.

- [x] **Step 1: Add the seven failing golden-message tests**

Add parameterized fixtures for `healthy`, `unchanged`, `stale_metrics`, `sale`, `published`, `repair_closed`, and `unresolved`. Each exact message asserts a Japanese heading, money summary, freshness, Builder, Marketer, repair/next action, Capafy listing URL, Reel/content URL, and dashboard URL. The unresolved fixture contains a private-path-shaped source error and raw enum inputs, then asserts none of these tokens appear:

```python
FORBIDDEN = (
    "reach_observing", "commercial_ready", "repair_started", "unresolved",
    "/Users/", "Traceback", "{{", "}}", "trial", "subscription",
)

@pytest.mark.parametrize("case", GOLDEN_CASES)
def test_japanese_owner_report_golden_cases(case):
    result = owner_report("render", case.envelope)
    assert result.returncode == 0, result.stderr
    assert result.stdout == case.expected
    assert not any(token in result.stdout for token in FORBIDDEN)
```

- [x] **Step 2: Run the golden tests and confirm RED**

Run:

```bash
python3 -m pytest -q skills/earn/capafy-marketing/tests/test_capafy_goal_monitor_report.py -k 'japanese_owner_report'
```

Expected: collection or invocation fails because `capafy_owner_report.py` does not exist.

- [x] **Step 3: Add failing period-key and delivery-ledger tests**

Cover all four report kinds, invalid/missing kinds and keys, same-period retry, the next unchanged hourly period, an event inserted between hourly retries, two distinct event identities, legacy delivery-state migration, corrupt-state fail-closed behavior, a failed-send no-record assertion at the shell boundary, mode `0600`, atomic JSON validity, and retention at exactly 256 entries. The key assertions are:

```python
assert key(hourly("2026-08-13T17")) == "hourly:2026-08-13T17"
assert key(hourly("2026-08-13T18")) == "hourly:2026-08-13T18"
assert key(event("sale", "capafy:order.received:2026-08-13")) == (
    "event:sale:capafy:order.received:2026-08-13"
)
assert already_delivered("hourly:2026-08-13T17", state_after_event) is True
```

- [x] **Step 4: Run delivery tests and confirm RED**

Run:

```bash
python3 -m pytest -q skills/earn/capafy-marketing/tests/test_capafy_goal_monitor_report.py -k 'period or delivery'
```

Expected: the current projection-only delivery state cannot distinguish periods and cannot retain non-adjacent keys.

- [x] **Step 5: Implement the minimal deterministic helper**

Create `capafy_owner_report.py` with four commands. Reuse `capafy_outcome.validate_outcome(company_state)` before rendering. Map every supported raw state to Japanese and map unknown values to `不明`; never echo an unknown raw value. Compute change reasons in this priority order: explicit `event_reason`, paid/order increase, new public Reel, prior active incident now absent, current active incident, unchanged projection, healthy status. Render fixed sections in this order:

```text
Capafy 時間レポート（2026-08-13 17時）
売上: 累計5件（有料2件）、総売上$19.98、受取待ち$8.00、入金済み$0.00、MRR $0.00。
収支: 計測コスト$4.78、記録済みコスト差引後-$4.78。
データ鮮度: 売上は最新。商品在庫、Instagramアカウント、マーケティング、コストは古いため要更新。
Builder: 公開21件、審査中0件、下書き2件、却下9件。
Marketer: @capafy.skills8m4q2z。公開Reelを確認済み。閲覧121、いいね0、コメント0、計測クリック1。
修復: Marketerの問題は未解決。次回確認は2026-08-07 13:50 JST。
次の対応: MarketerがInstagramの実ブラウザ状態を再取得する。
Capafy: https://capafy.ai/agent/5051239796
Reel: https://www.instagram.com/reel/DbhCWLhorxy/
ダッシュボード: https://capafy-skills-daily.netlify.app/company/
```

Use `json.dumps`, `tempfile.mkstemp`, `os.fsync`, and `os.replace` for state. Store only `delivery_key`, `projection_id`, `telegram_message_id`, and UTC `delivered_at`; reject non-numeric message IDs and malformed/private envelope data.

- [x] **Step 6: Integrate the existing goal monitor**

In `capafy-goal-monitor.sh`, read the previous `company_state` before appending the current report history, derive or accept the report kind/key, write one private temporary envelope, and call the helper. Replace the projection-only comparison with:

```bash
DELIVERY_KEY="$($PY "$OWNER_REPORT" delivery-key < "$OWNER_REPORT_ENVELOPE")" || exit 2
if ! "$PY" "$OWNER_REPORT" delivered --state "$DELIVERY_STATE" --key "$DELIVERY_KEY"; then
  BODY="$($PY "$OWNER_REPORT" render < "$OWNER_REPORT_ENVELOPE")" || exit 2
  SEND_RESULT="$(bash "$TELEGRAM_SENDER" "$BODY" 2>&1)" || exit 1
  MESSAGE_ID="$(printf '%s\n' "$SEND_RESULT" | sed -nE 's/.*MSGID=([0-9]+).*/\1/p' | tail -1)"
  [ -n "$MESSAGE_ID" ] || exit 1
  "$PY" "$OWNER_REPORT" record-delivery --state "$DELIVERY_STATE" \
    --key "$DELIVERY_KEY" --projection-id "$PROJECTION_ID" --message-id "$MESSAGE_ID" || exit 2
fi
```

Preserve the existing incident-on-send-failure behavior. Do not install or change launchd schedules in this task.

- [x] **Step 7: Run focused and full verification**

Run:

```bash
python3 -m pytest -q skills/earn/capafy-marketing/tests/test_capafy_goal_monitor_report.py
python3 -m pytest -q skills/earn/capafy-marketing/tests
python3 -m py_compile skills/earn/capafy-marketing/scripts/capafy_owner_report.py
bash -n skills/earn/capafy-marketing/capafy-goal-monitor.sh
git diff --check
```

Expected: all PASS. Also render the current production projection read-only and assert Japanese text contains `累計5件（有料2件）`, `$19.98`, the Capafy skill, Reel, and dashboard URLs, while the forbidden-token set is absent.

- [x] **Step 8: Fresh adversarial review and one correction round**

Review the exact commit read-only. Attack period collisions, timezone boundaries, event-between-period retries, state truncation, legacy/corrupt state, failed-send recording, duplicate Telegram, raw enum/path/trace leakage, missing URLs, unknown paid count, zero-dollar attribution, false repair closure, and English leakage. Send Critical/Important findings back to the same implementer once, then rerun Step 7 without a second review cycle.

- [x] **Step 9: Production cross-run and close the spec item**

Run the existing goal monitor with a unique test hourly period key and the real Telegram sender; require exit `0`, a real `MSGID`, and Japanese 5 / 2 / `$19.98` text. Repeat the identical period key and require no new message and byte-identical delivery state. Run the next hourly period key with unchanged projection and require exactly one new message. Update the authoritative Capafy spec with commits, test counts, message IDs, delivery-state hashes, and remaining stale sources; commit and push before Item 6.

## Closure evidence

- Implementation commits: `e8b0265f0`, `2786983ad`, `ffdfdf3ef`, and `90216887c`; merged as `455424e86`.
- Fresh parent verification: all Marketing tests `358 passed`; adversarial counterexamples `7 passed`; Python compile, Bash syntax, and diff checks passed.
- The single fresh adversarial review reproduced duplicate concurrent sends/lost delivery updates, spoofed sender success, unsafe URL/handle leakage, false event reasons, unsafe state modes, and invalid calendar periods. The same Luna implementer corrected them; no second review cycle was run.
- Production launchd runs 9–11 all exited `0`. `hourly:2026-08-13T17` delivered Telegram `15899`; its identical retry preserved the one-row delivery-state SHA-256 `846a6ca42222ac580ddfd76c5239a195beb0a529ef0a0bd3ffc27105b65789fc`; `hourly:2026-08-13T18` delivered Telegram `15900` and produced the two-row SHA-256 `d812ae6a16c9ffc3dd5b2200eac40e173939b54c039ec1cc6cadfafa2918e4dc`.
- The real Japanese body renders 5 lifetime orders, 2 paid orders, `$19.98`, freshness, Builder, Marketer, repair/next action, listing, Reel/content, and dashboard URLs with no forbidden raw token. The canonical revenue ledger stayed at 409 rows with SHA-256 `2729ed05e5504f9c6c26f684dca27fd35cdd2bc02d670a4971c0ffd5c6dc023e` across all three runs.
- Remaining truthful stale sources are inventory, Instagram account, Marketing, and cost. Scheduling remains deliberately deferred to Item 6.
