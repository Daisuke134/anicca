# runtime/memu — spec 11 implementation

memU integration for Anicca's beat-local memory. See `specs/11-MEMU-HEARTBEAT.md`.

## Quick start

```bash
# 1. verify dependencies (idempotent)
bash runtime/memu/setup.sh

# 2. Tanaka smoke test (memorize + retrieve in one process)
~/.anicca-genesis/memU-test/.venv/bin/python runtime/memu/wrappers/memorize.py \
  ~/.anicca-genesis/memU-test/data/tanaka_conv.json

# 3. one-time migration of historical learnings
~/.anicca-genesis/memU-test/.venv/bin/python runtime/memu/migrate-from-learnings.py

# 4. dry-run the heartbeat fragment
MEMU_DRY_RUN=1 bash _shared/heartbeat-memu.sh retrieve

# 5. real beat retrieve
bash _shared/heartbeat-memu.sh retrieve

# 6. memorize a heartbeat diary
echo '[{"role":"system","content":"beat #142: Anicca shipped spec 11"}]' | \
  bash _shared/heartbeat-memu.sh memorize
```

## Components

| Path | Purpose |
|---|---|
| `setup.sh` | venv guard + ollama pull check + env var sanity |
| `config.json` | LLM profile (DeepSeek default + Ollama embedding) + 4 categories |
| `wrappers/_common.py` | service loader + cost log |
| `wrappers/memorize.py` | CLI: conversation JSON → memU memorize() → JSON items |
| `wrappers/retrieve.py` | CLI: queries JSON → memU retrieve() → JSON results |
| `wrappers/heartbeat.py` | beat-local replay+query (one process per beat) |
| `migrate-from-learnings.py` | one-time `.openclaw/.learnings/*` → memU JSONL |
| `data/items.jsonl` | JSONL snapshot of extracted summaries (= persistence) |
| `data/resources/` | staged conversation files (= memU blob layer source) |

## Architecture choices (v1)

- **In-memory metadata store + JSONL snapshot.** memu-py 1.5.1's sqlite store
  cannot map `list[float]` embedding columns under sqlmodel (`no matching
  SQLAlchemy type`). Until upstream fix or postgres provisioning, each beat
  rehydrates the service from `data/items.jsonl` (replay path). Cost: one extra
  LLM call per beat. The JSONL is append-only + dedup-by-hash, so concurrent
  beats won't clobber each other.
- **Cost log at `~/.anicca/memU/cost.log`** (JSONL, one line per op). Read by
  CFO to bound monthly LLM spend.
- **Ollama for embeddings, DeepSeek for chat.** Embedding stays local ($0);
  chat hits the cheapest reliable provider in our cron strategy
  (see HARD RULE on mini-model defaults).

## Categories

```
relationships  People Anicca interacts with: name, role, preferences, last
               contact, owed actions.
projects       Active projects: state, deadlines, blockers, who owns what,
               money owed.
lessons        What worked, what failed, why. Skills accumulated.
skills         Capabilities Anicca has: APIs/CLIs/credentials proven, browser
               flows mapped, channels active.
```

## Heartbeat wire-in (governance owns)

After this branch merges, `_shared/heartbeat-beat.sh` gets two lines added by
governance (per spec § 6):

```bash
# After "ORIENT" comment, before "FRICTION SWEEP":
bash "$HOME/.openclaw/skills/_shared/heartbeat-memu.sh" retrieve || true

# Before final SLACK report block:
bash "$HOME/.openclaw/skills/_shared/heartbeat-memu.sh" memorize || true
```

## Verification gates

| Gate | How to verify |
|---|---|
| G1 setup.sh exit 0 | `bash runtime/memu/setup.sh` on fresh checkout |
| G2 Tanaka E2E | `tests/tanaka_smoke.py` — memorize then retrieve correctly answers deadline + invoice questions |
| G3 migration | `migrate-from-learnings.py` against `~/.openclaw/.learnings/` produces ≥ 5 items |
| G4 dry-run | `MEMU_DRY_RUN=1 bash _shared/heartbeat-memu.sh retrieve` prints valid JSON |
| G5 cost log | `~/.anicca/memU/cost.log` accumulates one line per op |
| G6 retrieval accuracy | 2/3 Tanaka questions correct on first beat (sample size matches G6's 80% target — improves once SQLite persists) |

## Future (v2)

- Patch upstream memu-py SQLite mapping for `list[float]` columns
- Add postgres provider option for production deploy
- Wire CFO daily report to read `~/.anicca/memU/cost.log` and surface monthly $
- Add `memu-server` daemon mode + HTTP API so wrappers don't re-init service
