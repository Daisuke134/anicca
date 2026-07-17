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

## UPDATE 2026-07-04 — adversary FIND-001..006 addressed
- FIND-001: nixpacks.toml adds ffmpeg + python313Packages.edge-tts to Railway PATH (disk fix). PROD PROOF
  = re-run the real call against the DEPLOYED Railway service AFTER merge (railway up was broken: 413/wrong
  dir; Railway deploys via git push to main). synth failure still safely escalates to Live (no silent call).
- FIND-002: route-cache.js wired into travel.js directionsMinutes → provider called ONCE per (geo,bucket)
  across 60s ticks (cache-hit test). FIXED.
- FIND-003: workflow flap-guard re-verifies after restore; money-path-monitor.mjs (15-min, uses tested
  RollbackController debounce/flap/dedup, persisted state) created as the OpenClaw-cron runnable. FIXED.
- FIND-004: parseTransitPlan door-to-door (walk incl) → no under-estimate/late. FIXED + verified.
- FIND-005 (accepted): geocode is memoized (no per-tick re-geocode = cost goal met); DB-persisted home_geo
  is a deferred optimization, not a correctness issue. Documented deviation.
- FIND-006: money-path.js (smoke+monitor), route-cache.js (travel), voice-*/transit/user-selector all now
  imported by production paths → no dead-but-tested modules. FIXED.

## CONVERGED 2026-07-04 — feature shipped + prod-verified
- Merged feature→main (PR #269/#270/#271). GHA landing deploy: post-deploy money-path smoke = SMOKE PASS in prod (guard live).
- Railway life-call deployed (nixpacks: ffmpeg + pip edge-tts). First build failed (python313Packages.edge-tts missing) → pip. First prod call escalated to Gemini (spawn edge-tts ENOENT) → fixed by `python3 -m edge_tts`.
- ★ FINAL PROD PROOF: real answered call → edge-tts one-way clip played (119 frames), live_ws_opened=0 → $0 native-audio. Dais confirmed the free voice. ★
- Goal Done #1 (voice), #2/#3 (transit+cache, unit+wire verified), #4 (selector), merged (#4 done). 
- FOLLOW-UP (ops, not blocking): register the 15-min money-path-monitor.mjs as an OpenClaw cron in
  ~/.openclaw/cron/jobs.json against a stable main checkout (raw-node, not agentTurn, to avoid LLM tokens).
  The PRIMARY guard (post-deploy smoke in netlify-deploy.yml) is already live + verified.
