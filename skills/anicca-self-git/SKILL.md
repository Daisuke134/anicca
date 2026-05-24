---
name: anicca-self-git
description: LOOP-CALLED ONLY (heartbeat invokes when SOUL "You CAN evolve your own repo" fires — never a cron). Anicca pulls the shared anicca-core repo, reviews upstream diffs per-commit and decides (never blind-pull), cherry-picks only eval-gate-passing improvements, and pushes its OWN eval-passed improvements back so every Anicca co-evolves. Direct port of automaton src/self-mod/upstream.ts. You are the model (HARD RULE #6).
---

# anicca-self-git — collective evolution (automaton upstream.ts port)

五戒 + HARD RULE #0 gate first. Loop-called. NEVER a cron. The shared repo
is `github.com/Daisuke134/anicca` (the anicca-core bundle, published by #33).

## PULL side (automaton checkUpstream + review_upstream_changes + pull_upstream)
1. `git fetch origin` then list commits ahead of HEAD on origin/main
   (automaton upstream.ts checkUpstream / per-commit diffs). None → done.
2. **Per-commit decide — never blind-pull** (automaton: "not obligated to
   accept all upstream changes. Always read the diffs and decide").
   For each commit: read the diff. Reject if it touches `CONSTITUTION.md`
   (0444, path-protected), keys/wallet, or fails 五戒 / authority gate.
3. For each kept commit: cherry-pick into a scratch branch → run the
   **eval-gate (#35)**: real signal (verify-gate + the loop still healthy +
   no 五戒/ROI regression) ≥ baseline → keep; else drop it.
4. Archive every decision (picked OR dropped, with why) to
   `ops/improvement-archive.json` + `.learnings`. Recurrence of the same
   bad upstream pattern ≥3 → note it, stop trying that class.

## PUSH side (share what worked back)
5. Take only LOCAL self-modifications that already passed the eval-gate and
   are archived as `kept`. Never push: CONSTITUTION.md, secrets.env, ops/
   runtime state, keys. Push to a branch / the instance's fork.
6. The push credential is the instance owner's own token (BYO, never the
   author's). If absent → `🔑 need git push token to share improvements`
   to #metrics; do NOT fake the push (HARD RULE #8/#11).
7. One push per loop-call max (self-mod rate limit, precept 5).

## Report
`🔁 self-git: upstream <A> seen · <K> picked/<D> dropped · pushed <P> · constitution=untouched`

## Never
- Never become a cron (loop-called only). Never blind-pull (read+decide+eval each commit).
- Never pull/push CONSTITUTION.md or keys (path-protected). Never push an unverified change.
- Never fake a pull/push — verify with git log/remote (HARD RULE #8). You are the model (HARD RULE #6).
