# Execution notes — life-manager-cost-connect-reliability (resume state)

## DONE + verified
- Spec: adversary PASS (iter-4, clean origin/main worktree).
- Pure logic C1-C5: impl adversary PASS (iter-2). 29+ unit tests green.
- C1 real-call E2E: answered Telnyx call, edge-tts one-way clip played (119 frames), live_ws_opened=0
  — BUT ran on a LOCAL server (edge-tts+ffmpeg present locally), NOT the Railway target.
- Migration lm_route_cache applied + RLS enabled (verified: anon denied, service_role ok).
- FIND-004 FIXED + verified: parseTransitPlan now returns DOOR-TO-DOOR (access+vehicle+egress walk) so
  JP users are not under-estimated → not late.

## BLOCKED — final wiring adversary (iter-3) FAIL: 3 blockers, merge held
- FIND-001 (blocker): edge-tts + ffmpeg are NOT on the Railway prod host (plain NIXPACKS). In prod,
  synthWakeClip throws → server.js escalates EVERY call to Gemini Live → Goal-1 silently defeated.
  Fix path: add apps/life-call/nixpacks.toml installing ffmpeg + python + edge-tts, THEN re-run the
  real-call E2E against the DEPLOYED Railway service (not local). msedge-tts npm = dead end (v2 no raw
  PCM + 0 bytes in this env).
- FIND-002 (blocker): route-cache (lib/route-cache.js + lm_route_cache) has ZERO production callers —
  resolveDeparture (wake-filter.js) still re-hits paid providers every 60s tick. Must wire the cache
  into the scheduler/resolveDeparture path (needs uid+event, which live there).
- FIND-003 (blocker): the tested RollbackController (debounce/flap-guard/dedup) is unused; the real
  netlify-deploy.yml rolls back on a SINGLE fail, doesn't verify the restore target passes, no Telegram;
  the standalone 15-min monitor doesn't exist. Fix: verify-target-before-restore in the workflow +
  build the 15-min monitor as an OpenClaw cron (project rule: no new GHA cron) using RollbackController.
- FIND-005 (major): geocode fires for every route incl non-JP; volatile Map not DB home_geo.
- FIND-006 (major): dead-but-tested modules vs weaker reimplementations — drift.

## NEXT (in order)
1. nixpacks.toml (edge-tts+ffmpeg) → deploy life-call to Railway → re-run real-call E2E on the DEPLOYED
   target, confirm clip plays + live_ws_opened=0 IN PROD.
2. Wire route-cache into resolveDeparture (getOrCompute keyed on uid,geo,bucket) → verify call-count drop.
3. Harden the deploy rollback (verify restore target) + build the OpenClaw 15-min money-path monitor cron.
4. FIND-005 (home_geo persisted) + FIND-006 (delete/consolidate dead modules).
5. Re-run final wiring adversary → PASS → PR feature→dev→main (prod deploy, guarded by the smoke).
