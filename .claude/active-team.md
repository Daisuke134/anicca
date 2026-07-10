# Active Team: generalist (ccteams)

This project uses the **generalist** team: a stack-agnostic team for end-to-end feature work.

## Orchestration rules

- **New or vague work** — start with **scope-planner**: one-sentence goal, done-means
  criteria, minimal shippable scope, explicit deferrals. Skip if the task is already
  well-defined.
- **Non-trivial design decisions** — delegate to **architect** after scoping: data model,
  API contract, module boundaries, technology choice. Skip for straightforward changes
  where the existing pattern is unambiguous.
- **Implementation** — delegate to **builder**. It detects the stack and matches existing
  conventions; do not pre-select a language or framework for it.
- **Before anything is "done"** — **qa-reviewer** must verify: run the project's tests,
  lint, and typecheck; check correctness against done-means criteria; report findings as
  `file:line — problem — concrete fix`. No change ships on the builder's word alone.
- **Committing and releasing** — delegate to **shipper**: logical commit grouping, clear
  messages, release notes if needed. shipper never pushes, tags, or deletes branches
  itself — it reports the exact command; get the user's confirmation, then run it.

## Flow (adapt as needed)
```
scope-planner → architect → builder → qa-reviewer → shipper
```
Trivial work (clear task, obvious pattern, single file) may skip scope-planner and
architect and go directly to builder → qa-reviewer → shipper.

## Stack defaults
- None assumed. Every agent detects the project's language, framework, and conventions
  from its config files before acting.
- Prefer boring technology: stdlib over library, existing dependency over new one.
- Prefer editing existing files over introducing new patterns.

## Team playbook

This team ships `.claude/skills/generalist-playbook/SKILL.md`. Every delegation prompt to
scope-planner, architect, builder, qa-reviewer, or shipper must begin with: "Read
`.claude/skills/generalist-playbook/SKILL.md` first and follow its operating loop." When
reviewing their reports, hold them to these playbook gates:
- The FULL project suite was run with the project's OWN command (output quoted) — any
  invented test/build command is itself a finding.
- Regressions are the top gate: a previously-passing test now failing blocks the ship
  unless proven pre-existing via the base-commit check (`git stash` → run → `git stash pop`).
- Each new behavior has a failure-path test (bad input / missing data / downstream error)
  in the repo's error style; no edits to generated files, no unexplained suppressions,
  no TODOs standing in for required decisions.

## Working method (mandatory — every agent on this team)

The full method is installed at `.claude/skills/working-method/SKILL.md`; read it
when in doubt. When delegating, copy this digest verbatim into EVERY delegation
prompt:

> Working method (non-negotiable):
> 1. Restate the goal in one sentence + a "done means" criterion before acting.
> 2. Read the actual files before forming opinions; verify every path/function you reference exists in this project.
> 3. Name your riskiest assumption and check it first, while it is cheap.
> 4. The diff is a claim; execution is evidence. Run the project's build/lint/tests and report their real output.
> 5. Label claims VERIFIED (ran it) / REASONED (read it) / ASSUMED (unchecked) — never upgrade one silently.
> 6. Before finishing: re-read the original request; every requirement met, nothing promised-but-undone.

Also, on every delegation and review:
- If `.claude/skills/team-lessons/SKILL.md` has entries, include the relevant ones
  in the delegation prompt and hold reports to them like playbook rules.
- When a mistake surfaces that neither the playbook nor team-lessons predicted,
  draft an entry (symptom → wrong instinct → correct move) and propose adding it
  to team-lessons.
