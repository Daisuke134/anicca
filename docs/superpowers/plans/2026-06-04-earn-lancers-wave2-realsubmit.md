# Earn Lancers Wave 2 — real-submit + CFO row ④ verify

> Follow-on to `2026-06-04-earn-lancers.md` (Wave 1 scaffolding). This plan executes ONE real Lancers proposal under the documented safety cap (`--max-apply 1 --max-budget-jpy 1000`), watches CFO/bank for the deposit, and is the ONLY plan permitted to close `#325`. Fully autonomous per HARD RULE #-2 — agent drives camofox + Google login env; the only allowed hard-block is a real CAPTCHA element or financial-broadcast prompt. No human eyeballing.

**Prereq:** Wave 1 (`2026-06-04-earn-lancers.md`) all Tasks 0–12 green. Skill registered. Dry-run E2E green. `~/.hermes/state/earn-lancers-dry-run-latest.json` exists.

**Done condition (the ONLY way `#325` closes):**
1. `~/.hermes/state/earn-lancers-runs.jsonl` has ≥1 row with `status:"applied"` AND `finish_url` containing `propose_finish`.
2. Camofox re-fetches the `finish_url` and the snapshot contains the proposal body text — agent verifies this autonomously, no human eyeball.
3. `cfo-bank` (already LIVE) records an incoming Lancers deposit on Dais's bank within 30 days of the `applied` row (Lancers payout SLA). Verified by running `bash ~/.openclaw/skills/cfo-bank/scripts/scan.sh` and grepping the output for `Lancers` / `ランサーズ`.
4. ONLY when (1)+(2)+(3) all true: TaskUpdate closes `#325` with the row from `~/.hermes/state/earn-lancers-runs.jsonl` and the CFO deposit line as the receipt.

## Task A: Preflight (X5)

- [ ] A.1 `curl -sS http://localhost:9377/health | jq -e '.ok and .browserConnected'` → exit 0.
- [ ] A.2 `command -v hermes && hermes --version` → ≥ 0.12.0 (X1 — do NOT update).
- [ ] A.3 Env presence: `GOOGLE_LOGIN_EMAIL`, `GOOGLE_LOGIN_PASSWORD`, `LANCERS_PASSWORD` all `FOUND` per Wave 1 Task 0 Step 3.
- [ ] A.4 `bash ~/.hermes/scripts/anicca-earn-lancers.sh --dry-run` → exit 0, `~/.hermes/state/earn-lancers-dry-run-latest.json` updated.
- [ ] A.5 `bash skills/anicca-earn-lancers/scripts/login-check.sh` → exit 0 (autonomous, no human). If exit 6/9 → diagnose `~/.hermes/state/earn-lancers-login-hardblock.json`, patch, retry. Do NOT proceed until exit 0.

## Task B: Execute ONE real proposal (autonomous, capped)

- [ ] B.1 Run, exactly once:
```bash
bash /Users/operator/.hermes/scripts/anicca-earn-lancers.sh \
  --confirm \
  --max-apply 1 \
  --max-budget-jpy 1000 \
  2>&1 | tee -a ~/.hermes/state/earn-lancers-cron-fire.log
```
Expected: stdout JSON envelope `.candidates[0].status == "applied"` and `.candidates[0].finish_url` matches `propose_finish`. If `.status` is anything else (`skip:REDIRECT` / `skip:BLOCKED` / `final_click_failed`), the candidate pool that day did not meet the ¥1k floor; re-run the next day's beat — do NOT raise the cap.

- [ ] B.2 Read back the last row autonomously:
```bash
ROW=$(tail -1 ~/.hermes/state/earn-lancers-runs.jsonl)
echo "$ROW" | /usr/bin/jq -e '.status == "applied" and (.finish_url | test("propose_finish"))' >/dev/null \
  && echo SUBMIT_OK || { echo SUBMIT_NOT_YET; exit 0; }
```
Expected: `SUBMIT_OK`. If `SUBMIT_NOT_YET`: NOT a failure — the autonomous loop is allowed to keep trying daily until B.1 produces `applied`. Do NOT close `#325`.

- [ ] B.3 Autonomous verification of the proposal page (no human):
```bash
FURL=$(echo "$ROW" | /usr/bin/jq -r '.finish_url')
TAB=$(curl -sS -X POST http://localhost:9377/tabs -H 'Content-Type: application/json' \
  -d "$(/usr/bin/jq -n --arg u "$FURL" --arg uid anicca --arg sk default \
        '{url:$u, userId:$uid, sessionKey:$sk}')" | /usr/bin/jq -r .tabId)
sleep 5
SNAP=$(curl -sS "http://localhost:9377/tabs/$TAB/snapshot?userId=anicca&sessionKey=default")
curl -sS -X DELETE "http://localhost:9377/tabs/$TAB?userId=anicca&sessionKey=default" >/dev/null
printf '%s' "$SNAP" | /usr/bin/jq -e '.snapshot | test("提案|Proposal|finish")' >/dev/null \
  && echo PROPOSAL_VISIBLE || { echo PROPOSAL_NOT_RENDERED; exit 0; }
```
Expected: `PROPOSAL_VISIBLE`. If `PROPOSAL_NOT_RENDERED`: write `~/.hermes/state/earn-lancers-wave2-hardblock-<ts>.json` with the snapshot subset and do NOT close `#325`; loop retries on the next beat.

## Task C: CFO bank deposit verify (the row ④ gate)

- [ ] C.1 Up to 30 days after Task B SUBMIT_OK, run on each weekday:
```bash
bash ~/.openclaw/skills/cfo-bank/scripts/scan.sh
grep -Ei 'Lancers|ランサーズ' ~/.openclaw/skills/cfo-bank/data/bank-latest.jsonl \
  && echo CFO_DEPOSIT_VISIBLE || echo CFO_DEPOSIT_PENDING
```
Expected eventually: `CFO_DEPOSIT_VISIBLE`. While `CFO_DEPOSIT_PENDING`: do NOT close `#325`. The autonomous loop keeps trying daily Wave 1 dry-runs in parallel — no human poke required.

## Task D: Close `#325` (only here, only when C.1 shows CFO_DEPOSIT_VISIBLE)

- [ ] D.1 TaskUpdate sets `#325` to `completed` with a comment containing: `(a)` the submitted `finish_url` from Task B.2; `(b)` the verified-rendered confirmation from Task B.3; `(c)` the CFO bank line from Task C.1 (amount + date).
- [ ] D.2 Update `specs/00-MASTER.md` row ④ sub-bullet ④a from "scaffold (Wave 1)" to "Wave 2 LIVE — one real proposal applied + CFO deposit verified <YYYY-MM-DD>"; commit + push.

That is the only flow allowed to advance row ④ on the Lancers channel.
