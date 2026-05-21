# Skills (single source of truth)

**Add or edit skills only here.** `.claude/skills` and `.codex/skills` are symlinks to this directory — they stay in sync automatically.

| Path | Type |
|------|------|
| `.cursor/skills` | **Canonical** (edit here) |
| `.claude/skills` | Symlink → `../.cursor/skills` |
| `.codex/skills` | Symlink → `../.cursor/skills` |

Root docs `CLAUDE.md` and `AGENTS.md` are also synced: repo root is canonical; `.claude/CLAUDE.md` and `.claude/AGENTS.md` are symlinks to them.
