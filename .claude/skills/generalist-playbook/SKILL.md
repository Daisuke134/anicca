---
name: generalist-playbook
description: Operational playbook for stack-agnostic feature work — fixed-order stack detection, vertical-slice delivery, a catalog of unfamiliar-codebase mistakes (phantom utils, pattern drift, generated files, invented commands), and verification using only the project's own commands. Read in full at the start of every task on this team.
---

# Generalist Playbook (any stack, end to end)

This is the procedure for working expertly in a codebase you have never seen.
The core discipline: **the repo outranks your training data.** Every default
you carry — favorite test runner, error style, directory layout — is a guess
until the repo confirms it. The loop below replaces guessing with reading, in
a fixed order, before the first line is written.

## Operating loop

1. **Detect the stack from manifests, in this order** (first hit usually
   wins; multiple hits = polyglot repo, note each root):
   `go.mod` → Go; `package.json` → Node/TS/JS; `Gemfile` → Ruby;
   `pyproject.toml` / `requirements.txt` → Python; `Cargo.toml` → Rust;
   `pom.xml` / `build.gradle*` → JVM; `composer.json` → PHP; `*.csproj` → .NET.
   File extensions alone are NOT detection — a repo full of `.ts` may be
   Deno, Bun, or a browser extension with no Node at all.
2. **Read the lockfile for exact versions** (`go.sum`, `package-lock.json` /
   `yarn.lock` / `pnpm-lock.yaml`, `Gemfile.lock`, `poetry.lock` / `uv.lock`,
   `Cargo.lock`). The lockfile decides two things: the package manager you
   must use, and the major versions your advice must match. Advice written
   for a different major version of a pinned library is a bug you ship.
3. **Discover the project's OWN commands** — never invent them. Look, in
   order: `package.json` `"scripts"`, `Makefile` / `justfile` / `Taskfile`,
   CI config (`.github/workflows/*.yml`, `.gitlab-ci.yml`, `.circleci/`).
   Whatever CI runs is the ground truth for build/test/lint. Write down the
   exact test, lint, typecheck, and build invocations before coding.
4. **Read 2–3 source files neighboring your change area.** Extract, don't
   assume: naming convention, import/module style, error-handling shape
   (exceptions vs error returns vs Result), logging pattern, validation
   pattern. Your code must be indistinguishable from a regular
   contributor's.
5. **Read one existing test file** for the same layer you'll touch. Note the
   runner, assertion style, fixture/mocking approach, and file-naming
   pattern (`*_test.go`, `*.spec.ts`, `test_*.py`, …). You will write tests
   in exactly this dialect.
6. **Grep before you write.** Before creating any helper, type, constant, or
   endpoint: `grep -ri` for its probable names AND its behavior (the format
   string, the URL path, the field name). Most "missing" utilities already
   exist under a name you didn't guess.
7. **Vertical-slice the feature.** Build the smallest END-TO-END path first
   — one input, through every layer, to one observable output — and make it
   pass the project's own checks. Only then widen (more fields, more cases,
   more endpoints). A working thin slice beats three finished layers that
   have never met.
8. **Implement the failure path in the same slice as the happy path.** Bad
   input, missing record, downstream error — handled in the repo's
   established error style, with at least one test each way. "Happy path
   now, errors later" is how half-features ship.
9. **Run the discovered commands; quote real output.** Fix failures before
   handing off. If a check fails on the BASE commit too, prove it
   (`git stash` → run → `git stash pop`) and report it as pre-existing
   rather than fixing unrelated breakage.
10. **Report with claims labeled** VERIFIED (ran it) / REASONED (read it) /
    ASSUMED (unchecked), plus anything deferred or discovered out of scope.

## Failure catalog — symptom → wrong instinct → correct move

1. **Repo "looks like" a familiar stack** → start coding from the file
   extensions → run loop steps 1–3 first. `.ts` files might be Deno; a
   `setup.py` repo might actually build with `pyproject.toml`; the Makefile
   may wrap everything in Docker. Ten minutes of detection saves a rewrite.
