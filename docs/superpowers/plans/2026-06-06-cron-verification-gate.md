# Cron Verification Gate Implementation Plan

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every cron-driven posting skill runs through fail-closed `ppg_check` before POST and `pvg_verify` after POST. The TikTok-EN-got-JA incident (the design driver) is structurally impossible after migration. Skill code, not LLM discipline, enforces.

**Architecture:** 2 shared lib files (`pre-post-gate.sh`, `post-verify-gate.sh`) + per-platform verifier (`verify-tiktok.sh`, `verify-x.sh`). Posting skills `source` them and call `ppg_check` / `pvg_verify` with skill-specific metadata.

**Tech Stack:** bash, jq, ffprobe, lingua-py (via uvx) or python3 langdetect, curl (Postiz API + camofox), bats-core.

**Pre-flight 2026-06-06**:
- `~/.openclaw/skills/_shared/lib/` exists; `verbatim-guard.sh` precedent (vg_check sourced by other skills) is the model to follow.
- 4.7-slideshow-factory + -ja are TikTok skills (POST via Postiz REST API to `cmnit95mg015rrm0ye5vm8dhl` integration).
- 16+ posting skills total. Canary = `4.7-slideshow-factory` (incident origin). Mass migration to others = follow-up batch.

**Scope of THIS plan**:
- Build the 4 lib files + bats
- Wire into 4.7-slideshow-factory (TikTok canary)
- Wire into anicca-x-useful (X canary — second platform proof)
- Document rollout pattern; mass migration to other 14 skills = follow-up (Plan ②.1)

---

## File Structure

| File | Role |
|---|---|
| `~/.openclaw/skills/_shared/lib/pre-post-gate.sh` | NEW — `ppg_check` function + standalone CLI |
| `~/.openclaw/skills/_shared/lib/post-verify-gate.sh` | NEW — `pvg_verify` function, dispatches per-platform |
| `~/.openclaw/skills/_shared/lib/verify-tiktok.sh` | NEW — TikTok live feed check (Postiz state + camofox snapshot fallback) |
| `~/.openclaw/skills/_shared/lib/verify-x.sh` | NEW — X API live tweet check |
| `~/.openclaw/skills/_shared/lib/lang-detect.sh` | NEW — wraps python3 langdetect (or fallback heuristic) |
| `~/anicca-project/tests/gate/test_pre_post_gate.bats` | NEW |
| `~/anicca-project/tests/gate/test_post_verify_gate.bats` | NEW |
| `~/anicca-project/tests/gate/helpers.bash` | NEW |
| `~/.openclaw/skills/4.7-slideshow-factory/scripts/06-postiz-publish.sh` | MODIFY — `source` + `ppg_check` + `pvg_verify` around the POST call |
| `~/.openclaw/skills/anicca-x-useful/scripts/post-x-direct.sh` | MODIFY — same wiring |
| `~/.openclaw/docs/VERIFY_GATE_ROLLOUT.md` | NEW — canary → mass-rollout checklist for remaining skills |

---

## Tasks

### Task 1: Write lang-detect.sh helper

- [ ] Create `lang-detect.sh` exposing `ld_detect <file-or-string>` → echoes 2-letter code (en/ja/...).
- [ ] Strategy: try `python3 -c "from langdetect import detect; ..."` first; fallback to heuristic (ascii-heavy = en, kanji/kana-present = ja).

### Task 2: Write pre-post-gate.sh

- [ ] `ppg_check` function with flags `--platform`, `--account`, `--integration-id`, `--language`, `--caption-file`, `--asset-manifest`.
- [ ] 5 checks: integration ID env match, lang detect match, asset existence, caption sanitize (no path leak + length cap + vg_check tail), account string lock.
- [ ] Exit codes: 0 ok; 1 integration; 2 lang; 3 asset; 4 sanitize; 5 account.
- [ ] On failure, prints `ppg_check: <code> <reason>` to stderr, returns exit code.

### Task 3: Write verify-tiktok.sh

- [ ] `vt_check_post_id <post_id> <expected_caption_head> <expected_lang>` → 0 ok, non-zero on mismatch.
- [ ] Postiz API GET /public/v1/posts/<id> first; check response state + caption start.
- [ ] If Postiz returns published, also fetch tiktok.com/@<account> via camofox snapshot (existing) and grep caption head — ground truth.
- [ ] If camofox unavailable, log warn, return ok-with-warn (don't false-fail).

### Task 4: Write verify-x.sh

- [ ] `vx_check_post_id <post_id> <expected_caption_head> <expected_lang>` → uses X API tweets endpoint, checks `text` field starts with caption head + `lang` field matches.

### Task 5: Write post-verify-gate.sh

- [ ] `pvg_verify` function with flags `--platform`, `--post-id`, `--expected-caption-head`, `--expected-language`, `--timeout`, `--max-retries`.
- [ ] Dispatch on platform → call verify-tiktok.sh or verify-x.sh.
- [ ] Retry loop with 30s/60s backoff.
- [ ] Exit codes: 0 ok; 6 caption mismatch; 7 lang mismatch; 8 account mismatch; 9 asset integrity; 10 timeout.
- [ ] On failure, posts Slack #content-metrics URGENT alert + returns exit code.

### Task 6: bats tests for ppg_check (RED→GREEN)

- [ ] Test cases: lang mismatch, missing asset, integration env wrong, caption with leaked path.

### Task 7: bats tests for pvg_verify (RED→GREEN)

- [ ] Test cases: caption head mismatch (mock verifier), lang mismatch, timeout exhaustion.

### Task 8: Wire 4.7-slideshow-factory/scripts/06-postiz-publish.sh

- [ ] Add `source` lines at top.
- [ ] Add `ppg_check` call before POST step.
- [ ] Add `pvg_verify` call after POST step, capturing POSTIZ_POST_ID from receipt.
- [ ] Failure path: skip Slack `✅` report, emit Slack URGENT instead, exit non-zero.

### Task 9: Wire anicca-x-useful/scripts/post-x-direct.sh (parallel platform proof)

- [ ] Same pattern as Task 8, X platform.

### Task 10: Manual canary fire — happy path

- [ ] `openclaw cron run` for 4.7-slideshow-factory-en daily; observe gate fires, post succeeds, verify succeeds, ✅ Slack received.

### Task 11: Manual canary fire — failure path (inject JA caption into EN skill)

- [ ] Patch caption.txt mid-run with JA text; expect ppg_check exit 2 → no POST → URGENT Slack.

### Task 12: Write VERIFY_GATE_ROLLOUT.md

- [ ] Document per-skill wiring template; canary-then-fan pattern; staleness audit.

### Task 13: Commit + push everything

- [ ] Mirror live files into `anicca-openclaw-mirror/`.
- [ ] git add + commit + push.
