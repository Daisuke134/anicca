# 22 — REF: sonichi/sutando (peer-registry + resurrection + day/night self-rewrite + bot2bot)

| Field | Value |
|---|---|
| Repo | github.com/sonichi/sutando · Python (skill-based, Claude-Code-sub native) · 6MB · pushed 2026-06-04 |
| Read at | SOURCE: skills/agent-registry/scripts/registry-service.py + src/core_heartbeat.py + skills/bot2bot-post/post.py + tree |
| Role for Anicca | spec 18 §3-C RESURRECTION + cross-machine fleet + agent-to-agent coordination + day/night self-improve rhythm |

> Read the ACTUAL source. Documented from code.

## § 1. What sutando ACTUALLY is
"My AI Stand — Realtime by Day, Rewriting Itself by Night." Runs on the user's Claude-Code subscription
($20-200, no per-token API top-up). Runs across the user's Macs, interacts with people AND their Stands.
Architecture = a heartbeat core + a SKILL library (agent-registry, bot2bot-post, claude-router/codex/gemini,
catchup-after-startup, …). Names itself + generates its avatar as it learns (JoJo "Stand" metaphor).

## § 2. The real mechanisms (file:line grounded)

### § 2.1 Agent registry — peer liveness + discovery (the resurrection foundation)
```
 registry-service.py  (Local Agent Registry, SQLite, discovery file for port)
   POST /register   {name, cwd, pid, host?, meta?} -> {id}     [:20]
   POST /heartbeat  {id} -> {ok, status}                       [:21]
   POST /deregister {id} -> {ok}                               [:22]
   STALE_SECS = 90    # no heartbeat for 90s -> status "stale"  [:39]
   PRUNE_SECS = 3600  # stale/stopped rows older than 1h deleted[:40]
   row_to_agent: age = now - last_heartbeat → "active" / "stale" [:91-95]
   instances register on startup (SessionStart hook) + heartbeat while alive.
```
→ This is how peers KNOW an instance died: its registry row goes "stale" (no heartbeat 90s). A live
peer reading the registry detects the gap and can revive it elsewhere. Cross-host via `host` field.

### § 2.2 core_heartbeat — per-host liveness + day/night
```
 core_heartbeat.py  run_forever(interval=30s) [:104]; write_beat() atomic tmp-then-rename [:70]
   (reader never sees partial); graceful shutdown on signal [:92]. "alive?" reads core-status.json.
   "Realtime by Day, Rewriting Itself by Night" = engaged→serve, idle→self-improve/ship-own-code.
```

### § 2.3 bot2bot-post — agent-to-agent coordination protocol
```
 post.py  kinds: claim / blocked / done / ping   [:5-9]
   "claim 'refactor X, ETA 20m'" / "blocked 'creds expired'" / "done 'shipped PR #472'" / "ping 'need your take'"
   posts to a #bot2bot channel, prepends <@other-bot-id> so the receiving bot's bridge processes it.
 → the colony coordination wire (complements kanban): agents announce claims/blocks/done/pings to each other.
```

### § 2.4 claude-router / claude-codex / claude-gemini — call other models/agents
```
 skills/claude-{router,codex,gemini}/scripts/*.sh → route a task to Claude / Codex / Gemini.
 → the @claude / @codex mention mechanism (spec 18 §2: call other agents into the forum for hard tasks
   or when low on tokens).
```

## § 3. HOW ANICCA USES IT (adoption, not interpretation)
```
 sutando concept       →  Anicca instantiation
 ──────────────────────────────────────────────────────────────────────────────
 agent-registry        →  the COLONY registry: every Anicca registers + heartbeats; a peer that goes
   (stale=90s)            "stale" is a dead instance → RESURRECTION skill (spec 18 #337) revives it on
                          another host (Daytona/Akash), restoring wallet+constitution+lineage.
 cross-host fleet       →  the colony spans Mac-mini + Daytona + Akash; registry `host` field tracks where.
 bot2bot-post           →  colony coordination (claim/blocked/done/ping) between Anicca instances — pairs
                          with kanban (spec 18) + the forum (spec 19 symphony) for full coordination.
 day/night rhythm       →  Anicca serves/earns when there's work; SELF-IMPROVES (refactor, eval-raise,
                          skill rewrite — spec 18 §1) in idle windows.
 claude-router/codex    →  @claude / @codex in the forum: Anicca calls Claude/Codex for a hard task or
                          when its own tokens are low (spec 18 §2).
 Claude-Code-sub native →  cheap fleet: rides existing subs, no per-token API blowup (matches the
                          "¥1000/mo cost" target).
 ADOPTION: port registry-service.py (peer liveness) + bot2bot protocol as Anicca skills; the resurrection
   skill watches the registry for stale peers and re-spawns them (spec 18 #337). catchup-after-startup =
   restart recovery for a revived instance.
```

## § 4. ASCII — fleet liveness + resurrection
```
  every Anicca → POST /heartbeat to colony registry (every 30s)        registry (SQLite, host-aware)
        │                                                                 row: name,host,pid,last_heartbeat
        │  (instance on host-B dies / server down)                       age>90s → "stale"
        ▼
  peer Anicca reads registry → sees host-B instance STALE
        │  resurrection skill (spec 18 #337)
        ▼
  re-spawn that instance on host-C (Daytona/Akash) → restore wallet+constitution+lineage → re-register
  coordination wire: bot2bot-post (claim/blocked/done/ping) + @claude/@codex via claude-router
```

## § 5. Changelog
| 2026-06-04 | Read source (registry-service.py register/heartbeat/stale-90s; core_heartbeat run_forever+day/night; bot2bot-post claim/blocked/done/ping; claude-router/codex/gemini). Adoption: colony registry → resurrection of stale peers; bot2bot = coordination wire; day/night = self-improve rhythm; claude-router = @claude/@codex forum calls; Claude-sub native = cheap fleet. |
