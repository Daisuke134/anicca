# 11 — anicca-memory-weaver  (= memU retrieve / memorize each heartbeat)

| Field | Value |
|---|---|
| Spec ID | 11 |
| Status | DRAFT v1 (2026-06-03) |
| Agent | **anicca-memory-weaver** |
| Worktree | `.worktrees/memu/` |
| Branch | `feature/memu-heartbeat` |
| Wave | 1 (parallel with 10, 12, 15) |
| Authoritative for | memU integration, heartbeat memory layer, relationship + project + lesson categories |

---

## § 0. Why

Verified 2026-06-03: memU (NevaMind-AI, Apache-2.0, 13.7k★, "OpenClaw alternative" verbatim) works with DeepSeek (chat) + Ollama (embedding) at $0/month for embeddings and ~$0.001/conversation for memorize. Tanaka scenario E2E:

- 5-message conversation → 5.6s memorize → 6 items + 10 categories
- Query "Tanaka deadline?" → 3.7s → correct answer "30s motion graphics, ¥919, 2026-06-05"
- Query "unpaid invoice?" → 3.2s → correct answer "sent 2026-05-30, unpaid 2026-06-01"

The heartbeat currently runs every 2h with `claude -p` + rich prompt but **does not load relationship / project memory before deciding**. Adding `memU.retrieve` at orient and `memU.memorize` at end closes the loop.

## § 1. File boundary

**TOUCHES**

| Path | Purpose |
|---|---|
| `runtime/memu/setup.sh` | venv + memu-py install + Ollama nomic-embed-text pull |
| `runtime/memu/config.json` | LLM profile (DeepSeek default, Anthropic fallback) + categories |
| `runtime/memu/data/` | persistent SQLite + vector store (gitignored) |
| `runtime/memu/wrappers/retrieve.py` | CLI wrapper: stdin query → stdout JSON top-k items |
| `runtime/memu/wrappers/memorize.py` | CLI wrapper: stdin conversation file → stdout result |
| `runtime/memu/migrate-from-learnings.py` | one-time: read `~/.openclaw/.learnings/*.jsonl` → memU |
| `runtime/memu/README.md` | how to start |
| `_shared/heartbeat-memu.sh` | fragment called by heartbeat-beat.sh (orient + end) — **only file in `_shared/` this agent writes** |

**NEVER**

- `_shared/heartbeat-beat.sh` itself (= governance merges fragments)
- `_shared/heartbeat-friction-sweep.sh` (= Agent-7)
- `services/**`, `adapters/**`, `skills/**`, `deploy/**` (= other agents)
- `CONSTITUTION.md`, `specs/**` (= governance)

## § 2. Microtasks

| # | Task | Verify |
|---|---|---|
| 11.T1 | `runtime/memu/setup.sh`: python3.13 venv + `pip install memu-py agentmail` + Ollama pull `nomic-embed-text` | venv has memu installed, ollama list shows nomic-embed-text |
| 11.T2 | `config.json` with LLM profile (DeepSeek default + Anthropic fallback) + 4 memory_categories (Relationships / Projects / Lessons / Skills) | `python wrappers/retrieve.py < testq.json` returns valid JSON |
| 11.T3 | `wrappers/memorize.py` stdin = JSON list of messages → stdout = items + categories | unit test: Tanaka scenario re-run, 6 items extracted |
| 11.T4 | `wrappers/retrieve.py` stdin = JSON `{queries, top_k}` → stdout = ranked items | retrieve "Tanaka deadline" → top item contains "2026-06-05" |
| 11.T5 | `migrate-from-learnings.py`: read `~/.openclaw/.learnings/LEARNINGS.md` + `ERRORS.md` + `FEATURE_REQUESTS.md` → memorize each entry | post-migration count > 5 items |
| 11.T6 | `_shared/heartbeat-memu.sh`: bash fragment that (a) at start: dumps last 24h cron summaries + active projects → memorize, (b) at end: writes today_diary → memorize | dry-run with `MEMU_DRY_RUN=1` shows correct stdin/stdout |
| 11.T7 | Cost log: each invocation writes `~/.anicca/memU/cost.log` with prompt_tokens + completion_tokens + USDC equiv | log entries appear |
| 11.T8 | Integration test: run `heartbeat-memu.sh` as standalone, then verify retrieve returns relevant item from a beat 1h earlier | true positive ≥ 80% in 5 test queries |

## § 3. Dependencies

- Ollama daemon (= 既 `/opt/homebrew/bin/ollama`)
- DeepSeek API key (= 既 `DEEPSEEK_API_KEY` in `.env`)
- Python 3.13 venv at `~/.anicca-genesis/memU-test/.venv/` (= 既 created same day)

## § 4. DoD verification gates

| Gate | Evidence |
|---|---|
| G1 | `bash runtime/memu/setup.sh` exits 0 on fresh machine (= dogfood test) |
| G2 | Tanaka scenario via wrapper CLI exits 0 + retrieves correct deadline |
| G3 | `~/.openclaw/.learnings/` migration produced ≥ all existing entries in memU |
| G4 | `_shared/heartbeat-memu.sh` dry-run shows valid JSON in/out |
| G5 | Cost log shows ≤ $0.01 per heartbeat beat |
| G6 | True-positive retrieve rate ≥ 80% on 5-question test set |

## § 5. Anti-goals

- Not Mem0 (= verified self-hosted but no file-system metaphor)
- Not Letta (= not taste-tested in vivo)
- Not a separate vector DB (= memU's bundled SQLite + Ollama suffices)
- Not Inbox Zero memory (= scope = email, not full agent memory)

## § 6. Wire-in (= governance handles after agent completes)

After Agent-3 commits + pushes, governance edits `_shared/heartbeat-beat.sh` to add **2 lines**:

```bash
# After "ORIENT" comment block, before "FRICTION SWEEP":
bash "$HOME/.openclaw/skills/_shared/heartbeat-memu.sh" retrieve || true

# Before final SLACK report block:
bash "$HOME/.openclaw/skills/_shared/heartbeat-memu.sh" memorize || true
```

This is the only file-conflict point and governance owns the merge.

## § 7. Changelog

| Date | Change |
|---|---|
| 2026-06-03 | Initial draft. Born from spec 06 v2 stack revision (memU replaces Mem0/Letta/Inbox-Zero-memory). |
