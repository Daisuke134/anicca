# AI Entity Article Writer model-agnostic restoration

Status: implementation source of truth.

This specification restores the proven AI Entity Article Writer, keeps the
effective improvements added later, and makes the model process boundary work
with Codex or Claude. The detailed implementation order is in
[model-agnostic-restoration-plan.md](model-agnostic-restoration-plan.md).

## 1. Overview

### Problem

The known-good `592a193` article loop performs the complete foreground pass:
research, native Japanese and English writing, headline image generation,
Mermaid and table authoring, platform adaptation, visual verification,
publication, reality gates, reporting, and self-improvement.

The attempted model port replaces that complete agent with a new Writer Engine
generation architecture before parity is proven. The installed replacement
currently has these measured failures:

- the canonical `ai.anicca.article-daily` job is not loaded
- the replacement daily job is loaded at 06:00 JST
- the replacement resume job runs every 300 seconds
- the active run remains incomplete at six of eight live outputs
- Zenn Japanese and X Article English remain pending
- the note output lacks its required eyecatch and the article package lacks
  required reader-visible diagrams
- X Article English can be abandoned after a ten-minute publication window
- scheduled Writer Engine learning exits without performing learning
- the proven article self-improvement, audit, and whitelist jobs are not loaded
- the active replacement records Blockrun, which is outside this loop

### Required outcome

The production system MUST have:

1. one Mac mini launchd scheduler
2. one daily run ID per JST date
3. one immutable Japanese/English article package
4. one publication ledger and one recovery path
5. two capability-equivalent model runners: Codex and Claude
6. eight reader-visible live outputs
7. durable pending-only recovery
8. daily and weekly evidence-driven self-improvement

Codex and Claude are runners behind one loop. They MUST NOT be independent
daily loops and MUST NOT publish competing copies of the same package.

### Canonical identity

- repository source: `skills/article-writer/`
- canonical skill name: `ai-entity-article-writer`
- user skill alias: `~/.claude/skills/ai-entity-article-writer`
- daily driver: `skills/article-writer/article-daily.sh`
- production host: the always-on Mac mini
- scheduler: launchd

`skills/writer-engine/` is an improvement donor, not the production generation
architecture. Its effective publisher, evidence, recovery, and exact8 behavior
is backported into `skills/article-writer/`.

### External basis

- Apple specifies launchd as the preferred timed-job mechanism and
  `StartCalendarInterval` as its calendar trigger:
  <https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html>
  — “The preferred way to add a timed job is to use `launchd`.”
- OpenAI specifies `codex exec` for unattended scripts:
  <https://developers.openai.com/codex/noninteractive/>
  — “Use `codex exec` to run Codex in scripts and CI”
- Anthropic specifies `claude -p` as non-interactive execution:
  <https://docs.anthropic.com/en/docs/claude-code/cli-reference>
  — “Print response without interactive mode”
- Durable work retains one execution and its state across failure:
  <https://docs.temporal.io/workflow-execution>
  — “A Temporal Workflow Execution is a durable, reliable, and scalable
  function execution.”
- Production activation follows a bounded canary before full rollout:
  <https://sre.google/workbook/canarying-releases/>
  — “We define canarying as a partial and time-limited deployment of a change
  in a service and its evaluation.”

## 2. Acceptance criteria

### AC-01: One autonomous daily trigger

- `ai.anicca.article-daily` MUST be the only launchd job allowed to create a new
  article run.
- It MUST start at 06:00 JST through `StartCalendarInterval`.
- It MUST create at most one `daily-YYYY-MM-DD` run per JST date.
- It MUST run without a human, an interactive Codex session, or an interactive
  Claude session.
- The replacement `ai.anicca.writer-daily` and
  `ai.anicca.writer-resume` jobs MUST be unloaded before activation.

### AC-02: Model-agnostic runner

The runner MUST accept:

```text
ARTICLE_PROVIDER=auto|codex|claude
```

- `auto` MUST prefer healthy Codex, then healthy Claude.
- `codex` MUST require Codex and fail closed when it is unavailable.
- `claude` MUST require Claude and fail closed when it is unavailable.
- Authentication status alone MUST NOT count as available quota.
- Availability MUST be based on a bounded real call or the classified result of
  the required call.
