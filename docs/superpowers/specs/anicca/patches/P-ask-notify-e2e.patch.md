# P-ask-notify-e2e — battle-test ask / notify / telemetry end to end with real evidence (no mock)

> Spec: `28-product-redesign-merge-2026-06-16.md` §2. Task #4. Targets: `~/anicca/skills/life/{ask,notify}` (OSS, applied)
> + `apps/landing/netlify/functions/{life-ask,life-notify,telemetry,dashboard-sync}.js` (products) + live crons.
> **Goal:** prove the three "applied-but-unverified" WF-B/telemetry pieces actually work with fresh real evidence —
> leave-no-task-behind (spec 28 Definition of Done). This is a VERIFY patch: it adds the missing E2E tests + a
> verification doc; it only ADDS small fixes if a round-trip fails.

---

## §1 Reality found (cited)

| piece | applied code | what's unverified |
|---|---|---|
| **ask** | `~/anicca/skills/life/ask/ask.js:1-30` (GCal scan → `gog gmail send` question; trigger `~/.openclaw/cron/jobs.json "anicca-life-ask"` daily 06:00 JST) + web fn `apps/landing/netlify/functions/life-ask.js` (`_lib/ask-logic.js`) | a real question mail goes out, a real reply is parsed, and the location is written back to GCal — never E2E-proven |
| **notify** | `~/anicca/skills/life/notify/notify.js` (late-risk from started `[Travel]` blocks → approval gate → notify) + web fn `life-notify.js` (`_lib/notify-logic.js`) | a real late-risk → approval → stakeholder notify round-trip — unproven |
| **telemetry** | `apps/landing/netlify/functions/{telemetry,dashboard-sync}.js` (verified vs ONE instance) | `/dashboard` showing **>1** instance (multi-instance aggregate) — unproven; STATUS.md says dashboard renders one/genesis only |

## §2 The E2E runs (real side effects, HARD 0.24/0.31)

### ask
```bash
# 1. seed a GCal event with an UNKNOWN location (a place name that needs asking)
# 2. fire the ask path against keiodaisuke@gmail.com (Dais's own inbox — not a third party)
node ~/anicca/skills/life/ask/ask.js --action question   # canonical entry (documented in ask.js) → gog gmail send
# 3. reply to the question mail with the location
# 4. fire the reply-ingest → assert the GCal event now has the location + a [Travel] block follows
```
Evidence: the sent mail id, the reply, the GCal event before/after (location filled).

### notify
```bash
# 1. create a started [Travel] block that implies lateness (start in the past, not yet at destination)
# 2. fire notify scan → it produces an approval mail (target + draft) to keiodaisuke@gmail.com
# 3. approve → assert the stakeholder-notify mail is sent
```
Evidence: approval mail id + the post-approval notify mail id (both to Dais's own inbox; no real third party).

### telemetry (multi-instance)
```bash
# sign + POST a SECOND instance's telemetry (a second wallet) so instances has >1 row, then:
curl -s https://aniccaai.com/.netlify/functions/dashboard-sync | jq '.instances | length'   # expect >= 2
```
Evidence: `/dashboard` (or dashboard-sync JSON) lists ≥2 instances with real net_worth.

## §3 Acceptance
1. ask: a real question mail sent + a real reply parsed + GCal location written back (before/after captured).
2. notify: approval mail → approval → stakeholder notify mail, all real, to Dais's own inbox only.
3. telemetry: dashboard-sync returns ≥2 instances from real signed POSTs.
4. A verification doc `docs/verifications/2026-06-16-ask-notify-telemetry-e2e.md` records every id/tx/before-after.
5. Any failure → a minimal fix patch is added here and the run repeats until green (no "coming", no mock).

## §4 Boundaries
Verification-first: no new feature code unless a round-trip fails. Mail targets = `keiodaisuke@gmail.com` (Dais's own),
never an external third party (test-safety). `~/anicca/skills/life/*` + products `life-*`/telemetry functions only.
