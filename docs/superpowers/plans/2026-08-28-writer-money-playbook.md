# Writer Money Playbook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore Writer publication, require a verified GPT Image 2 headline for every article, learn transferable mechanisms from profitable writers, and scale only from received writing revenue.

**Architecture:** Keep GitHub main as the only code source and production on exact immutable releases. The model researches and judges winner mechanisms through natural-language prompts; deterministic code owns schemas, hashes, locks, deduplication, accounting, and provider readback. Execute W0-W21 sequentially from `docs/ARTICLE-LAUNCH-TODO.md`; Q/A tables in the consolidation spec are history and dependency evidence.

**Tech Stack:** Bash, Python standard library, SQLite, JSON/JSONL receipts, launchd via `lm-loop`, CloakBrowser CDP, GPT Image 2, provider-native APIs.

## Global Constraints

- Work only in a temporary worktree from current `origin/main`; merge by PR before cutting a release.
- Never edit or restart another loop, browser profile, state owner, plist, or production release.
- Never invoke a publisher from the primary session; kickstart and observe the installed launchd loop.
- Every production apply requires `lm-loop doctor all` and `lm-loop status all` before/after snapshots. Only the
  explicitly targeted Writer labels may change release/state/plist/argv; sibling receipts may only advance through
  the same owner to a valid terminal result with no new failure or duplicate effect.
- Model judgment uses the canonical natural-language prompts; regex is limited to fixed-format parsing.
- Credentials and tenant state remain outside Git and outside immutable releases.
- Received payout is money; views, likes, drafts, pending, available, and projections are not.
- No cadence increase before seven terminal runs, native headline readback, replay-zero, and first received payment.

---

### Task 1: Recover legacy Writer lock safely

**Files:**
- Modify: `skills/writer-agent/article-daily.sh`
- Test: `skills/writer-agent/tests/article-daily-lock-recovery.sh`

**Interfaces:**
- Consumes: legacy lock directory with `owner.pid` and optional `owner.start`
- Produces: acquired current lock or terminal JSON receipt with no publication effect

- [x] Write a failing fixture proving a dead legacy PID-only lock currently returns success without acquiring the lock.
- [x] Run the fixture and preserve the exact RED output.
- [x] Implement the minimum identity-stable quarantine path and nonzero terminal failure for unsafe ambiguity.
- [x] Run the lock fixture, Writer focused tests, and `bash -n skills/writer-agent/article-daily.sh`.
- [x] Save `lm-loop doctor all` and `lm-loop status all` before snapshots with every label, release, argv, state root, and terminal receipt.
- [x] Commit, push, open a PR, obtain fresh read-only review, merge, and cut a main-derived immutable release.
- [x] Apply `article-daily`, `article-resume`, and `article-healthcheck` one at a time with `LIFE_MANAGER_APPLY_TARGET`; read back each exact release SHA, argv, state root, and terminal receipt before applying the next label.
- [x] Save the same all-loop after snapshots and fail the task unless only those three Writer labels changed and every sibling release, state root, and plist/argv is unchanged. Accept a sibling receipt change only as a valid natural terminal advancement from the same owner with no new failure or duplicate effect.

### Task 2: Prove one complete headline-backed article run

**Files:**
- Modify: `skills/writer-agent/article-daily.sh`
- Create: `skills/writer-agent/scripts/generate_headline_image.py`
- Modify: `skills/writer-agent/scripts/media_create_once.py`
- Modify: `skills/writer-agent/SKILL.md`
- Test: `skills/writer-agent/tests/test_media_create_once.py`
- Test: `skills/writer-agent/tests/article-run-completion.sh`

**Interfaces:**
- Consumes: installed Writer release and external state root
- Produces: article artifacts and headline receipt `{request_id,request_model,prompt_sha256,response_sha256,file_sha256,width,height,alt,rights}`

- [ ] Add a RED case to `test_media_create_once.py` proving completion currently accepts a missing or unverified headline receipt.
- [ ] Implement the deterministic Image API owner with `model=gpt-image-2-2026-04-21`; capture `x-request-id` and hash the exact response before decoding.
- [ ] Extend `media_create_once.py` receipts with prompt hash, request model, request ID, response hash, alt text, and rights provenance.
- [ ] Apply the exact merged release to Writer labels only.
- [ ] Kickstart the installed loop once and read back Note JA, Substack JA/EN, and X Article JA.
- [ ] Kickstart a second time and prove article, ledger, and notification duplicates are zero.