- The runner MUST expose the same three modes for both providers:
  `agent`, `judge`, and `vision`.
- A provider MUST be ineligible for a mode when it lacks the required tool or
  image capability.

Codex production settings:

```text
model = gpt-5.6-luna
reasoning effort = xhigh
```

Claude production settings:

```text
model = sonnet
effort = provider default
```

Blockrun and any third provider MUST NOT be present.

### AC-03: Exact8 publication contract

One daily package MUST produce exactly these eight live outputs:

| Pair | Language | Form | Timing |
|---|---|---|---|
| note | Japanese | article | immediate group |
| Zenn | Japanese | article | immediate group |
| Dev.to | English | article | immediate group |
| Substack | Japanese | article | immediate group |
| Substack | English | article | immediate group |
| X Article | Japanese | article | immediate group |
| X Article | English | article | Japanese X Article + at least 6 hours |
| X Post | Japanese | short post | once per JST date, at or after 12:00 |

“Immediate group” means publish sequentially as soon as that platform's
artifact and gates pass. It does not impose an artificial delay between note,
Zenn, Dev.to, Substack, and X Article Japanese.

The X Article language spacing MUST obey:

```text
x_article_en.not_before = x_article_ja.published_at + 6 hours
x_article_en.deadline = none
```

The resume job MUST check pending work every 300 seconds. Under normal
availability, X Article English therefore publishes between six hours and six
hours five minutes after the Japanese version. Missing the exact six-hour tick
MUST NOT abandon the English article.

The next day's X Article Japanese remains owned by the next daily run. It MUST
NOT bypass same-day idempotency or reuse the prior run ID.

### AC-04: Reader-visible media

Both canonical language drafts MUST contain:

- one selected headline image
- at least one reader-visible explanatory diagram
- Mermaid source for diagrams where Mermaid is the authored representation
- a table when the source material contains a relationship best explained as a
  comparison

Each publisher MUST adapt the same canonical asset rather than silently remove
it:

- note MUST have a confirmed eyecatch and reader-visible body diagram
- Zenn MUST render supported Mermaid or its approved image equivalent
- Dev.to, Substack, and X Article MUST show the adapted diagram/image
- every public asset MUST pass URL and rendered-page readback

A live URL without the required visible media MUST NOT count toward exact8.

### AC-05: Durable publication and failover

Before the first live side effect, the loop MUST persist:

- run ID and JST date
- topic ID and research provenance
- Japanese and English artifact hashes
- exact8 publication intents
- expected account and destination identities

Before any live side effect, a provider quota failure MAY switch to the other
healthy provider and continue the same run.

After any live side effect:

- the complete daily prompt MUST NOT be replayed
- already-live pairs MUST NOT be republished
- the same run ID, artifacts, hashes, intents, and remote identities MUST be
  loaded
- only pending pairs MUST be attempted
- uncertain remote outcomes MUST be reconciled before another create action

If both providers are unavailable, the run MUST remain pending. It MUST resume
after a provider becomes healthy without creating a second run.

### AC-06: Platform isolation and evidence

- One platform failure MUST NOT cancel attempts for unrelated platforms.
- Completion MUST require the exact set of eight pairs, not only a count of
  eight.
- Every pair MUST have a stable public ID, canonical live URL, publication
  timestamp, artifact hash, and reality-gate result.
- note, X, Dev.to, Substack, and Zenn account identities MUST match the
  configured production identities.
- Telegram MUST send a durable completion receipt only after exact8 passes.
- A pending or failed run MUST send an honest pending/failure report and MUST
  NOT use a success message.

### AC-07: Self-improvement loop

The restored system MUST run these autonomous jobs:

| Schedule | Job | Required result |
|---|---|---|
| every day 06:00 | article daily | read last verified lesson and produce one exact8 package |
| every day 22:30 | article self-improve | measure, learn, propose one bounded change |
| Sunday 03:00 | whitelist learning | update language whitelist through syntax-checked evidence |
| Sunday 22:00 | seven-day audit | verify live URLs, language gates, SEO, and learning evidence |

The daily self-improvement cycle MUST:

