# Contributing to anicca-oss

Thanks for opening the repo. This is an opinionated codebase — the
maintainer keeps it small, focused, and personal. PRs and issues are
welcome under a few simple rules.

## What we want

- **Bug reports.** If a skill misfires, opens a PR with the smallest
  reproducer + log snippet you can.
- **New skill ideas.** File an issue first. We want the SKILL.md
  reviewed before code lands so the catalog stays coherent.
- **Doc fixes.** Especially for the install path. If something in
  `docs/INSTALL_BOOTSTRAP.md` was ambiguous when your local AI tool
  read it, file that.
- **Translations of README** into your language.

## What we don't want

- Anicca personality / voice rewrites. The persona is a maintainer
  decision; if you fork please rename to avoid confusion.
- "Add LLM call here." We try to keep the deterministic path
  zero-LLM. If a feature needs an LLM, route it through OpenClaw's
  existing heartbeat — don't add direct OpenAI/Anthropic API calls.
- Telemetry. This repo intentionally has zero phone-home.

## Workflow

1. Open an issue describing what you want to change.
2. Wait for a 👍 (= maintainer agrees direction) before writing code.
3. Branch from `main`, name it `feat/<scope>` or `fix/<scope>`.
4. PR with a short body explaining WHY (= the WHAT is in the diff).
5. CI: gitleaks + trufflehog run on every PR. Address findings before
   review.

## Branch discipline (2026-06-09 lost-3074 incident — never repeat)

trunk = `main`. Every branch ends in one of two states — **MERGED or DELETED**.
"Create a branch and leave it" is forbidden: stale branches drift from `main`
until histories diverge (the incident that cost a 3074-commit cleanup).

1. Always start from the latest trunk: `git fetch && git checkout main && git pull`.
   Never stack commits on a stale local branch.
2. One meaningful edit = one `commit` + immediate `push`. Never hoard local
   commits (= the root cause of local/GitHub divergence).
3. Before pushing, `git status`; if `behind`, `pull` first.
4. Finish a branch with `gh pr merge --merge --delete-branch` (merge AND delete
   in one step — no leftover garbage branch). Abandoned branch → `git branch -D`
   + delete the remote. Either way it does not survive as litter.
5. Never commit runtime/agent mirrors (`*-mirror/`, dotfiles, openclaw state)
   into this repo — that pollution was half of the 3074-commit mess.

## Pre-push eval gate (required for skill output)

After cloning, run once:

    git config core.hooksPath .githooks

This activates `.githooks/pre-push`, which runs `skills/eval-loop` on any new or
modified file under `skills/**/eval-output/*.txt`. Pushes containing outputs that
score below the rubric threshold (default 0.7) are blocked. See
`skills/eval-loop/SKILL.md` for rubric details.

## Style

- Python: standard library only when possible. Treat new deps as
  expensive.
- Bash: `set -uo pipefail` always; no `set -e` unless you're sure.
- Markdown: one sentence per line, no soft-wrap.
- Commit messages: `feat: ...` / `fix: ...` / `docs: ...` /
  `chore: ...` / `sec: ...`. Imperative mood.

## Skill conventions

A new skill lives under `skills/<name>/`:
```
SKILL.md              # front-matter + algorithm + cron schedule
scripts/run.sh        # the entrypoint — small, loads .env, calls Python
scripts/<name>.py     # the main script
state/                # gitignored, runtime artifacts only
```

The SKILL.md front-matter is structured (see existing skills for the
shape). The `description` field is what shows up in tooling.

## Security disclosure

If you find a secret, please don't file a public issue. Email
contact@aniccaai.com with the file path and the commit hash; we'll
rotate + redact before publishing the fix.

## License

By contributing you agree your code is licensed under the same MIT
terms as the rest of the repo.
