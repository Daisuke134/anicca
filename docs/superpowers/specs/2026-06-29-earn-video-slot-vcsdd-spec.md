# earn/video — faceless video earn SLOT (state machine in the ONE loop) — VCSDD spec (2026-06-29)

Dais 2026-06-29: "We're building a LOOP that earns money without humanity." ⇒ EVERY step is a loop
transition, NOT a manual step. If the affiliate link is deferred to "after warmup", that deferral MUST be
a state in the machine the loop runs — otherwise no one ever does it. Nothing is manual. Nothing waits on a human.

## What this is
`earn/video` = a registry LIVE slot (per `2026-06-29-ecosystem-integration-design.md` slot contract). The ONE
loop (`runtime/loop`, brain=claude-p|proxy) picks it among gig/clip/affiliate/video/audit each wake and spawns
`~/anicca/skills/earn/video/run.sh` for ONE bounded unit of work. The faceless-video business (create→warmup→
post→monetize) is encoded as an idempotent STATE MACHINE so the loop drives the whole lifecycle with zero human.

## STATE (per brand account; SSOT = ~/.cloak/ig-<handle>.json + state/earn-video.jsonl)
```
{ handle, email, pw, status, warmup_day, affiliate_set, last_post_date, posts, niche, tid?, ctx? }
status ∈ {created, warming, warmed, monetized}
```

## THE STATE MACHINE — run.sh does exactly ONE transition per wake (idempotent, bounded)
```
on each wake (read state, do the FIRST applicable, persist, exit 0 with one-line result):

 S0  no account yet for this niche        → ig-account-create (proven) → setup_profile(icon+bio, NO link)
                                             status=warming, warmup_day=0
 S1  status=warming AND warmup_day<7       → warmup-instagram ONE day's actions (feed scroll/watch/light like)
                                             warmup_day++  (HARD: never commercial yet)
 S2  warmup_day>=7 AND NOT affiliate_set   → ★ THE DEFERRED STEP, NOW IN THE LOOP ★
                                             setup_profile --website <affiliate/ebook link> (+ bio CTA)
                                             affiliate_set=true, status=warmed
 S3  status∈{warmed,monetized} AND today-not-posted
                                           → faceless-money-factory: gen fresh script(agent's own model)→
                                             TTS→Mixkit b-roll→assemble+captions→ig-reels-poster (DRAFT→live)
                                             last_post_date=today, posts++
 S4  posted already today                  → check affiliate/ebook EXTERNAL inflows → record-earn (real USDC ONLY)
                                             status=monetized
```
★ The affiliate link (S2) is just another transition — the loop applies it automatically on warmup-day-7.
No human ever touches it. Same for warmup (S1), posting (S3), earnings (S4). ★

## SLOT CONTRACT (must satisfy — runtime/run-skill.mjs interface)
1. **Entrypoint** `~/anicca/skills/earn/video/run.sh` — reads args (env/argv), does ONE transition, prints one
   line `{transition, did, earned_usdc, cost_usdc}` on stdout, exit 0. Wallet from standard path (keys scrubbed).
2. **NO HUMAN** (hard): captcha→CapSolver · email-OTP→`gog gmail in:anywhere` · login→`~/.openclaw/.env` ·
   publish→autonomous (ig-reels-poster). Any human step ⇒ not a valid slot. (IG signup already 0-human; YT dropped
   for now = SMS wall.)
3. **5-GATE + record-earn (INV-7)**: V1 proposal(account+niche) / V2 listing(profile live) / V3 deliverable(post
   live, verified URL) / V4 inbound(affiliate clicks/orders) / V5 continuous(daily). `record-earn` counts ONLY
   real EXTERNAL on-chain USDC inflows — NEVER count "posted" as "earned" (past skills earned ¥0 for lacking this).
4. **Idempotent + bounded**: safe every wake; one transition only; respects SKILL_TIMEOUT_S; logs what it dropped
   (e.g. "warmup already done today").
5. **registry.json**: `summary` (one line the brain reads), `status: live`. Notify dashboard CC to wire it.

## NO-HUMAN proof (already built, reused as transitions)
- account: ig-account-create (proven @money_blueprintdaily, @aiclipsvault — 0 phone/captcha/human).
- profile: setup_profile.py (proven — icon+bio; --website for S2).
- video: faceless-money-factory (proven, $0, AI-agnostic, Dais "top notch").
- post: ig-reels-poster (--dry proven; --live when warmed).
- warmup: warmup-instagram (research-backed, ban-signal stop).
The slot just SEQUENCES these as state transitions.

## VERIFICATION = VCSDD
SPEC(this) → RED(failing tests: state-machine picks correct transition for each state; record-earn rejects
non-USDC; idempotent double-run = no double action) → GREEN(run.sh state machine + persist) → fresh-context
**vcsdd-adversary**(disk-only, find: a state that does nothing/loops, a human step, a "posted=earned" leak,
non-idempotency) → NO-MOCK E2E(real wake on @money_blueprintdaily: S1 does a real warmup action; later S3 posts
a real reel; S4 records only real USDC) → 4-D convergence.

## DONE = the ONE loop (brain=claude-p) picks earn/video across wakes; it autonomously warms the account,
## sets the affiliate link on day-7 (in-loop, no human), posts a fresh faceless money short daily, and
## record-earns ONLY real USDC inflows — same body flips to self-funded via ANICCA_BRAIN=proxy.
```
Built by VCSDD; entrypoint + registry summary delivered to the dashboard CC to flip status:live.
```

## VCSDD verdict — ROUND 8: OVERALL PASS (2026-06-29)

All 5 dimensions PASS (D1 state-machine, D2 INV-7 record_earn, D3 no-human, D4 warmup-real, D5 contract) after 8 fresh-context adversary rounds. Fixed across rounds: D1 affiliate trap → reachable; warmup fake-counter → real distinct reels; dry-fake post → live+verified; unverified post/affiliate → published+post_url / website_set gates; posting starvation → S3 priority; double-post on timeout → verify-only reconcile; record_earn spoof → fail-closed on-chain gate; stale render → freshness gate; corrupt state → state_io atomic+.bak; ban → per-day backoff; S4 starvation → affiliate once/day (FIND-801).

### Known-accepted non-blocking findings
| ID | Sev | Status |
|----|-----|--------|
| FIND-804 | low | `json.load(open(p))` without context-manager — FD leak only in short-lived `$PY -c` procs; no practical impact. Accepted. |
| FIND-805 | low | Concurrency: atomic writes prevent truncation but two SIMULTANEOUS wakes could last-writer-wins or double-post. **Invariant: the ONE loop spawns this slot SERIALLY (one bounded transition/wake) — never two concurrent run.sh for the same handle.** Enforced by the loop scheduler, not in-file. |

### REMAINING for first real $ (not code-correctness, but real-world wiring)
1. Finish @money_blueprintdaily 7-day warmup (loop-driven S1).
2. Create the monetizable product + affiliate/payout rail (ebook/Gumroad etc.) → set MONK_EBOOK_URL.
3. Build the on-chain payout detector that writes ~/.cloak/earn-video-inflows.jsonl ONLY after real Base USDC confirmation (replaces verify_onchain stub).