1. collect immutable per-article engagement, SEO, quality, and sales evidence
2. prefer real revenue as the decision metric when available
3. mark views/likes/rubric scores as proxy metrics when revenue is unavailable
4. create exactly one concrete hypothesis and one next change
5. record the baseline, cut date, target axis, application evidence, and
   evaluation date
6. apply the change to the next eligible article
7. evaluate it after seven days using disjoint pre/post evidence
8. keep it only when the metric is not worse, application is proven, and the
   change generalizes across the required language lanes
9. revert the exact prior text when the change fails

Self-improvement MAY change:

- topic prioritization
- headline and lead guidance
- article structure and platform adaptation guidance
- quality rubrics and non-safety writing guidance through one reversible
  experiment

Self-improvement MUST NOT change:

- safety or identity gates
- production account identities
- exact8 membership
- the 06:00, 12:00, six-hour, or retry schedules
- provider credentials or provider priority
- publication idempotency and recovery rules
- its own keep/revert acceptance criteria

A self-improvement provider failure MUST preserve the last known-good playbook
and MUST NOT block the next day's article.

### AC-08: Source and deployment integrity

- One tracked repository tree MUST be the source of truth.
- The installed production tree MUST record the deployed git commit.
- launchd `ProgramArguments` MUST point to the installed copy of the same
  tracked driver.
- The skill alias MUST resolve to the installed canonical article-writer tree.
- Production state, credentials, logs, and browser profiles MUST remain outside
  git.

### AC-09: Production activation

The restored scheduler MUST remain disabled until one real armed canary proves:

- all exact8 public URLs
- required headline and body media on every supported destination
- Japanese and English content readback
- X Article English at least six hours after Japanese
- one and only one X Post for the JST date
- complete ledger and remote identity evidence
- Telegram delivery
- no duplicate publication

The current incomplete run MUST be repaired in place before or as the bounded
canary. Already-live pairs MUST not be recreated.

## 3. As-Is / To-Be

| Concern | As-Is | To-Be |
|---|---|---|
| canonical loop | replacement Writer Engine | restored AI Entity Article Writer |
| scheduler | replacement daily + resume jobs | one article daily job + bounded recovery jobs |
| model | replacement runtime with Blockrun residue | Codex/Claude runner shim only |
| generation | JSON/no-tools replacement path | proven foreground tool-using agent |
| daily outputs | six of eight can remain pending | exact8 reader-visible live outputs |
| X language spacing | six-hour start plus ten-minute deadline | minimum six hours, no deadline |
| X Post | date slot in replacement state | one JST-date slot at or after 12:00 |
| images | URL can pass without visible media | eyecatch/headline/body asset readback required |
| recovery | repeated replacement resume | same-run pending-pair recovery |
| self-improvement | installed placeholder exits | daily evidence loop + weekly audit |
| skill identity | alias absent | `ai-entity-article-writer` alias restored |
| completion | internal state can appear green | public exact identity/content/media proof |

### Retained known-good foundation

Restore the foreground workflow and supporting files from `592a193`.

### Retained improvements

Retain the behavior introduced by the following history:

- `a8fa2b5`: streamed foreground progress
- `4bbcd7c`: preflight before side effects
- `f5567da`: no blind complete replay
- `5f31ce3`: crash-safe publication resume
- `41b32f4`: complete publication intents
- `30942bb`: resume bound to the same run
- `93346b1`: same-day duplicate prevention
- `33b4064`: guarded note 404 recovery

Also backport the effective Writer Engine destination behavior:

- exact account and remote identity journaling
- rich article and asset upload/readback
- X Article browser identity and uncertain-outcome recovery
- X Post identity, readback, and emoji correctness
- supported Substack endpoint/schema
- authenticated Dev.to recovery/readback
- canonical Zenn ownership/frontmatter/redeploy/deferred retry
- durable Telegram retry
- immutable research provenance and private-residue checks
- exact8 output membership

### Discarded behavior

Do not retain:

- Blockrun
- a third provider
- the JSON-only replacement article generator
- a no-tools judge profile as the article producer
- a standalone visual plan as a substitute for generated media
- a second daily scheduler
- a ten-minute X Article English deadline
- completion based only on process exit, local files, counts, or URLs

## 4. Test matrix

