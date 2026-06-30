---
id: proactive-loop-architecture-and-cleanup
status: active
sprint: 2-to-3-bridge
owners: [anicca]
created: 2026-07-01
related:
  - 2026-06-07-automaton-sutando-fork-design.md
  - 2026-06-29-earn-gig-slot-design.md
  - .vcsdd/features/proactive-loop-skeleton/   # VCSDD-converged sprint-2
---

# Proactive-Loop Architecture & Sprint-1 Cleanup

## 1. Why this spec exists

Sprint-2 (`proactive-loop-skeleton`) converged through VCSDD with iter-4 PASS + my own live macOS E2E (commit `0011c39`). Before migrating the 6 earn slots to it (= sprint-3 work), we must:

1. Lock in the architectural relationship between LAYER A/B/C/D (= proactive-loop vs existing `<slot>-cli.sh` tmux cores vs launchd watchdog vs bot2bot).
2. Resolve duplications with sprint-1 helpers under `skills/_shared/` so we don't run two of the same thing.
3. Define the per-slot migration contract (= menu.json schema, plist template, tasks/ folder, build_log.md location).

This spec is the source of truth for that bridge. Sprint-3 implements migrations against it.

## 2. The four-layer architecture (post-sprint-2)

```
LAYER A — launchd plist per slot           (= cadence = 5 min)
  ai.anicca.<slot>-proactive.plist  → bash proactive-loop.sh <slot>

LAYER B — proactive-loop 8-step body       (= OUTER orchestrator, this sprint)
  STEP 0/0.5/1/2/3/4/5/6/7  (= quota → tasks → pending-q → health → log →
                                pick → ACT → append)

LAYER C — <slot>-cli.sh tmux+claude core   (= INNER worker, UNCHANGED)
  the existing ALWAYS-ON tmux session that runs the real browser actions
  (CloakBrowser daily-driver, Coconala/clip/affiliate/bounty workflows).
  LAYER B writes tasks/ items that the INNER worker dequeues.

LAYER D — bot2bot (= AI-to-AI lateral lane, gh-issue based)
  any LAYER B run can bot2bot.post / poll across slots without touching humans.
```

### Why LAYER C is preserved

The `<slot>-cli.sh` pattern (cloned from Sutando) is the only thing that has actually earned ¥. It uses CloakBrowser daily-driver tabs that survive across proactive-loop ticks. We do not collapse LAYER B + LAYER C; we keep the INNER tmux worker and let the OUTER proactive-loop decide WHAT it should do via the tasks/ queue + menu.json picks.

### Cadence map

| layer | cadence | trigger |
|---|---|---|
| launchd `<slot>-core-healthcheck.plist` | every 1 min | restart tmux if dead (belt-suspenders) |
| LAYER A proactive-loop plist | every 5 min | fcntl re-entrancy guard skips overlap |
| LAYER C tmux internal cron | per slot (e.g. every 10 min for Coconala scan) | independent; not gated by LAYER B |

LAYER C runs autonomously. LAYER B steers it; if LAYER B is silent (quota=DORMANT, all blocked), LAYER C still works on whatever it was doing.

## 3. Per-slot migration contract (= what every slot must have)

```
~/loops/<slot>/                             ← created by first proactive-loop tick
├── menu.json                               ← per-slot ROI catalog
├── tasks/                                  ← LAYER B → LAYER C queue
│   ├── *.txt | *.json                      ← dropped here by STEP 6
├── pending-questions.md                    ← READ ONLY, never surfaced
├── build_log.md                            ← append-only narrative
├── state/
│   └── core-status.json                    ← per-step status snapshot
├── .proactive.lock                         ← fcntl LOCK_EX | LOCK_NB
├── .unfixable.jsonl                        ← EDGE-S4 cascade sink
├── .dormant.sentinel                       ← Q5 7d-negative ROI write
├── bot2bot-sent.jsonl                      ← LAYER D outbound trace
└── roi.jsonl                               ← sprint-3 per-pass ROI (deferred)
```

### menu.json schema (= proven via gig E2E 2026-07-01)

```json
{
  "schema_version": 1,
  "categories": [
    {
      "name": "<unique action>",          // e.g. "scan-coconala-new-requests"
      "category": "<dedup family>",       // e.g. "scan-requests" — used for novelty
      "platform": "<service>",            // e.g. "coconala"
      "roi_estimate_jpy": <number>,       // expected payout per land
      "probability_of_landing": <0-1>,    // expected landing rate
      "required_budget": "LIGHT|MEDIUM|FULL",
      "blocker_check": null | "<callable>",
      "min_cadence_seconds": <number>     // 0 = always eligible; 86400 = once/day
    }
  ],
  "novelty_quota_ratio": <0-1>            // pick_next reserves this fraction
                                          // for never-tried (category, platform)
}
```

`min_cadence_seconds > 0` lets sprint-1 `adversary-daily.sh` retire — daily adversary becomes a menu item with `min_cadence_seconds=86400` (per EDGE-S7).

### launchd plist template (= 1 plist/slot, sprint-3 generates these)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
                "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>ai.anicca.<SLOT>-proactive</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>/Users/operator/anicca/skills/_shared/proactive-loop.sh</string>
    <string><SLOT></string>
  </array>
  <key>StartInterval</key><integer>300</integer>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>/Users/operator/.openclaw/logs/<SLOT>-proactive.out</string>
  <key>StandardErrorPath</key><string>/Users/operator/.openclaw/logs/<SLOT>-proactive.err</string>
