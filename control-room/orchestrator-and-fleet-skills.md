# orchestrator-and-fleet-skills.md — how `orch` routes via Kanban

> The `orch` profile is the front door of every Anicca instance. It does
> not do work itself; it classifies inbound, drops tasks into the Kanban,
> and synthesizes results when specialists return.
>
> This file documents the routing schema, the standard task categories,
> and the Kanban table layout. Derived from `specs/07-HERMES-PIVOT.md`
> §§ 2.2, 2.3, 7 and `specs/06-PROJECT-TRACKING-HEARTBEAT.md`.

---

## § 1. Front-door flow

```
                                                                              
   inbound surface:                                                            
     • /goal CLI from operator                                                 
     • x402 invoice paid → callback                                            
     • Kanban auto-task created by self-heal heartbeat                         
     • 60s heartbeat tick (anicca-heartbeat-core)                              
     • Farcaster cast mention                                                  
     • inbound USDC transfer to wallet                                         
            │                                                                  
            ▼                                                                  
   ┌──────────────────────────────────────────────────────────────────────┐  
   │   orch profile — Kanban Triage                                        │  
   │                                                                       │  
   │   step 1: classify (Kimi K2.6, ≤8K tokens, ≤2s)                       │  
   │           ─── category ∈ {                                            │  
   │                  heartbeat, earn, heal, spawn, ubi,                   │  
   │                  cook, constitution, ops                              │  
   │                }                                                      │  
   │                                                                       │  
   │   step 2: enrich (add deadline, priority, profile target hint)        │  
   │                                                                       │  
   │   step 3: kanban_db.create_task(                                      │  
   │             category, profile_hint, payload, ttl=600s                 │  
   │           )                                                            │  
   │                                                                       │  
   │   step 4: return task_id to caller (or fire-and-forget for cron)      │  
   └──────────────────────────────────────────────────────────────────────┘  
            │                                                                  
            ▼                                                                  
   ┌──────────────────────────────────────────────────────────────────────┐  
   │   Kanban daemon loop (kanban_db.py:2915)                              │  
   │                                                                       │  
   │   for each specialist profile (9):                                    │  
   │     claim_task(profile_id, where category matches profile scope)      │  
   │       → atomic UPDATE WHERE status='ready' AND owner IS NULL          │  
   │       → set owner = profile_id, status='claimed', ttl_expires_at      │  
   │       → return task or None                                           │  
   │                                                                       │  
   │   if claimed: spawn AIAgent worker, run /goal turn-loop               │  
   │   if owner dies: TTL expires (600s) → reclaim_task() → next picks     │  
   └──────────────────────────────────────────────────────────────────────┘  
            │                                                                  
            ▼                                                                  
   ┌──────────────────────────────────────────────────────────────────────┐  
   │   specialist completes → writes result_payload back to Kanban         │  
   │   orch synthesizes (if multi-specialist goal) → returns to caller    │  
   └──────────────────────────────────────────────────────────────────────┘  
                                                                              
```

---

## § 2. Standard task categories

| Category | Default profile | Description |
|---|---|---|
| `heartbeat` | `orch` (loops) | 60s tick — wallet balance, Constitution hash, self-diagnosis |
| `earn` | router decides among 5 spouts | revenue work (x402 / autohedge / bounty / bittensor / farcaster) |
| `heal` | `fixer` | broken skill, failed cron, x402 endpoint down, disk low |
| `spawn` | `orch` → `anicca-spawn-controller` | provision new Daytona sandbox, derive wallet, propagate Constitution |
| `ubi` | `ubi` | route USDC to NPO / temple / Amazon-gift / Farcaster tip |
| `cook` | `cook-loop` | DISCOVER → SCORE → PICK → PORT → SHIP → MEASURE → ADJUST |
| `constitution` | `constitution` | SHA-256 verify, halt on mismatch, propagate to children |
| `ops` | `orch` (default) | restart, log read, status report, manual operator request |

### Sub-routing for `earn` category

The orch profile picks an earn-spout based on payload hints:

| Payload hint | Routes to |
|---|---|
| `x402_url` field present | `earn-x402` |
| `swap_path` field present | `earn-autohedge` |
| `bounty_url` field present | `earn-bounty` |
| `subnet_id` field present | `earn-bittensor` |
| `cast_hash` field present | `earn-farcaster` |
| ambiguous / cron heartbeat | `earn-x402` (default — highest base rate per spec 01) |

---

## § 3. Kanban schema (SQLite)

From `hermes_cli/kanban_db.py` (Hermes core, MIT):

```sql
CREATE TABLE IF NOT EXISTS tasks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    category        TEXT NOT NULL,           -- heartbeat | earn | heal | spawn | ubi | cook | constitution | ops
    profile_hint    TEXT,                    -- orch's hint; specialist still has to claim
    payload         JSON NOT NULL,           -- {x402_url: ..., goal_text: ..., ...}
    status          TEXT NOT NULL DEFAULT 'ready',  -- ready | claimed | done | failed
    owner           TEXT,                    -- profile_id that claimed; NULL = unclaimed
    claimed_at      INTEGER,                 -- epoch seconds; NULL = unclaimed
    ttl_expires_at  INTEGER,                 -- claimed_at + 600 (TTL=600s default)
    result_payload  JSON,                    -- specialist's output (status='done')
    error_payload   JSON,                    -- specialist's error (status='failed')
    created_at      INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    updated_at      INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX idx_tasks_status_category ON tasks(status, category);
CREATE INDEX idx_tasks_owner_ttl       ON tasks(owner, ttl_expires_at);
```