No replacement test framework is created. Existing focused checks and one real
armed production canary provide the evidence.

| # | To-Be | Verification name | Evidence |
|---|---|---|---|
| 1 | one 06:00 scheduler | `launchd-single-daily` | `plutil`, `launchctl print`, no competing labels |
| 2 | one run per JST date | `daily-idempotency` | two triggers, one run ID, no extra intents |
| 3 | Codex agent mode | `codex-agent-canary` | bounded real tool/file action succeeds |
| 4 | Claude agent mode | `claude-agent-canary` | run only after quota health succeeds |
| 5 | provider failover | `same-run-provider-switch` | same run/artifact hashes, no replayed live pair |
| 6 | exact8 membership | `public-exact8` | exact public pair set and eight reality PASS rows |
| 7 | required media | `public-media-readback` | eyecatch/headline/body diagram visible |
| 8 | X six-hour rule | `x-language-spacing` | EN timestamp is at least JA + six hours |
| 9 | missed tick recovery | `x-no-deadline-recovery` | first later 300-second tick publishes EN |
| 10 | one X Post | `x-post-jst-slot` | exactly one status ID for the JST date |
| 11 | partial publication recovery | `pending-pairs-only` | existing live IDs unchanged |
| 12 | uncertain outcome recovery | `remote-reconciliation` | readback before create, no duplicate |
| 13 | Zenn deferred recovery | `zenn-deferred-live` | same slug becomes live and passes readback |
| 14 | daily learning | `self-improve-proposal` | one evidence-bound experiment at 22:30 |
| 15 | application | `next-article-applies-lesson` | application ledger binds experiment and article |
| 16 | keep/revert | `seven-day-promotion` | disjoint evidence and reversible result |
| 17 | weekly controls | `weekly-audit-and-whitelist` | Sunday receipts and syntax-clean whitelist |
| 18 | deployment integrity | `deployed-commit-binding` | repo, installed commit, symlink, launchd agree; learning push atomically advances the marker |
| 19 | completion reporting | `telegram-exact8-receipt` | message ID and eight verified URLs |

### E2E judgment

| Item | Value |
|---|---|
| UI change | none |
| Conclusion | Maestro not required; this is a Mac launchd/browser-publication workflow, so a real public canary and public-page readback are required |

## 5. Boundaries

### In scope

- surgical restoration of the known-good article workflow
- Codex/Claude process-boundary compatibility
- exact8 publication
- headline image, diagram, Mermaid, and table preservation
- same-run recovery and deduplication
- daily and weekly self-improvement
- Mac mini launchd installation and verification

### Out of scope

- returning to known defects fixed by retained commits
- a new Writer Engine generation design
- a provider beyond Codex and Claude
- Blockrun
- VPS execution
- database redesign or migration unrelated to preserving the current run
- a second scheduler
- a new visual generator
- a replacement test framework
- redesigning the article voice before production parity

### User GUI tasks

None. The agent performs repository changes, Mac mini launchd changes, browser
publication, public readback, and production verification.

## 6. Execution steps

1. Freeze current runtime and remote publication evidence.
2. Unload replacement Writer Engine launchd jobs.
3. Restore the known-good article-writer foreground tree without overwriting
   runtime state.
4. Reapply the retained pre-consolidation safety and recovery changes.
5. Add one Codex/Claude shim and replace the 18 logical direct Claude calls.
6. Backport destination, evidence, exact8, and X Post improvements.
7. replace the X Article English deadline with a durable six-hour not-before
   rule.
8. Restore media generation and public asset readback.
9. Restore and model-port daily/weekly self-improvement.
10. Restore the canonical skill alias and launchd files without activating the
    daily scheduler.
11. Pin `ARTICLE_PROVIDER=codex` and repair the current incomplete run in place.
12. Run one real armed exact8 canary and collect all acceptance evidence.
13. Activate the 06:00 daily scheduler only after the canary passes.
14. Switch to `ARTICLE_PROVIDER=auto` only after Claude passes its bounded
    capability checks.
15. Record and push the exact deployed commit.

Detailed file operations, commands, checkpoints, and rollback boundaries are in
[model-agnostic-restoration-plan.md](model-agnostic-restoration-plan.md).
