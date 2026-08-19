# Identity fix report

STATUS: DONE

## Scope

Owned files changed:

- `skills/earn/gig/scripts/coconala_queue_snapshot.py`
- `skills/earn/gig/tests/test_reply_concurrency.py`
- this report

No other worktree or deployment was touched. The existing
`DIRECT_MESSAGE_EXPRESSION` definition and its module-load enhancement wrapper
remain in place and unchanged.

## RED

The behavior test was added before the production change and run with:

```text
uv run --with pytest==9.0.3 --with websockets pytest -q skills/earn/gig/tests/test_reply_concurrency.py -k head_and_direct_thread_normalized_messages_share_identity_sha
```

Observed failure: **1 failed, 23 deselected** with
`KeyError: 'last_message_identity_sha256'` from the head-normalized row. This
confirmed the old head path did not produce the thread-compatible identity.

## GREEN and verification

- Targeted identity test: **1 passed, 23 deselected**.
- `uv run --with pytest==9.0.3 --with websockets pytest -q skills/earn/gig/tests/test_reply_concurrency.py`: **24 passed**.
- `uv run --with pytest==9.0.3 --with websockets pytest -q skills/earn/gig/tests/test_reply_semantic_fast_route.py`: **8 passed**.
- `python3 -m py_compile skills/earn/gig/scripts/coconala_queue_snapshot.py skills/earn/gig/tests/test_reply_concurrency.py`: **pass**.
- `git diff --check`: **pass**.

## Implementation

- The direct inbox expression now exposes only raw `message_id`, `sent_at`,
  and `body` identity fields in the in-memory DOM result; preview hashing is
  unchanged. Numeric timestamps are converted to UTC ISO text in the browser.
- `message_identity_sha256` is the single Python builder. It hashes the
  canonical `message_id + body` pair when an id is valid, otherwise canonical
  UTC `sent_at + body`; incomplete observations return no identity.
- Both `inquiries_from_dom` and `direct_message_event` call that builder.
  The head-only projection still allowlists only bounded metadata, including
  the resulting SHA, and never persists raw identity fields or body text.

## Judgment and concerns

- An untrusted/precomputed DOM SHA is no longer accepted by either normalizer;
  the current raw fields must pass the shared builder. This prevents the old
  JavaScript schema from being compared with the new thread schema.
- Live authenticated Coconala markup was not exercised in this isolated test
  lane. If a live Vue message lacks all of `message_id/messageId/id` and
  `sent_at/sentAt/createdAt`, the builder fails closed and targeted dispatch
  remains pending until a fresh identity is observable.
- No push or deploy was performed, per task constraint.