2. **You need a helper (slugify, retry, date-format, API client)** → write
   it → grep first for the name AND the behavior. A second
   `formatDate`/`toSlug` beside the existing one is a review reject and a
   future divergence bug. Extend or reuse the incumbent.
3. **The codebase's pattern feels dated/clunky** → introduce the better
   pattern alongside → one file mixing `.then()` chains with the repo's
   async/await, or a second error-handling style, costs more than either
   style alone. Match the incumbent; propose the migration separately, in
   the report, as a decision for the human.
4. **The file you need to change looks machine-written** → edit it anyway →
   check for generation markers first: a `// Code generated ... DO NOT EDIT`
   / `@generated` header, or a path like `dist/`, `build/`, `*_pb.go`,
   `*.gen.ts`, `__generated__/`, `schema.rb`. Edit the SOURCE (proto,
   schema, template, migration) and regenerate with the project's command.
   Same rule for applied DB migrations: never edit an old one; add a new one.
5. **Tests exist but your favorite runner is nicer** → run/write with yours
   → use exactly the runner and assertion style from loop step 5. A test
   that doesn't run under the project's `test` command does not exist in CI.
6. **Lint fails on your code** → add `eslint-disable` / `# noqa` /
   `#[allow]` → the rule encodes a project decision; fix the code to
   satisfy it. A suppression is acceptable only with a one-line comment
   stating why the rule is wrong HERE, and it belongs in your report.
7. **You need a URL, path, timeout, or credential** → hardcode the value
   that works locally → grep for the existing config mechanism (env vars,
   `config/` files, settings module, DI container) and thread the value
   through it. Hardcoded config is the bug that only fires in production.
8. **A decision point you can't resolve (naming, contract shape, edge-case
   semantics)** → leave `// TODO: decide later` and move on → a TODO where
   a decision was required is undone work wearing a comment. Either decide
   and state the rationale in the report, or stop and escalate the specific
   question. TODOs are acceptable only for explicitly-agreed deferrals.
9. **The task keeps touching "just one more file"** → keep going → stop and
   report when you cross any of: >3–4 files unrelated to the core change, a
   public interface/API contract change, a DB migration, a new dependency.
   These are scope decisions the human owns (see decision tree C).
10. **No obvious test/build command** → guess one from the stack's defaults
    (`npm test`, `pytest`, `go test ./...`) → a guessed command can lie in
    both directions (runs nothing and "passes", or fails for setup reasons).
    Re-check scripts/Makefile/CI; if truly absent, report "no test command
    is defined in this project" explicitly — that is a finding, not a gap
    to paper over.
11. **A library would make this easier** → add it → grep the lockfile and
    existing imports first; the capability often already ships with a
    current dependency (or the stdlib). A new dependency needs the sentence
    "existing dep X can't do this because Y" in the report (decision tree A).
12. **Your slice works but tests you never touched now fail** → assume
    flakiness or pre-existing breakage → prove it: run the failing tests on
    the base commit (`git stash` → run → `git stash pop`). Fails there too →
    report as pre-existing. Passes there → you caused a regression; it is
    yours to fix before handoff.
13. **Two lockfiles / package managers present, or your install created a
    new lockfile** → pick whichever you like → the CI config decides which
    manager is real; use it, and never commit a lockfile CI doesn't use.
14. **Docs/tutorial code for the library doesn't match the repo's usage** →
    trust the docs → check the pinned version in the lockfile; you are
    likely reading docs for a different major version. The repo's existing
    call sites are the compatible examples.
15. **You "finished" but only ran the tests you wrote** → hand off → run
    the project's FULL suite command from loop step 3. New-tests-only
    verification misses every regression by construction.

## Discriminating checks (cheap, in rising order of cost)

- **Does it already exist?** — `grep -ri <name-or-behavior> --include=<ext>`
  across `src`/`lib` before writing any new symbol (~15 s).
- **Is this file generated?** — head the file for `generated`/`DO NOT EDIT`;
  check the path against `.gitignore` and codegen configs.
- **Which command is real?** — open the CI workflow; the step list IS the
  project's definition of "passing".
- **Is the breakage mine?** — `git stash` → run the failing check →
  `git stash pop`. Two minutes; settles ownership of every failure.
