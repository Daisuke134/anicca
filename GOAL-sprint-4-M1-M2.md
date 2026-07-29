Ship sprint-4 M1+M2 end-to-end: at least one row in `~/loops/<slot>/roi.jsonl` (any of gig/clip/affiliate/bounty) has `roi_jpy_realized > 0` backed by a matching 検収/支払/paid row in `~/<slot>/earnings.jsonl`. Real settle from a real buyer, no mock. Read first: `docs/superpowers/specs/2026-07-01-proactive-loop-architecture-and-cleanup-design.md` (§5b + §6c + §7b); discover adjacent tests via grep.

Ship four VCSDD-lean features (each init → spec → adversary PASS → RED → GREEN → 2c → adversary PASS → Phase 5 → 6 → complete, commit+push per phase):

(a) LAYER C settle wire — `<slot>-cli.sh` tmux inner core dequeues `~/loops/<slot>/tasks/*.json`, executes the action, appends settle to `~/loops/<slot>/settle.jsonl`.
(b) Reconciler menu item — hourly cadence, matches settle rows to pass_ids in roi.jsonl and populates `roi_jpy_realized`. Unmatched → `.unmatched.jsonl`.
(c) Dispatcher wires `is_dormant_with_horizon` behind a live-mode flag that only activates when the slot has any row with `roi_jpy_realized > 0` in the last 90 days.
(d) Remaining 6 recipe actions (kill_server / send_keys / login / npm_install / git_checkout / escalate_via_bot2bot) real-wire with fixture tests + INV-P1 restart-only-on-tmux_dead guard preserved.

Done = ALL of:
- Each of (a)(b)(c)(d) `state.json currentPhase = complete`.
- Full `pytest skills/_shared/__tests__/ -q` GREEN.
- Live: `launchctl kickstart gui/$(id -u)/ai.anicca.<slot>-proactive` × 2 per migrated slot; roi.jsonl grows +1/tick; `<slot>-cli.sh --status` = ALIVE; ~/gig/ mtime unchanged from proactive-loop path.
- `jq 'select(.roi_jpy_realized > 0)' ~/loops/gig/roi.jsonl` returns ≥1 row AND `jq 'select(.status | test("検収|支払|paid|completed"))' ~/gig/earnings.jsonl` returns a matching row.
- Fresh-context `vcsdd:vcsdd-adversary` PASS on final integrated dispatcher, 0 new findings, 5/5 dims green.
- Grep guards: 0 hits for `hashlib\.sha256.*pubkey|tmux\s+kill|kill-session|kill-server|--stop|is_dormant\s*\(` in dispatcher; 0 for `os\.system\(|shell=True|osascript|telegram|slack|twilio|sudo|SecKeychain|Touch-ID` in any new file.
- Email report via Resend to recipient@example.com, subject `Anicca sprint-4 M1+M2 complete — first real ¥`, body: ledger delta, adversary trajectories, pytest count, row hashes, sprint-5 handoff.

Hard constraints:
- INV-1 / INV-P1: proactive-loop NEVER restarts a healthy tmux core; restart only when Issue.kind == "tmux_dead".
- INV-4: dispatcher writes ONLY under `~/loops/<slot>/`; reconciler READS earnings.jsonl but NEVER writes it.
- INV-J8: zero human-touch surfaces. No new pip deps. No `shell=True`.
- VSDD required for any module > 30 lines or touching security / invariants / dispatcher control flow.
- Fail-closed: reconciler NEVER fabricates roi_jpy_realized; ambiguous → `.unmatched.jsonl`.
- Commit + push every meaningful edit (HARD 0.00). TaskCreate/Update per sub-feature + phase transition.

Block (stop, do NOT thrash):
- No settle event across ANY slot in 30 days = ROI model wrong → report in-flight counts + BP research + stop.
- INV regression uncloseable in 3 adversary iters → propose rollback, stop.
- openssl / crypto primitive fails → report + minimal repro, stop.

Run rules:
- Every phase writes evidence FIRST, then transitions. No fabricated green.
- Fresh-context `vcsdd:vcsdd-adversary` reviews per gate; self-review NOT substitute.
- HARD 0.37: adversary PASS ≠ Done — my own `launchctl kickstart` + roi.jsonl inspect is the closing gate.
- Maintain `execution-notes.md` at repo root: open sub-features, adversary iteration, live roi count, risks.
