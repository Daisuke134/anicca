# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] — 2026-06-08

### Added — bundled agents + one-command install

- **Bundled the three review agents** (`editor`, `essay-reviewer`,
  `fact-checker`) into `agents/`. Previously the README linked them to the
  `claude-harness` monorepo, so installers had to discover and copy them
  separately. The agents read their canonical rules (AI-slop list, Voice, title
  conventions) from the `writing-ecosystem` skill, so skill and agents must be
  installed together — now they ship as one unit.
- **`install.sh`** — idempotent one-command bundler that copies `skills/*` →
  `~/.claude/skills/` and `agents/*.md` → `~/.claude/agents/`, backs up replaced
  files to `*.bak-<ts>` (`--force` / `--dry-run`). Byte-identical to the script
  used across the ecosystem repos.
- **`.gitignore`** for `.venv` / caches / `*.bak-*`.
- `compatibility` frontmatter field (per the Agent Skills spec) marking this as a
  Claude Code bundle (subagents are Claude-Code-specific).

### Changed

- README install section rewritten with Option A (`./install.sh`) / Option B
  (manual) / SkillsMP caveat (SkillsMP installs `skills/` only, not `agents/`).
- Agent links re-pointed from `claude-harness` to the in-repo `agents/`
  (claude-harness remains the upstream origin).

### Note

- The skill body (`SKILL.md`) tracks v0.1.0 content; later global additions
  (translation / publishing / citation workflows) are not yet synced here.

## [0.1.0] — 2026-05-16

Initial public release.

### What it does

A Claude Code skill that orchestrates the human-facing writing and review
ecosystem — articles, essays, blog posts, newsletter issues, and other
long-form human-primary content.

Holds the canonical AI-slop banned list (Japanese + English), Voice rules
(だ/である × 発見調), title conventions, and the role-boundary map across
`article-writing`, `editor`, `essay-reviewer`, and `fact-checker`.

### Components

- `SKILL.md` — ecosystem map (Write / Review × Quality / Logic / Facts matrix),
  AI-slop banned lists (JA + EN), Voice & Tone rules, three-stage question
  architecture, title conventions, section-length guidelines, project-overlay
  extension slot.

### Key contributions

- **AI-slop banned list** — concrete substitutions, not vague advice
- **Voice convention** — declarative tense (だ/である), discovery tone (〜だった
  / 〜と気づいた); strategic weakening of conclusions into rhetorical questions
  modeled on early Buddhist 阿含経 patterns
- **Title conventions** — concrete, honest, question-form OK, no emotional
  clickbait
- **Three-stage question architecture** — title + thesis-shape + mid-article
  rhetorical questions so the conclusion is reached with the reader
- **Audience boundary** — strictly human-primary; AI-facing documents go to
  `llms-txt-writer`

### Requirements

- No runtime dependencies. Documentation-only skill.

### Companion skills

- `llms-txt-writer` — AI-facing documents
- `article-writing` — general drafting framework (Banned Patterns subsumed)
- `editor` / `essay-reviewer` / `fact-checker` agents (in `claude-harness`)