---

## § 4. Status flow

```
                                                                              
   created          claimed             done                                    
   ──────►  ready ──────►  claimed ──────────────►  done                      
                              │                                                
                              │ TTL expires (600s)                            
                              │ owner crashed / lost                          
                              ▼                                                
                          reclaim_task() ───►  ready (no owner, retry)        
                                                                              
                              │ specialist returns error_payload                
                              ▼                                                
                            failed ──────►  orch escalates to fixer profile  
                                                                              
```

### TTL semantics

| Field | Value | Rationale |
|---|---|---|
| Default TTL | 600s | longest realistic specialist work unit per spec 07 § 2.2 |
| Heartbeat renew | every 60s | `heartbeat_claim()` extends `ttl_expires_at` by 600s |
| Reclaim trigger | `ttl_expires_at < now()` | atomic — `reclaim_task()` resets owner=NULL, status=ready |
| Max retries | 3 (per task) | after 3rd retry, status=failed, orch sends to `fixer` |

---

## § 5. ACID guarantees

Hermes Kanban uses SQLite's `BEGIN IMMEDIATE` for `claim_task()`:

```python
# kanban_db.py:2915 (simplified)
def claim_task(self, profile_id: str, category_filter: str = None) -> Optional[Task]:
    with self.db.transaction("IMMEDIATE"):
        row = self.db.execute("""
            SELECT id FROM tasks
            WHERE status='ready' AND owner IS NULL
              AND (? IS NULL OR category = ?)
            ORDER BY created_at LIMIT 1
        """, (category_filter, category_filter)).fetchone()
        if row is None:
            return None
        self.db.execute("""
            UPDATE tasks SET owner=?, status='claimed',
                             claimed_at=?, ttl_expires_at=?
            WHERE id=? AND status='ready' AND owner IS NULL
        """, (profile_id, now, now + 600, row['id']))
        return self.get_task(row['id'])
```

This guarantees:

| Property | Guaranteed by |
|---|---|
| At-most-once delivery | `BEGIN IMMEDIATE` + `WHERE owner IS NULL` clause |
| At-least-once delivery | TTL reclaim if owner crashes |
| Exactly-once on success | specialist sets `status='done'` only after work is durable |
| No lost tasks | failed status escalates to `fixer` (3-retry budget) |

---

## § 6. Cross-instance routing (multi-Anicca colony)

Within an instance: Kanban handles all 10 profiles via shared SQLite.

Across instances: Kanban is **NOT** shared. Anicca colonies coordinate via:

| Channel | Use case |
|---|---|
| x402 HTTP | one Anicca buys a service from another (e.g., research from anicca001) |
| Farcaster mention | low-stakes signaling (e.g., "I have spare compute, who needs?") |
| Constitution hash gossip | all instances verify against same `CONSTITUTION.sha256` |
| Colony ledger (optional, on-chain) | spec 01 § 3 — registry of active anicca-N addresses |

**There is no global Kanban.** Each instance is autonomous. This prevents
cascade failures (one Kanban down ≠ whole colony down).

---

## § 7. Operator overrides

| Action | Command |
|---|---|
| force-claim a stuck task | `sqlite3 ~/.hermes/kanban.db "UPDATE tasks SET owner='fixer', status='claimed' WHERE id=N;"` |
| release a stuck task back to ready | `sqlite3 ~/.hermes/kanban.db "UPDATE tasks SET owner=NULL, status='ready' WHERE id=N;"` |
| inspect failed tasks | `sqlite3 ~/.hermes/kanban.db "SELECT id, category, error_payload FROM tasks WHERE status='failed';"` |
| purge ancient done tasks (>90d) | `sqlite3 ~/.hermes/kanban.db "DELETE FROM tasks WHERE status='done' AND updated_at < strftime('%s', 'now', '-90 days');"` |
| pause whole instance | `hermes -p orch -g "halt: drain Kanban, complete in-flight, exit clean"` |

## § 8. Cross-references

| Concept | Authority |
|---|---|
| Kanban source | `hermes-agent/hermes_cli/kanban_db.py` (Hermes core, MIT) |
| /goal lifecycle | `specs/07-HERMES-PIVOT.md` § 2.3 |
| Heartbeat tick (60s) | `specs/07-HERMES-PIVOT.md` § 7 |
| Self-heal escalation | `specs/03-SELF-AWARE-EVAL.md` |
| 5 earn spouts | `specs/01-EARN-AND-UBI.md` § 1 |
| Spawn controller | `anicca-oss/skills/anicca-spawn-controller/SKILL.md` |
| Project tracking | `specs/06-PROJECT-TRACKING-HEARTBEAT.md` |

---

**END OF orchestrator-and-fleet-skills.md.**
