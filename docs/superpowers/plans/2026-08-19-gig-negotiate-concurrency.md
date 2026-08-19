# Gig Negotiate Concurrency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect every new actionable Coconala buyer message within 30 seconds, judge up to two changed threads concurrently, send each authorized reply exactly once, and retain official readback without adding a fifth business lane or a second supervised service.

**Architecture:** The existing Negotiate launchd owner becomes one long-lived parent. A fast producer reads only the newest inbox page, writes a typed inbox event to the existing SQLite outbox before any model work, and dispatches the durable thread identity to two in-process consumer tasks. Consumers collect and judge one direct-message thread each; the existing reply lane keeps the pre-send freshness, click authorization, duplicate fence and official readback. Full four-page reconciliation runs as a lower-priority coroutine and never blocks the producer.

**Tech Stack:** Python 3 standard library (`asyncio`, `sqlite3`, `subprocess`), existing CloakBrowser CDP helpers, existing `connector-outbox.sqlite3`, pytest.

**Spec:** `skills/earn/gig/TODO.md` §0b

## Global Constraints

- Keep exactly four business lanes: Apply, Negotiate, Paid and Storefront.
- Keep one Negotiate launchd label and one long-lived supervised parent; no observer service, fifth lane, new database, broker or dependency.
- The producer interval is at most 30 seconds and durable outbox enqueue happens before semantic/model work.
- Start with exactly two semantic consumers. Each browser operation owns its own CDP page/target; never select `pages()[0]` or require front focus.
- Semantic judgment remains `reply-semantic-agent`, Luna medium, one candidate, tool-disabled, 60-second runner deadline and no slow fallback.
- Existing pre-send freshness, paid-room refusal, near-duplicate suppression, click authorization, official readback and replay idempotency remain mandatory.
- An in-memory `asyncio.Queue` is dispatch only; SQLite remains the restart/replay source of truth.
- Full four-page reconciliation remains present but yields to urgent claimed work.
- No customer body, credential, seller identity or runtime evidence enters the public tree or logs.
- Completion requires a natural buyer-origin → detection → judgment → click → official-readback receipt within five minutes; operating target is at most two minutes.

---

### Task 1: First-page observation and pre-semantic durable identity

**Files:**
- Modify: `skills/earn/gig/scripts/connector_outbox.py`
- Modify: `skills/earn/gig/scripts/coconala_queue_snapshot.py`
- Create: `skills/earn/gig/tests/test_reply_concurrency.py`

**Interfaces:**
- Produces: `coconala_inbox_event_key(thread_id: str, identity_sha256: str) -> str`
- Produces: `direct_inbox_coverage_expression(page_limit: int = 10) -> str`
- Produces CLI mode `direct-inbox-head-only`, returning `collector_mode`, `captured_at`, `inquiries`, `head_only: true`, and `read_only: true` without semantic work or a full-coverage claim.

- [ ] **Step 1: Write the failing identity and bounded-head tests**

Add literal assertions to `test_reply_concurrency.py`:

```python
def test_inbox_event_key_is_thread_bound_and_rejects_non_sha_identity():
    assert outbox.coconala_inbox_event_key("123", "a" * 64) == (
        "coconala:inbox:v1:123:sha256_v1:" + "a" * 64
    )
    assert outbox.validate_coconala_event_key(
        "coconala:inbox:v1:123:sha256_v1:" + "a" * 64, "123"
    ).startswith("coconala:inbox:v1:123:")
    with pytest.raises(ValueError):
        outbox.coconala_inbox_event_key("123", "not-a-sha")
    with pytest.raises(ValueError):
        outbox.validate_coconala_event_key(
            "coconala:inbox:v1:123:sha256_v1:" + "a" * 64, "999"
        )


def test_head_expression_reads_one_page_without_changing_full_expression():
    assert snapshot.direct_inbox_coverage_expression() == snapshot.DIRECT_INBOX_COVERAGE_EXPRESSION
    head = snapshot.direct_inbox_coverage_expression(1)
    assert "pageLimit=1" in head
    assert "pageLimit=10" not in head
    with pytest.raises(ValueError):
        snapshot.direct_inbox_coverage_expression(0)
```

