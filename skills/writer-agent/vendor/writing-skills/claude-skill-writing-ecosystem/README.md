# claude-skill-writing-ecosystem

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/shimo4228/claude-skill-writing-ecosystem) [![GitMCP](https://img.shields.io/endpoint?url=https://gitmcp.io/badge/shimo4228/claude-skill-writing-ecosystem)](https://gitmcp.io/shimo4228/claude-skill-writing-ecosystem)

A [Claude Code skill](https://docs.claude.com/en/docs/claude-code/skills) that orchestrates the **human-facing writing & review ecosystem** — articles, essays, blog posts, newsletter issues, and other long-form human-primary content.

Holds the canonical AI-slop banned list (Japanese + English), Voice rules (だ/である × 発見調 / declarative × discovery tone), title conventions, and the role-boundary map across `article-writing`, `editor`, `essay-reviewer`, and `fact-checker`.

> For AI-facing documents (`llms.txt` / `llms-full.txt` / FAQ pages / glossaries), use [llms-txt-writer](https://github.com/shimo4228/llms-txt-writer) instead. Audience separation is enforced by these two skills owning distinct concerns.

## Install

This repo bundles **both the skill and the agents it orchestrates** (`editor` / `essay-reviewer` / `fact-checker`). The agents read their canonical rules (AI-slop list, Voice, title conventions) from the `writing-ecosystem` skill, so the skill and its agents must be installed together.

### Option A — one command (recommended)

```bash
git clone https://github.com/shimo4228/claude-skill-writing-ecosystem
cd claude-skill-writing-ecosystem
./install.sh
```

Copies `skills/*` into `~/.claude/skills/` and `agents/*.md` into `~/.claude/agents/`. Existing files are backed up to `*.bak-<timestamp>` first (use `--force` to skip backups, `--dry-run` to preview).

### Option B — manual

```bash
cp -r skills/writing-ecosystem ~/.claude/skills/writing-ecosystem
cp agents/*.md ~/.claude/agents/
```

No runtime dependencies; the skill is documentation-only.

> The `article-writing` drafting skill referenced in the ecosystem map is **not bundled** — it comes from [Everything Claude Code](https://github.com/affaan-m/everything-claude-code) (MIT). Install it separately for the drafting half; the review half (this skill + its agents) works without it.

### SkillsMP

```bash
/skills add shimo4228/claude-skill-writing-ecosystem
```

> **Caveat:** SkillsMP installs `skills/` only — not `agents/`. After `/skills add`, copy the agents: `cp agents/*.md ~/.claude/agents/` (or use Option A).

## Ecosystem map

The skill enforces a **2D role separation** — `Write / Review` × `Quality / Logic / Facts`:

| Phase | Component | Axis | Trigger |
|---|---|---|---|
| **Write** | `article-writing` skill | general drafting | any writing task — first drafts, structure |
| **Review: Quality** | `editor` agent | tech-article structure, code, AI slop, terminology | tech-article review |
| **Review: Logic** | `essay-reviewer` agent | idea-article logic, overload, tone | idea-article review |
| **Review: Facts** | `fact-checker` agent | web-verification of factual claims | before publication |
| **Shared** | `writing-ecosystem` skill (this one) | AI slop / Voice / ecosystem map | auto-loaded on writing + review |
| **Overlay** | `<project>/.claude/rules/<platform>-writing.md` | platform-specific rules | inside the project only |

## Key contributions

- **AI-slop banned list (JA + EN)** — concrete substitutions, not vague advice. e.g. 「画期的」/ "powerful tool" / "revolutionize" — banned, with replacement strategies
- **Voice convention** — だ/である × 発見調. Declarative tense, discovery tone. Strategy for *weakening conclusions* into rhetorical questions (modeled on early Buddhist 阿含経 patterns)
- **Title conventions** — concrete, honest, question-form OK, no emotional clickbait
- **Three-stage question architecture** — title-level + thesis-shape + mid-article rhetorical questions, so the conclusion is reached *with* the reader rather than imposed
- **Project overlay slot** — platform-specific rules (Zenn character limits, Qiita tag conventions, corporate blog restrictions) extend the base via `<project>/.claude/rules/`

## Audience boundary

| Audience | Skill |
|---|---|
| Humans (articles, essays, blog posts, newsletters) | `writing-ecosystem` (this skill) |
| AI search engines / LLM agents (`llms.txt`, `llms-full.txt`, FAQ, glossary) | [llms-txt-writer](https://github.com/shimo4228/llms-txt-writer) |

The two skills do not overlap. Mixing audiences in one document makes both worse.

## Related

- [`editor`](agents/editor.md) agent — tech-article review (**bundled** in this repo's `agents/`)
- [`essay-reviewer`](agents/essay-reviewer.md) agent — idea-article review (**bundled**)
- [`fact-checker`](agents/fact-checker.md) agent — web-based fact verification (**bundled**)
- [`article-writing`](https://github.com/affaan-m/everything-claude-code/tree/main/skills/article-writing) — general writing framework from **Everything Claude Code (ECC)** by Affaan Mustafa (MIT). Not bundled; its Banned Patterns are subsumed by this skill's superset
- [llms-txt-writer](https://github.com/shimo4228/llms-txt-writer) — AI-facing documents (`llms.txt` etc.)

The three review agents are also maintained in [claude-harness](https://github.com/shimo4228/claude-harness) (upstream origin); this repo vendors them so the ecosystem installs as one unit.

## Acknowledgments

The `article-writing` skill referenced in the ecosystem map is **not authored by this repo**. It comes from [Everything Claude Code (ECC)](https://github.com/affaan-m/everything-claude-code) by [Affaan Mustafa](https://github.com/affaan-m), MIT-licensed. This skill (`writing-ecosystem`) layers a superset of conventions on top of it — AI-slop banned list, Voice rules, title rules, role boundaries — but the general drafting framework itself is ECC's contribution.

Thank you to ECC and to Affaan Mustafa for the foundational `article-writing` skill that this ecosystem depends on.

## License

MIT. See [LICENSE](LICENSE).
