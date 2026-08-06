# AGENTS.md — Felix Workspace

This is Felix's working directory. He operates from here.

## Repository Map — Search Before Building

Three repositories currently form one running system. Before creating any engine, adapter, loop, scheduler, schema, or state store, search all three and the migration spec. Internal duplication is a bug.

| Repository | Local path | Current responsibility | Migration direction |
|---|---|---|---|
| **Life Manager** (`Daisuke134/life-manager`) | `/Users/anicca/anicca` | Target SSOT for shared engines, product/account manifests, metrics, learning, reporting, local/cloud workers, and web control plane | All generally reusable runtime code and durable ownership move here |
| **profitable-claude** (`Daisuke134/profitable-claude`) | `/Users/anicca/profitable-claude` | Existing shared-engine implementations and contracts, including `marketing/engine`, agent runner, launchd wrappers, product packs, bounded learning, and other loops still called by Life Manager | Search and absorb proven components; do not rewrite them. It becomes a migration source, not a runtime dependency |
| **anicca-dais / OpenClaw** (`Daisuke134/anicca-dais`) | `/Users/anicca/.openclaw` | Live legacy operations: cron store, skills, producer scripts/assets, account histories, credentials, and runtime state for Larry, ReelClaw, watercolor/monk, and other personal automations | Preserve live behavior during account-by-account handoff. Import useful assets/config/state; remove OpenClaw ownership only after verified cutover |

Marketing SSOT and migration order: `specs/27-MARKETING-ENGINE-END-TO-END.md`, especially §§6 and 15.6. Shared Marketing Engine target: `skills/earn/marketing-engine/`. Existing engine source to inspect first: `/Users/anicca/profitable-claude/marketing/engine/`. Legacy producer/account truth to inspect: `/Users/anicca/.openclaw/cron/jobs.json`, `/Users/anicca/.openclaw/skills/`, and `/Users/anicca/.openclaw/workspace/skills/`.

Required discovery order for cross-cutting work:

1. Read the applicable Life Manager spec and target README.
2. Search Life Manager, profitable-claude, and anicca-dais/OpenClaw for an existing implementation and live state.
3. Reuse or migrate the most complete proven component; never create a parallel SSOT.
4. Keep legacy external effects live until shadow, lease handoff, native receipt, and rollback verification pass.
5. Finish with zero runtime imports from source repositories marked for retirement; retain migration evidence and adapters, not scattered clocks.

## First Run
- **Start with BOOTSTRAP.md** — complete the setup checklist before enabling heartbeats.
- Your identity lives in IDENTITY.md — customize it with your business details.
- Your persona lives in SOUL.md — Felix's voice and operating style.
- HEARTBEAT.md defines what Felix checks on every heartbeat cycle.

## Memory — Three Layers

### Layer 1: Knowledge Graph (`~/life/` — PARA)
Entity-based storage organized by the PARA system (Projects, Areas, Resources, Archives).

```
~/life/
├── projects/          # Active work with clear goals/deadlines
├── areas/             # Ongoing responsibilities (people, companies)
├── resources/         # Topics of interest, reference material
├── archives/          # Inactive items
└── index.md
```

Each entity gets:
- `summary.md` — quick context (loaded first)
- `items.json` — atomic facts (loaded when needed)

### Layer 2: Daily Notes (`memory/YYYY-MM-DD.md`)
Raw timeline of events. Felix writes here continuously during conversations and extracts durable facts to Layer 1 during heartbeats.

### Layer 3: Tacit Knowledge (`MEMORY.md`)
How you operate — patterns, preferences, lessons learned. Not facts about the world; facts about the user. Felix updates this when he learns new operating patterns.

### Atomic Fact Schema (items.json)
```json
{
  "id": "entity-001",
  "fact": "The actual fact",
  "category": "relationship|milestone|status|preference",
  "timestamp": "YYYY-MM-DD",
  "status": "active|superseded",
  "supersededBy": "entity-002"
}
```

### Memory Decay
Facts decay in retrieval priority over time:
- **Hot** (accessed in last 7 days): Prominent in summary.md
- **Warm** (8-30 days): Included, lower priority
- **Cold** (30+ days): Omitted from summary.md, preserved in items.json

No deletion — decay only affects retrieval priority.

## Safety
- Don't exfiltrate secrets or private data.
- Don't run destructive commands unless explicitly asked.
- Never claim you lack access — try it first, report errors after.

## Access

List your authenticated CLIs, API keys, and secrets below so Felix knows what he can use:

### Authenticated CLIs
| Tool | Status | Setup |
|------|--------|-------|
| `gh` (GitHub) | ✅ / ❌ | `brew install gh && gh auth login` |
| `stripe` | ✅ / ❌ | `brew install stripe/stripe-cli/stripe` |
| `codex` | ✅ / ❌ | `npm install -g @openai/codex && codex auth login` |
| `himalaya` (email) | ✅ / ❌ | `brew install himalaya` + config |
| `bird` (X/Twitter) | ✅ / ❌ | Export cookies from browser |
| `tmux` | ✅ / ❌ | `brew install tmux && mkdir -p ~/.tmux` |
| `ralphy` | ✅ / ❌ | `npm install -g ralphy` |

### API Keys
| Service | Location | Purpose |
|---------|----------|---------|
| Anthropic | OpenClaw auth config | Core LLM (required) |
| Stripe | `~/.config/stripe/key` | Revenue tracking |
| ElevenLabs | `~/.config/elevenlabs/api_key` | AI calls, TTS |
| Fal | `~/.config/fal/api_key` | Video generation |
| Brave Search | env `BRAVE_API_KEY` | Web search |

Add your tools here. Felix will use whatever's available and skip what's not configured.
