# Affiliate local money loop handover

- Spec SSOT: `/Users/anicca/anicca-project/.worktrees/affiliate-life-manager-spec/docs/affiliate-agent/AFFILIATE-AGENT-SSOT.md`; resume from `Remaining autonomous money-loop work — canonical order` and its `Current execution cursor`.
- Repository/worktree: `/Users/anicca/anicca-project/.worktrees/affiliate-life-manager-spec`; branch `docs/affiliate-life-manager-spec`; verified spec commit `b01f4e1ca`; pushed to both `origin` and `canonical`. Worktree clean.
- Installed runtime: `/Users/anicca/.local/share/life-manager/affiliate/current` → release `22e8876ad561eef85827a73fa9f34dc534d7e771`, byte-identical to that commit. All six launchd owners loaded, 600-second job intervals, last exit `0`, browser owners running. **Reinstall after ANY commit touching `skills/affiliate`**: `AFFILIATE_LANDING_ROOT=/Users/anicca/anicca-project/.worktrees/affiliate-foundation-prod ./skills/affiliate/scripts/install-release.sh` (needs a clean checkout and HEAD == release SHA). Invariant: `git diff <installed-release> HEAD -- skills/affiliate` must be empty.
- Test baseline: `69/69` green from `skills/affiliate` via `python3 -m unittest $(ls tests/test_*.py | sed 's#/#.#;s#\.py##')`. Do not tolerate a red baseline; two long-red tests were stale mocks and were repaired.

## Cursor: M2.1-P is MET at ten placements. Next is E1-H, the first real transaction.

The canonical ledger holds **ten** placements, each with one dedicated PartnerStack link, one owned article, one X post, and one public readback. All ten `x-posts` receipts are `X_POST_PUBLIC_READBACK / LIVE`; no effect fence is open and no duplicate post exists.

**Money is still exactly zero and must be reported that way.** All ten placements carry a provider-measured click denominator of `0`, `transaction_count=0` across pending/approved/paid/reversed, empty approved net, and `UNKNOWN` cash cost. Zero of the USD 10,000.

**The binding constraint is demand, not placement count.** Ten live dedicated links with a provider-confirmed zero-click denominator means ten more of the same shape would still multiply zero. Growing the portfolio further before a channel produces measured qualified traffic is motion without money.

## Five production fixes this session, each verified on a real installed wake

1. `7fef8d02c` — `advance_tts_api_publication` re-drove a full X timeline scrape every 10-minute wake for a settled placement, so any transient scrape failed the whole wake. Terminate on content equality. Also records `publication_failure_detail`, mirroring the distribution handler.
2. `9e482de48` — that fix removed the only recurring liveness proof, so `sweep_publication_liveness` re-verifies every live receipt once per `Asia/Tokyo` day through the existing publisher, which cannot post while a receipt carries a public URL. A failed sweep deliberately never mutates the ledger: one bad scrape must not drop a real placement.
3. `7d2e019b0` — a source refresh recomposed already-published campaigns, spending scarce daily composition passes on work that can never publish. Skip any plan whose placement receipt is `LIVE`.
4. `e63503a5d` + `f4b8109c0` — recomposition also left published campaigns' publication and policy receipts stale, and both checks ran before the completed check and `return` rather than `continue`, so one live campaign blocked every campaign sorted after it. **General rule now in the spec: a live placement is terminal, so no later receipt drift about it may gate a different campaign.**
5. `22e8876ad` — `flush_telegram` was the only effect owner with no resume path, so a single failed send wedged owner reporting permanently (silent 00:54–01:18 JST). Resume under the same identity like every other owner; `event_uuid` dedupe still prevents resending a delivered message.

## Proven safety properties (do not "fix" these)

- `XPostError: X effect is ambiguous; retry will reconcile timeline` is **safe by construction**. `start_effect` refuses a second effect while one is `EFFECT_STARTED` (`job_journal.py:69`), so a retry can only reconcile or fail closed. Observed live: job ended `VERIFIED` at `attempt 2` with `sequence` still `1`, proving exactly one post. Never "fix" this by retrying the compose branch.
- The publication fence is real: placement ten's landing deploy failed on an unrelated `next/font/google` error, the article stayed `404`, and the loop refused to post. An X post may never point at a non-live article.

## Known open items

- Two unresolved `systeme-io` effects (`PROVIDER_LOGIN`, `PROVIDER_EMAIL_VERIFY` at attempt 10) are the second-provider CAPTCHA blocker. They do not touch the ElevenLabs money path. This is M2.2 work.
- Composition budget is `131072` tokens per JST day with a `32768` reservation, so at most four sealed compositions per day.
- The landing deploy can fail transiently on Google Fonts; the loop cannot retry a GitHub Actions run itself.

## First safe resume action

Fetch, confirm clean HEAD/upstream and an empty `git diff <installed-release> HEAD -- skills/affiliate`, then read `placement-ledger.json` and the latest `logs/loop.out.log` receipt. Do not add placement eleven to chase the target. The highest-risk unmet gate is that ten placements produce zero measured clicks, so the next real work is a measurable acquisition channel (M2.4) and E1-H's first provider transaction. Never post, compose, or publish by hand; trigger the existing launchd owners and read back.