- [ ] **Step 2: Run RED**

Run: `python3 -m pytest -q skills/earn/gig/tests/test_reply_concurrency.py`

Expected: FAIL because both public helpers are absent.

- [ ] **Step 3: Add the typed inbox event**

In `connector_outbox.py`, add a strict `_INBOX_EVENT` grammar beside `_MESSAGE_EVENT`, build the exact key above, include it in `validate_coconala_event_key`, and classify it as a normal—not estimate—event. Do not change the schema or add a table.

- [ ] **Step 4: Add the bounded head collector mode**

In `coconala_queue_snapshot.py`:

1. Add `direct_inbox_coverage_expression`; accept only real integers `1..MAX_PAGINATION_PAGES` and preserve the existing expression byte-for-byte at the default.
2. Allow `inspect_page`/`inspect_message_page` to receive a custom coverage expression and to skip full-coverage validation only when explicitly requested.
3. Add parser choice `direct-inbox-head-only`.
4. In that mode, open one owned `DefaultTab`, evaluate one-page coverage, normalize cards with `inquiries_from_dom`, and write a snapshot with `head_only: true`, `semantic_ssot: false`, and no message body. Do not call `SemanticJudge`; do not claim `coverage_complete`.

- [ ] **Step 5: Run GREEN and regressions**

Run:

```bash
python3 -m pytest -q skills/earn/gig/tests/test_reply_concurrency.py
python3 -m pytest -q skills/earn/gig/tests/test_reply_semantic_fast_route.py
python3 -m py_compile skills/earn/gig/scripts/connector_outbox.py skills/earn/gig/scripts/coconala_queue_snapshot.py
```

Expected: all pass; no warning or error output.

- [ ] **Step 6: Commit**

```bash
git add skills/earn/gig/scripts/connector_outbox.py skills/earn/gig/scripts/coconala_queue_snapshot.py skills/earn/gig/tests/test_reply_concurrency.py
git commit -m "feat(gig): claim new buyer messages before semantics"
```

---

### Task 2: One-thread semantic worker using the existing effect lane

**Files:**
- Modify: `skills/earn/gig/scripts/coconala_queue_snapshot.py`
- Modify: `skills/earn/gig/scripts/reply_detector.py`
- Modify: `skills/earn/gig/tests/test_reply_concurrency.py`

**Interfaces:**
- Consumes: exact `action_id`, typed inbox `event_key`, thread id and observed head identity already stored in `ConnectorOutbox`
- Produces CLI mode `direct-thread-only --talkroom-id <id>` with exactly one inquiry and `semantic_ssot: true`
- Produces: `run_targeted_thread(args, *, action_id: int, inbox_event_key: str, thread_id: str, evidence: Path, run_id: str) -> dict[str, Any]`
- Produces: a fresh, complete `orders-only` receipt and paid-room fence collected after semantics and immediately before any reply or estimate effect

- [ ] **Step 1: Write the failing targeted-thread test**

Create a fixture whose direct thread ends with buyer message `buyer-2`, whose semantic receipt authorizes body `回答です`, and whose fake lane result contains one officially verified reply. Assert:

```python
result = detector.run_targeted_thread(
    args, action_id=action_id, inbox_event_key=inbox_event_key,
    thread_id="123", evidence=tmp_path / "evidence", run_id="run-1"
)
assert result["status"] == "completed"
assert result["replied"] == 1
assert result["thread_id"] == "123"
assert result["official_readback"] == 1
assert all("123" in command for command in recorded_collect_commands)
```

The fake scripts must write the complete snapshot/queue/lane JSON shapes consumed by the real function. Assert filesystem results and returned values, not mock call counts alone.

- [ ] **Step 2: Run RED**

Run: `python3 -m pytest -q skills/earn/gig/tests/test_reply_concurrency.py::test_targeted_thread_reaches_official_readback`

Expected: FAIL because the targeted collector and worker do not exist.

- [ ] **Step 3: Add `direct-thread-only`**