### Task 3: Add winner observation and prompt contracts

**Files:**
- Create: `skills/writer-agent/config/winner-observation.schema.json`
- Modify: `skills/writer-agent/article-daily.sh`
- Modify: `skills/writer-agent/SKILL.md`
- Test: `skills/writer-agent/tests/test_winner_observation_contract.py`

**Interfaces:**
- Consumes: current web sources, official platform facts, article history, money history
- Produces: one validated observation and one single-variable experiment proposal per run

- [ ] Write RED fixtures for missing source URL, fact/inference mixing, copied source text, unknown income, and multiple changed fields.
- [ ] Implement fixed-format validation and keep transfer judgment in the model prompt from `proven-writer-money-playbook.md`.
- [ ] Make `SKILL.md` reference the new playbook and remove or explicitly historicalize conflicting active-six, reusable-series-cover, and in-body-infographic instructions.
- [ ] Insert the five canonical prompts at the existing generation and learning boundaries without a second agent/router.
- [ ] Run focused tests and verify prompt output is absent from public logs and Telegram.
- [ ] Commit and merge through the standard loop-development flow.

### Task 4: Join received money to exact articles

**Files:**
- Modify: `skills/writer-agent/scripts/money_sync.py`
- Modify: `skills/writer-agent/scripts/money_ledger.py`
- Create: `skills/writer-agent/tests/test_money_sync.py`

**Interfaces:**
- Consumes: official purchase, fee, refund, payout, artifact, and run receipts
- Produces: unique net received writing revenue rows with original currency and separate FX receipts

- [ ] Add RED cases for pending/available misclassification, duplicate payout, unmatched artifact, refund, and software revenue mixed into writing revenue.
- [ ] Implement the smallest joins using existing money ledger tables and unique provider receipt IDs.
- [ ] Verify a missing provider source is `unknown`, not zero, and currencies are not silently converted.
- [ ] Add `fx_receipts` keyed by `payout_receipt_id` with source URL, rate date, retrieval time, source currency/amount/decimals, source units per EUR, USD per EUR, USD micros, and response SHA.
- [ ] Compute `(source_amount / 10^decimals) / source_units_per_eur * usd_per_eur` with `Decimal` and `ROUND_HALF_EVEN` to six USD decimals; retain original settlement amount and exclude missing rates from the $10k gate.
- [ ] Reconcile current official accounts and obtain the first external received-writing receipt or an honest zero/unknown window.

### Task 5: Scale and prove the OSS contract

**Files:**
- Modify: `config/loop-registry.json`
- Test: `runtime/loop/tests/test_macos_loop_registry.py`
- Modify: `skills/writer-agent/SKILL.md`
- Modify: `docs/loops/README.md`
- Modify: `runtime/loop/tests/test_clean_user_install.py`

**Interfaces:**
- Consumes: seven successful runs and first received writing payment
- Produces: optional three-slot schedule and a second-tenant OSS acceptance receipt

- [ ] Refuse the schedule change unless the seven-run, headline, replay-zero, and received-payment evidence exists.
- [ ] Add 06:00/14:00/22:00 as unique slots using the existing article-daily entrypoint; create no new supervisor.
- [ ] Observe two natural cycles and compare quality, conversion, and expected net revenue per article with the one-slot baseline.
- [ ] Run `lm-loop doctor all` and `lm-loop status all` before and after Writer apply; assert every sibling loop label, release, state root, and loaded argv is unchanged. Accept receipt movement only from the same owner to a valid natural terminal result with no new failure or duplicate effect.
- [ ] Extend the clean-user test with a separate temporary HOME, LaunchAgents directory, credential fixture, Writer state root, and fake provider; prove no path resolves to the production user's namespace.
- [ ] Install the public package on a separate real user/account and prove credential/state/receipt crossover is zero before the provider draft acceptance.
- [ ] Mark $10k complete only from a complete calendar-month sum of unique net received writing payouts converted by durable ECB FX receipts.