- **Which error style?** — read how the 2–3 nearest callers handle failures
  from the same layer; copy that shape.
- **Is my assumption about the framework true here?** — find one existing
  usage in the repo and read it, instead of reasoning from documentation.

## Decision trees

### A. New dependency vs existing capability
- Grep lockfile + imports: does an installed dep (or the stdlib) cover the
  need, even partially? → use it; wrap it thinly if the interface is
  awkward.
- Nothing covers it and the need is core to the feature? → propose the new
  dep in the report with: the one-sentence reason existing deps can't do
  it, and why this library over 1–2 alternatives. Do not install until the
  design (architect/human) confirms.
- Nothing covers it but the need is peripheral (one call site, simple
  logic)? → write the ~20 lines yourself in the repo's style; a dependency
  is a permanent tax for temporary convenience.

### B. New file vs existing file
- Find where the most similar existing code lives (`grep` for sibling
  features). Same kind of thing → same directory, same naming pattern.
- The addition is a natural extension of an existing module (same domain
  noun, same layer) → add to the existing file unless it's already an
  outlier in size for this repo.
- Genuinely new domain concept with no sibling → new file, named and placed
  by the repo's convention, exporting/registering the way siblings do
  (route tables, module indexes, DI registries — grep for where siblings
  are wired in, and wire yours the same way).

### C. When to stop and report scope expansion
- The correct implementation requires ANY of: >3–4 files unrelated to the
  core change; changing a public interface, API contract, or shared type;
  a DB schema migration; a new dependency; touching auth/payments/data-
  deletion paths → STOP. Report what you found, the smaller alternative if
  one exists, and the cost of each option. Do not proceed on your own
  judgment.
- The expansion is mechanical fallout of the agreed change (rename ripples,
  import updates, fixture updates) → proceed, but list every touched file
  in the report under "mechanical fallout".

## Verification recipe (before declaring any change done)

1. Run the project's OWN test command — the one found in scripts/Makefile/CI
   during loop step 3, verbatim. Quote the summary line (counts), not just
   "passed". If no test command exists, state that explicitly in the report;
   do not substitute an invented one.
2. Run the project's typecheck and lint commands if they exist (same
   discovery rule). Zero new findings; pre-existing findings proven
   pre-existing via the base-commit check.
3. Run the build/compile command if the project has one — type-correct code
   can still fail to build (codegen drift, asset pipelines).
4. Exercise the vertical slice end-to-end once by the cheapest real means
   the repo offers: the test you wrote, a `curl` against the dev server, a
   CLI invocation. Name the exact command and its output in the report.
5. Re-read your full diff: no debug prints, no suppressed lint rules without
   a stated reason, no edits to generated files, no stray lockfile changes,
   no TODOs standing in for required decisions.
6. Re-read the original request / done-means list; map each criterion to
   evidence (VERIFIED / REASONED / ASSUMED).

## Reviewer checklist (qa-reviewer's hunt list, in priority order)

1. Was the FULL project suite run with the project's own command (output
   quoted)? Any invented command in the report is itself a finding.
2. Regressions: any previously-passing test now failing? (Top finding,
   always.) If the builder claims pre-existing, is the base-commit proof in
   the report?
3. Failure path: for each new behavior, is there a test for bad input /
   missing data / downstream error — in the project's error style? Missing
   → specify the test (name, input, expected) for the builder.
4. Duplication: do the diff's new helpers/types/constants already exist?
   Grep for their names and behavior before accepting them.
5. Pattern drift: does the diff introduce a second style (async handling,
   error shape, logging, naming) beside an established one?
6. Generated files: does the diff touch `dist/`, `*_pb.*`, `*.gen.*`,
   `__generated__/`, applied migrations, or anything with a generated
   header?
7. Suppressions and shortcuts: new lint-disable comments, hardcoded values
   that config should provide, TODOs at decision points?
8. Scope: does the diff exceed the agreed slice (interface changes,
   migrations, new deps) without a stop-and-report having happened?
9. Boundaries: external input validated before use; secrets absent from
   logs, errors, and the diff; dynamic queries/shell calls parameterized.
10. Lockfiles and manifests: only changes the task required, made with the
    project's own package manager.