Validate the supplied thread id with the existing direct-message route grammar, open exactly `https://coconala.com/mypage/direct_message/<id>` in its own `DefaultTab`, call `direct_message_event` with the existing semantic judge and official-context provider, and emit one inquiry. Preserve message identity, buyer timestamp, semantic receipt and estimate fields. Invalid route, missing identity or semantic failure remains fail-closed.

- [ ] **Step 4: Extract the targeted worker from the existing pass**

`run_targeted_thread` must validate that `action_id`, `inbox_event_key` and `thread_id`
name the same pending durable action. It must then reuse one shared effect pipeline, also called
by the existing full pass, in this order:

1. `direct-thread-only` collection;
2. `reply_queue.py build` and `reply_queue.py enqueue`, confirming the collected message event
   coalesces into the supplied `action_id` before any marketplace effect;
3. explicit semantic-action allowlist validation; unknown or failed actions remain pending;
4. a fresh `direct-inbox-head-only` re-read proving the supplied inbox identity is still current;
5. a fresh `orders-only` collection with complete coverage, followed by `build-paid`; do not
   accept a caller-supplied, cached or stale registry;
6. requested-estimate effect/readback when required, otherwise existing
   `reply_lane.py --max-model-calls 0` for normal replies;
7. return only bounded counts and verified event metadata. A positive `replied` count without
   matching verified official events is recoverable pending/failure, never `completed`.

Extract the queue/effect/readback sequence from the existing full-pass block rather than copying
it into a second 300-line implementation. The full pass and targeted pass must call the same
function for build/enqueue, estimate ordering, paid fence, reply lane and readback classification.

If semantic judgment is one of the explicitly supported intentional no-send actions, revalidate
the exact head identity, claim only the supplied unchanged action/revision and close it through
the existing `nothing_to_say` closure. A catch-all semantic action must never close an action.
If the head identity changed, semantic judgment failed, orders coverage is incomplete, or the
fresh paid proof is absent/stale, leave the exact action pending for bounded retry; never close it
as success and never send.

- [ ] **Step 5: Add replay and no-send tests**

Add two behavior tests:

```python
def test_targeted_replay_has_zero_second_effect(...):
    first = detector.run_targeted_thread(...)
    second = detector.run_targeted_thread(...)
    assert first["official_readback"] == 1
    assert second["replied"] == 0
    assert second["duplicate_effect"] == 0


def test_intentional_no_send_closes_claim_without_reply(...):
    result = detector.run_targeted_thread(...)
    assert result["replied"] == 0
    assert result["closed_without_send"] == 1
    assert ConnectorOutbox(database, manifest).pending_actions() == []
```

Also add negative tests proving: wrong inbox identity cannot close an action; a newer head identity
prevents send/closure; an unknown semantic action remains pending; orders proof is collected after
semantics and before normal or estimate effect; stale/incomplete orders proof blocks both effect
paths; and `replied > 0` without matching official readback cannot return `completed`.

- [ ] **Step 6: Run GREEN and focused regressions**

Run:

```bash
python3 -m pytest -q skills/earn/gig/tests/test_reply_concurrency.py
python3 -m pytest -q skills/earn/gig/tests/test_reply_semantic_fast_route.py
python3 -m py_compile skills/earn/gig/scripts/reply_detector.py skills/earn/gig/scripts/coconala_queue_snapshot.py
```

- [ ] **Step 7: Commit**

```bash
git add skills/earn/gig/scripts/reply_detector.py skills/earn/gig/scripts/coconala_queue_snapshot.py skills/earn/gig/tests/test_reply_concurrency.py
git commit -m "feat(gig): process one changed buyer thread"
```

---

### Task 3: One supervised producer–consumer runtime

**Files:**
- Modify: `skills/earn/gig/scripts/reply_detector.py`
- Modify: `skills/earn/gig/config/launchd-jobs.json`
- Modify: `skills/earn/gig/tests/test_reply_concurrency.py`

**Interfaces:**
- Consumes: head snapshots and `run_targeted_thread`
- Produces: `async supervise_replies(args, *, probe, worker, reconcile, stop) -> None`
- Production CLI: `reply_detector.py --continuous --poll-seconds 30 --workers 2`

- [ ] **Step 1: Write RED concurrency tests**

