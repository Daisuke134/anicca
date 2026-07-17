# WS6h — Verify the DEPLOYED cloud actually runs the agentic + worldwide Life Manager loops

Date: 2026-06-19
Branch / worktree: `feature/lm-cloud-deploy-verify` → `../anicca-lm-cloud`
Files this touches: `apps/life-call/server.js`, `.railwayignore`, this spec.

## Problem

The agentic ask/reply rewrite + worldwide (no-hardcoded-Tokyo) fixes are merged to `main`
(`22026366`, `4006f9df`, `ba16e069`) and verified by a no-mock LOCAL E2E (`scripts/e2e-ask.js`,
3/3 green against the real Google Calendar). But the Railway-deployed service's `[ask]` log still
prints the OLD format (`asked=N resolved=N`, no `autofilled=`), so we cannot yet prove the DEPLOYED
service runs the new code. `railway up` is unusable here (uploads the whole 395 MB monorepo → 413).

## Goal

Prove — with fresh evidence from the running Railway service — that the deployed life-call runs the
agentic + worldwide code, by:

1. Emitting an unambiguous build marker on startup so the live commit is identifiable in logs.
2. Letting the GitHub→Railway integration deploy `main` (the service's deploy branch) via a normal
   PR merge — NO `--no-verify`, NO direct main commits, lefthook green.
3. Reading the live logs back: startup shows the marker AND the next `[ask]` tick prints the new
   `autofilled=` field.

## Design

| Item | Change | Why |
|---|---|---|
| Build marker | `server.js` listen log → `build=agentic-ask-worldwide-v2` | Distinguishes new vs old image in `railway logs`, deterministically. |
| `.railwayignore` | add `.git/ .codegraph/ .agents/ .serena/ **/*.sock` | So any future `railway up` can tar the context (sockets/`.git` are un-archivable). Improvement, not the deploy mechanism. |

## Verification (no-mock, fresh evidence)

1. Merge the PR to `main` → Railway auto-deploys.
2. `railway logs` shows `listening … build=agentic-ask-worldwide-v2`.
3. Within 20 min the `[ask]` tick logs `autofilled=… asked=… resolved=…` (the new field) — proving
   the agentic ask loop is the live code.
4. Travel + scheduler loops already log `started` lines; confirm they remain.

## Out of scope (separate, with their own constraints)

- A literal brand-new paid Google user (new-account creation is prohibited; uid is per-Google-user).
- A duplicate real $20 Stripe charge (Dais's row is already `paid=true`; webhook already verified).
  These two are the only parts of "fresh paid user E2E" that cannot run autonomously without a new
  account or real money; everything else (onboarding seam, wake, ask, travel) is verified.