</dict>
</plist>
```

## 4. Sprint-1 helper cleanup (= what to archive, what to keep)

| File under skills/_shared/ | Verdict | Reason |
|---|---|---|
| `proactive-loop.sh` + `proactive-loop-dispatch.py` | **KEEP** | sprint-2 canonical (LAYER A/B) |
| `lib/{quota_tracker,menu,health_check_v2,bot2bot,proactive_loop,build_log,_common}.py` | **KEEP** | sprint-2 PURE layer |
| `credential-restore.sh` | **KEEP** (scaffold, sprint-3 wires camofox) | STEP 3 recipe target |
| `auto-allowlist.sh` / `auto-rollback.sh` | **KEEP** (scaffolds) | STEP 3 recipe targets |
| `self-recover.sh` + `self-recover-dispatch.py` | **KEEP** | main-loop side, separate path |
| `anicca-bot.pub` / `trusted-authors.json` / `hook-modules-allowlist.txt` / `payout-endpoint-allowlist.json` | **KEEP** | trust anchors |
| `loop-healthcheck.sh` + `loop-healthcheck-dispatch.py` | **ARCHIVE** | replaced by `health_check_v2.dispatch_highest_priority` |
| `loop-roi.sh` + `loop-roi-dispatch.py` | **ARCHIVE** | replaced by STEP 7 build_log + sprint-3 roi.jsonl |
| `loop-propose.sh` | **ARCHIVE** | replaced by `pick_next` from menu.json |
| `loop-scale.sh` | **ARCHIVE** | replaced by budget-aware ACT in STEP 6 |
| `loop-improve.py` | **ARCHIVE** (revive as menu item) | sprint-3 re-introduces as `min_cadence_seconds=N` menu entry |
| `adversary-daily.sh` | **ARCHIVE** | menu item with `min_cadence_seconds=86400` (per EDGE-S7) |
| `cross-learn-read.sh` / `cross-learn-share.sh` / `cross-learn-share-dispatch.py` | **ARCHIVE** | replaced by `bot2bot` gh-issue lane |

Archive target = `skills/_shared/archive/sprint-1/`. Reason: VCSDD convergence proved sprint-2's 4 generic primitives subsume the 9-handler sprint-1 design. Keeping both running creates double-write races on the same `~/loops/<slot>/` state.

## 5. Migration sequence (= sprint-3 task ordering)

1. **(this spec)** Lock architecture; commit + push.
2. **Plist scaffold generator** — `skills/_shared/scripts/install-proactive-plist.sh <slot>` emits a per-slot launchd plist from the template above + `launchctl bootstrap`s it.
3. **gig FIRST** (TASK #27) — write `~/loops/gig/menu.json`, install plist, watch 1 hour of ticks, verify build_log grows and tasks/ items get dequeued by LAYER C.
4. **Bridge step** — modify `skills/earn/gig/run.sh` to be a thin shim: pass-through to LAYER B (= during migration window only).
5. **Remove sprint-1 helpers** from active cron (= unload any launchd plists, delete from cron entry tables), then `git mv` them to `archive/sprint-1/`.
6. **Migrate clip / clip-promote / affiliate / bounty** (TASK #28) one at a time, each with a 1-hour soak before next.
7. **`hl-trade` + `finchip-publish` + `board-poller`** — they lack `run.sh` today; sprint-3 spec each individually (separate specs).
8. **Cleanup PR** — when all 6 slots are on LAYER B, remove `earn-slot.mjs`'s special-casing of `run.sh` if it duplicates LAYER A scheduling.

## 6. Anti-collision invariants (= acceptance tests for sprint-3)

| INV | Statement |
|---|---|
| INV-1 | Only ONE proactive-loop tick may modify `~/loops/<slot>/build_log.md` at a time (= fcntl, proven 2026-07-01) |
| INV-2 | LAYER B never blocks LAYER C: STEP 6 enqueues into `tasks/`; LAYER C dequeues at its own cadence |
| INV-3 | sprint-1 helpers MUST NOT be on cron after migration (= grep `launchctl list` for them = 0 hits) |
| INV-4 | run.sh and proactive-loop.sh MUST NOT both write `~/loops/<slot>/state/core-status.json` (= during migration, run.sh shim only) |
| INV-5 | bot2bot label `escalation` body MUST contain none of `_HUMAN_BODY_PHRASES` (= REQ-J8 inherited) |
| INV-6 | per-slot launchd plist + `<slot>-core-healthcheck.plist` may co-exist (different cadence) but NOT two LAYER A plists per slot |

## 7. What I will NOT do

- Won't remove `<slot>-core-healthcheck.plist` — it's the OS-level last-resort restart and runs at a different cadence.
- Won't change `<slot>-cli.sh` tmux core internals — sprint-2's job was outer orchestrator only.
- Won't auto-publish, auto-merge, or auto-send during migration — bot2bot's auto-merge is sprint-3+ (FIND-015 carry).
- Won't migrate slots without VCSDD adversary PASS on the new menu.json content per slot.

## 8. Open questions (= I resolve, no human gate)

| Q | Resolution |
|---|---|
| Where do `tasks/` items come from for hl-trade / finchip-publish / board-poller? | They get a stub `menu.json` and `tasks/` stays empty until each gets its own design spec (sprint-3+) |
| Does proactive-loop ever invoke `<slot>-cli.sh` to restart? | YES via STEP 3 `dispatch_highest_priority({tmux_dead: true})` recipe → `restart` action calls `<slot>-cli.sh --restart` (sprint-3 wires the real action) |
| Does LAYER B keep working if LAYER D (gh) is rate-limited? | YES — STEP 3 routes `api_rate_limit` to a haiku-model swap; bot2bot.post is best-effort with retry |