Use real `asyncio.Event` barriers and literal timestamps. The first fake worker waits; the probe emits a second identity before that barrier is released. Assert the second durable claim exists before worker 1 completes and both worker start events occur concurrently:

```python
assert claim_times["identity-2"] < finish_times["identity-1"]
assert max(worker_started.values()) < min(worker_finished.values())
assert max_active_workers == 2
```

Add restart coverage by pre-populating an inbox event in SQLite, starting the supervisor with the same head identity, and asserting the pending action is dispatched once. Add replied-event coverage asserting a duplicate head identity creates no second effect.

- [ ] **Step 2: Run RED**

Run: `python3 -m pytest -q skills/earn/gig/tests/test_reply_concurrency.py -k 'slow or restart or workers'`

Expected: FAIL because `supervise_replies` is absent.

- [ ] **Step 3: Implement the standard-library supervisor**

Use one `asyncio.Queue[InboxWork]`, one producer task, two consumer tasks and one reconciliation task.

- Producer: every `poll_seconds`, execute the head collector with `asyncio.to_thread`; for each unread row with a valid identity, call `ConnectorOutbox.enqueue(coconala_inbox_event_key(...))` before `queue.put`. Dispatch the returned `action_id`, exact event key, thread id and identity together. Skip an already terminal/replied duplicate. A pending duplicate after restart is re-dispatched with the same durable tuple.
- Consumers: keep an in-memory set only to suppress duplicate simultaneous dispatch; call `run_targeted_thread` with the exact durable tuple through `asyncio.to_thread`; always release the in-memory marker in `finally`.
- Reconciler: when the urgent queue and in-flight set are empty, run the existing full pass at the existing five-minute reconciliation cadence. Producer and consumers continue independently while it runs.
- Shutdown: SIGTERM/SIGINT sets `stop`; cancel tasks, await them, release the lane lock and leave SQLite claims recoverable. Do not delete state.

- [ ] **Step 4: Make launchd supervise the parent**

For the existing `ai.anicca.hf-gig-reply-detector` job only:

- append `--continuous --poll-seconds 30 --workers 2`;
- replace `StartInterval` with `KeepAlive: true`;
- keep `RunAtLoad: true` and `ThrottleInterval: 30`;
- do not change Apply, Paid, Storefront, release or browser jobs.

- [ ] **Step 5: Run GREEN and manifest regression**

Run:

```bash
python3 -m pytest -q skills/earn/gig/tests/test_reply_concurrency.py
python3 -m pytest -q skills/earn/gig/tests/test_reply_semantic_fast_route.py
python3 -m json.tool skills/earn/gig/config/launchd-jobs.json >/dev/null
python3 -m py_compile skills/earn/gig/scripts/reply_detector.py
git diff --check
```

Expected: all pass. The semantic-fast-route manifest test must now assert Negotiate `KeepAlive: true`, no `StartInterval`, exact CLI values `30` and `2`, and unchanged intervals for the other lanes.

- [ ] **Step 6: Commit**

```bash
git add skills/earn/gig/scripts/reply_detector.py skills/earn/gig/config/launchd-jobs.json skills/earn/gig/tests/test_reply_concurrency.py skills/earn/gig/tests/test_reply_semantic_fast_route.py
git commit -m "feat(gig): keep negotiate discovery live during replies"
```

---

## Primary-agent rollout gate

After all three reviewed tasks:

1. Run the complete gig test suite and classify every failure against the pre-change baseline.
2. Run gitleaks/PII changed-path checks; customer content and runtime evidence must be zero.
3. Obtain fresh Sol Advisor verdict on the full diff; fix every Critical/Important finding and re-review.
4. Merge/push to `main`, build an immutable release, install only the Negotiate job, and read back the loaded plist argv/environment.
5. Observe one natural no-op/reconciliation cycle: process stays resident, head polling continues, other three lane PIDs/schedules remain independent, model calls are zero when nothing changed.
6. Observe the next natural actionable buyer message and record buyer origin, durable claim, semantic start/end, click and official readback. Require at most five minutes, target at most two minutes, second wake/effect zero.
7. Update `skills/earn/gig/TODO.md` only from those receipts; do not publish an after-speed claim before step 6.
