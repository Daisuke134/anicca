# Life Manager Portable Runtime + Finance + Self-Improving Marketing Platform Design

**Status:** Canonical program SSOT  
**Scope owner:** Life Manager  
**Canonical repository:** `https://github.com/Daisuke134/life-manager`  
**Current release:** OpenClaw-to-Life-Manager Portable Runtime Migration
**First production products:** Anicca iOS and Honne AI  
**Primary outcome:** every retained loop runs from Life Manager with zero
OpenClaw dependency, first locally and then from the same runtime in the cloud.

**Current implementation cursor:** the portable local foundation, bounded
financial-report job adapter, shared loop-adapter registry, and the first Life
Manager daily generation→publication chain are proven. A Life Manager-owned
local scheduler and worker sent real Telegram `message_id=432`, persisted the
immutable snapshot/effect receipt, and survived a worker restart without
resend. The daily marketing path owns immutable generation inputs, a verified
render receipt, and deterministic independent Instagram/TikTok jobs. The chain
defaults off while the legacy LaunchAgent remains active. The Life Manager-owned
Instagram profile is now recovered with exact-account, feed, launcher, and
read-only Reel-list proof; the legacy source profile remains untouched. New
publication receipts preserve provider metric join keys, and a generic
per-publication 2h/24h/72h/7d observation adapter plus deterministic scheduler
fanout is proven with missing metrics retained as unavailable. The observation
schedule defaults off while the legacy owner remains active. The first generic
ReelClaw generation slice now imports Honne JA's 24 hooks and four MP4s into
Life Manager ownership, executes a durable tenant-scoped no-effect job, selects
`HJA-007` from imported plus receipt history, and emits immutable video/copy
lineage without reading a legacy path at runtime. The working Honne launchd
owner is unchanged. Next: connect generic publication and scheduling in
shadow mode, migrate the remaining Larry/ReelClaw products, add product
attribution, and do not cut over ownership before the seven-expected-run gate.

## 1. Executive decision

Life Manager becomes the single control plane for personal health and autonomous
income loops. The Portable Runtime Migration ships first. Until its local and
cloud gates pass, new finance, marketing-learning, health, and app-generation
features are frozen except where they are required to preserve an existing loop
during migration.

The current release has exactly two sequential outcomes:

```text
Milestone A — local:
  all retained loops run from Life Manager-owned code/data/secrets
  with OpenClaw stopped and ~/.openclaw inaccessible

Milestone B — cloud:
  the same release runs multi-tenant on Railway-managed infrastructure
  with no Mac Mini dependency and monthly subscription entitlement
```

Repository identity is not inferred from a local directory name:

| Role | GitHub identity | Local state | Rule |
|---|---|---|---|
| **Only active SSOT** | [`Daisuke134/life-manager`](https://github.com/Daisuke134/life-manager), repository ID `1248111245` | canonical checkout is currently `/Users/anicca/Projects/life-manager-main` | all new code, specs, plans, issues, CI, deployment config, schedules, and release evidence live here |
| Legacy historical source | [`Daisuke134/life-manager-v0`](https://github.com/Daisuke134/life-manager-v0), repository ID `1273052304` | archived read-only; any old local clone is non-runtime | no new work, runtime, scheduler, CI, or deployment may target it; 35/35 disposition, issue transfer, redirect, archive, and runtime-reference-zero gate are complete |
| Temporary worktrees | branches whose Git common directory is the canonical repository | multiple paths may exist during bounded work | a worktree is not another repository or SSOT; merge or retire it when its task closes |

The selected architecture is portable local/cloud with cloud as the default
hosted mode:

| Plane | Runtime | Responsibility |
|---|---|---|
| Portable application | The same Life Manager services and OCI images | accounts, products, schedules, jobs, ledgers, attribution, experiments, reports, panel, Telegram |
| Local deployment | Docker Compose plus `life-manager` CLI | private/self-hosted operation on Mac/Linux without any OpenClaw process or folder |
| Cloud deployment | Railway initially; provider-neutral worker pools | always-on multi-tenant operation, horizontal scaling, failover, phone-first use |
| Data plane | PostgreSQL in both modes | immutable events, financial snapshots, content lineage, metrics, experiments, job state |
| Object plane | local object adapter or S3-compatible storage | media, evidence, exports, signed migration archives |
| Secrets | OS keychain/encrypted local vault or tenant-scoped cloud vault | credentials and browser sessions; never stored in prompts, job payloads, logs, or Git |

### 1.1 Deployment and commercial boundary

Local and cloud are two deployment profiles of one codebase, one schema, one
job protocol, and one release artifact. They are not separate products and
must not fork business logic.

| Mode | Operator | Availability | Current commercial rule |
|---|---|---|---|
| Local/self-hosted | user operates Life Manager on Mac or Linux | depends on the user's machine and internet | no managed-cloud monthly subscription is required; the user supplies hardware and connector/provider costs |
| Cloud/hosted | Life Manager operates the same versioned services on Railway and provider-neutral workers | always-on within the hosted service SLO; no user computer required | monthly subscription is required; entitlement controls schedules and worker usage, while export and cancellation remain available |

Annual, lifetime, and usage-only plans are outside the current release. No
numeric price is authorized until measured per-tenant infrastructure and
connector costs establish a sustainable floor.

The migration order is mandatory:

```text
archived historical `life-manager-v0` + one writable canonical repository
  → self-contained canonical repository (`Daisuke134/life-manager`)
  → OpenClaw-dependent local
  → Life Manager-owned local
  → portable local/cloud parity
  → cloud-default production
```

`life-manager-v0`, OpenClaw, Profitable Claude, and repository-specific launchd jobs are migration
sources only. Every retained script, asset, prompt, schedule, state file, and
credential reference moves behind Life Manager-owned contracts and paths
before cloud migration begins. Legacy repositories remain intact until parity
and rollback evidence pass.

## 2. Goal and non-goals

### Goal

`done = true` only when all of the following are true:

1. Every OpenClaw cron entry and relevant launchd job is classified as
   `migrate`, `replace`, or `retire`; no enabled or loaded job is unowned.
2. Stopping `ai.openclaw.gateway` and denying access to `~/.openclaw` does not
   interrupt any retained Life Manager loop.
3. Runtime code, config, schedules, secrets, assets, and state contain no read,
   execute, import, or fallback dependency on `~/.openclaw`,
   `/Users/anicca/profitable-claude`, or `/Users/anicca/anicca`.
4. `life-manager runtime up --mode local` runs all retained loops locally from
   Life Manager-owned code and data.
5. The same versioned services run with `--mode cloud`; moving a tenant between
   modes changes deployment adapters, not loop behavior or business logic.
6. The Life Manager panel and Telegram show the same reconciled financial
   snapshot, including freshness and unavailable-source states.
7. Every published mobile creative has lineage:
   `product → campaign → experiment → format → hook → artifact → publication
   → platform metrics → install → trial → paid revenue`.
8. A learning promotion changes one bounded rule, passes a canary, is consumed
   by the next generation run, and can be reverted from a durable receipt.
9. Anicca iOS and Honne AI each have independent product packs, goals,
   attribution, metrics, and learned weights.
10. A new user can connect a product and run the same engine without Anicca
   names, paths, accounts, or credentials.
11. In cloud mode, powering off the Mac Mini does not interrupt any production
   loop; Codex on the Mac is an optional command client, not an executor.
12. Cloud worker capacity scales horizontally with tenant demand and enforces
   per-tenant quotas, rate limits, concurrency limits, and fair scheduling.
13. GitHub, CI, Railway, local launchd during migration, and every canonical
    spec resolve to repository ID `1248111245`; repository ID `1273052304` is
    read-only archived after a signed import/equivalence manifest passes.

### Non-goals for the first release

| Deferred item | Reason |
|---|---|
| New financial connectors and the full Financial Health dashboard | Preserve and migrate the existing report first; expand it only after local and cloud runtime parity |
| New marketing formats or autonomous self-improvement | Migrate current posting behavior first; activate learning only after publication and metric receipts survive local/cloud parity |
| Autonomous mobile-app creation and App Store submission | Prove growth of existing apps before generalizing the development loop |
| Physical- and mental-health expansion | Preserve currently retained health behavior; new automation follows runtime migration |
| Deleting OpenClaw or legacy repositories | Do not delete history. `life-manager-v0` is archived after its dedicated import/equivalence gate; other runtime sources are disabled and archived only after shadow, canary, restart, and dependency tests |
| Trading with user funds | Financial health is read-only reporting; execution requires a separate risk and authorization spec |
| Accepting raw Apple IDs or passwords | App Store Connect API keys and delegated authorization are safer and automation-compatible |
| Claiming guaranteed `$10k MRR` | `$10k MRR` is a measurable target with explicit assumptions, not a promise |

## 3. Evidence: current state

### 3.1 Measured runtime state

| System | Measured state | Consequence |
|---|---|---|
| Canonical GitHub repository | `Daisuke134/life-manager`, repository ID `1248111245`, public/unarchived, default branch `main`; 3,241 tracked files in the measured checkout | This is the only write/deploy/spec target |
| Legacy GitHub repository | `Daisuke134/life-manager-v0`, repository ID `1273052304`, public/archived, default branch `main`; 35 tracked files, open issue/PR・workflow/webhook/deployment 0 | Retirement complete: 35/35 disposition, missing required behavior 0, canonical redirect exactly1, active runtime reference 0 |
| Local repository naming | canonical repo is cloned as `life-manager-main`; the directory named `life-manager` actually points to `life-manager-v0` | Directory names are unsafe identifiers; use remote URL plus repository ID until the legacy clone is quarantined and the canonical checkout is normalized |
| Live Life Manager launchd paths | measured Life Manager daily, dev, financial, payout, self-build, TaskMarket, uGig, and x402 jobs point to `/Users/anicca/Projects/life-manager-main`; none point to `life-manager-v0` | Runtime already selects the canonical repository, but remains local and path-bound |
| Local OpenClaw gateway | Running as `ai.openclaw.gateway` | OpenClaw is still running |
| OpenClaw scheduler | Read-only capture contains 222 stored jobs; 92 are marked enabled | Stored/enabled is not proof of current execution; each row remains unclassified until Task 2 assigns a verified disposition |
| macOS launchd | Read-only capture contains 176 user LaunchAgent plist files and one additional relevant loaded-only label; 161 plist-backed labels are currently loaded. The loaded CFO plist cannot be parsed by `plutil`, and `com.anicca.daemon` has no user LaunchAgent plist; both are preserved as explicit parse errors | launchd is the actual scheduler for many observed loops; malformed or loaded-only rows must not be silently dropped or changed |
| Unified runtime inventory | `docs/migrations/openclaw/runtime-inventory.json` contains all 399 captured OpenClaw and relevant LaunchAgent rows; 269 are enabled or loaded; commands and private identifiers are redacted | All 399 rows now carry one measured disposition (214 migrate, 40 replace, 132 retire, 13 retain-external; zero `unclassified`) with owners and rollback actions per `docs/migrations/openclaw/classification-summary.md`; no scheduler change is authorized by the inventory |
| Profitable Claude marketing engine | Registry, schemas, bounded learning, canary keep/revert, observation terminalizer, and dashboard exist | Reuse these contracts |
| Marketing runtime store | About 20 KB; dashboard and logs only; no run, publication, metric, experiment, or observation ledgers | The production feedback loop is not closed |
| Life Manager Railway | `/health` returns 200 from `life-call-production.up.railway.app` | A functioning cloud control plane already exists |
| Life Manager panel | Timeline, connection, score, gate, API cost, and limited financial-ledger projections exist | Extend; do not build a second dashboard |
| Financial report loop | the legacy launchd loop remains active; the Life Manager local scheduler/job/worker path separately sent real Telegram `message_id=432` with immutable snapshot/effect receipt and restart count `1 → 1` | Report execution is OpenClaw-independent and shadow-ready; scheduler ownership is intentionally not cut over until seven expected runs |
| Financial report scope | x402/TaskMarket/USDC earnings, fees, losses, API costs, payout reserve | Bank, App Store, Stripe, broader crypto, and business P&L are absent |
| Moneytree connector | One connected Japanese bank account is readable | Bank balance can seed the personal balance sheet; account identifiers must stay private |
| Historical Anicca metrics | 299 seven-day downloads on 2026-05-15; subsequent snapshot showed zero due to ASC collection failure; historical trial start rate about 3.5–3.8% | Data quality must be first-class; zero and unavailable cannot be conflated |

RevenueCat administration and credential operations belong to the separate
Anicca iOS/API product boundary. They are not a Life Manager connector, metric
source, implementation cursor, or completion gate. Hosted Life Manager
entitlement remains Stripe-based.

### 3.2 Marketing jobs actually loaded in launchd

The table lists the revenue-relevant daily families, not every unrelated
machine-maintenance job.

| Family | Current cadence | Current boundary | Latest observed condition |
|---|---|---|---|
| Larry Anicca slideshows | Multiple EN/JA accounts, 1–4 posts per account/day | Profitable Claude wrapper; several scripts return to `~/.openclaw` | Active; some library-post jobs exit 3 |
| ReelClaw Anicca videos | Card/widget EN/JA, 1–2 posts per variant/day | Mostly `~/.openclaw/skills/_dispatcher` and ReelClaw scripts | Active; several jobs exit 1 |
| Honne videos | EN at 07:00/11:00/20:30; JA at 08:30/12:30/21:30 | `~/.openclaw` ReelClaw scripts | Active with recent logs. The JA shadow counterpart was enabled in the local compose stack on 2026-07-30 13:33 JST (worker capabilities generate-only, never `marketing.video.publish`, via a gitignored `deploy/local/compose.override.yaml` outside repo defaults), so seven-cycle shadow evidence now accrues automatically at the 12:30/21:30 JST slots while this legacy launchd job remains the production owner |
| Larry strategy learning | 05:10 daily | Reads OpenClaw content metrics and library state | Latest exit 2 |
| Capafy core | 08:10 daily | `/Users/anicca/anicca` | Active |
| Capafy goal/marketing | 09:00, 11:20, 16:00 | `/Users/anicca/anicca` | Active; latest marketing rows show zero engagement |
| Clipping | Every 86,400 seconds | `/Users/anicca/anicca` | Active; latest recorded asset was below quality floor |
| Writer/article | craft train and article resume/daily/learning jobs are loaded; standalone writer daily/learn plists exist but are not currently loaded | Profitable Claude plus local writer CLI | Mixed; loaded jobs include successes and failures |
| Shared marketing metrics | Every 15 minutes | Profitable Claude engine | Runs successfully but has no production ledgers to observe |
| Shared marketing dashboard | Every 15 minutes | Profitable Claude engine | Runs successfully but projects an empty runtime |
| Life Manager financial report | Every five minutes; send gates at 20:00 daily and Sunday 20:05 weekly | Legacy launchd still reads its historical environment; replacement uses Life Manager PostgreSQL jobs and tenant secret refs | Replacement real-send proof complete (`message_id=432`); legacy remains active only for shadow/cutover safety |

Immediate Life Manager marketing routing measured during this design update:

| Route | Scheduler identity | TikTok integration before | TikTok integration after | State |
|---|---|---|---|---|
| Current Life Manager IG + TikTok daily pass | launchd `ai.anicca.life-manager-daily`, 10:15 JST | `cmp9txjdp01c8oh0yb6dhlarr` (`@anicca_buddha`) | `cmpc6cr6g00d8lg0yfythzz9f` (`@anicca.comedy`) | Route change is now proven by B01 TikTok `7667934981481875473`; the old launchd remains loaded for the seven-cycle shadow gate |
| Retired OpenClaw wrappers | `6ad526a5-7f2a-4738-930b-89c158acf10d` and `a7e6095c-1472-4408-ae04-e20598b66cbf` | `cmpc6cr6g00d8lg0yfythzz9f` | n/a | Both are classified `disabled` |
| Retired recording-based successor | launchd `ai.anicca.lm-video-post` | `cmpc6cr6g00d8lg0yfythzz9f` | n/a | Service is not loaded, active plist is absent, and control-plane desired state is `disabled` |

The first `ai.anicca.life-manager-daily` migration slice is operational:

- Life Manager imports the exact B01 video, caption, standing approval, and
  Instagram profile into its own data root. Runtime jobs contain only
  content-addressed `object://sha256/...`, tenant profile, integration, and
  secret references.
- Instagram and TikTok are separate durable publication jobs. One broken
  account cannot block the other platform, and a partial effect cannot be
  misreported as a two-platform success.
- TikTok B01 is publicly reachable at
  `https://www.tiktok.com/@anicca.comedy/video/7667934981481875473`.
  The PostgreSQL job completed on attempt 1 with that raw URL and the exact
  video/caption hashes. Re-enqueue after worker replacement returned
  `created=false`; the provider still contained exactly one matching post.
- Postiz returned a profile URL plus a numeric `releaseId`. The adapter now
  derives and verifies the individual video URL, and reconciles the exact
  recent caption+integration before any upload. A provider success can no
  longer become either a false failure or a duplicate retry.
- The configured Instagram session returns `ChallengeRequired` and remains
  `poisoned_manual_backup`. No IG write was attempted and no unrelated account
  was substituted. Replacing/warming that tenant profile remains required
  before the Instagram shadow counter can start.
- This slice proves portable distribution and restart safety, not creative
  quality or self-improvement. B01 came from the currently retained renderer.

The second `ai.anicca.life-manager-daily` migration slice makes generation
portable without enabling a competing scheduler:

- The creative bank, call audio, stock footage, proof image, and Whisper
  transcript were copied once into Life Manager's private content-addressed
  object store. Generation jobs now carry only those five immutable refs plus
  tenant and date; they read no OpenClaw or other repository path.
- The local Life Manager worker completed three real render jobs on attempt 1.
  A03 produced a 34.666667-second MP4 with SHA-256
  `35e4084f1aa1349029348c908a5d1f07a0db2c9ded1fe5728fcfd2d69fba0cda`;
  state, lock, and render files are mode `0600`, and the MP4 was imported back
  into the immutable object store.
- Real frame comparison exposed why the old rotation did not create visible
  variation: A01 and A02 had different ledger IDs but byte-identical MP4s and
  no rendered text because the runtime image had no fonts. The image now
  packages fontconfig plus Noto/CJK and the ASS contract names that font.
  A03 has a different MP4 hash, and its decoded frame visibly contains both
  `BEFORE LIFE MANAGER • A03` and the Japanese hook.
- Life Manager now has the 10:15 JST generation scheduler contract, but
  `LM_MARKETING_GENERATION_ENABLED` defaults to `false`. It remains disabled
  while the legacy launchd owner is loaded, so this proof cannot create a
  duplicate daily publication.
- This closes portable asset/state/render ownership for this one loop.
  Publication chaining, metric attribution, winner/challenger learning,
  next-run consumption, Telegram marketing reporting, and seven-cycle shadow
  evidence remain open. Autonomous learning still remains frozen until the
  runtime migration gates permit Orders 32–35.

The third slice closes the durable generation→publication handoff without
creating a competing external effect:

- The scheduler scans only one explicit tenant and receipts created on or
  after an explicit cutoff. It accepts only completed, verified
  `marketing_daily_generation` receipts and fans each receipt out into
  independent Instagram and TikTok publication jobs.
- An isolated PostgreSQL proof completed generation attempt 1, found exactly
  one immutable receipt, and created exactly two queued publication jobs:
  Instagram 1 and TikTok 1. Replaying the same scan returned
  `created=false,false`; the database still contained three total jobs
  (generation 1 plus publication 2) and one generation receipt.
- The proof database was dropped after verification. The live local database
  contains zero A03 publication jobs, so this slice made no provider call and
  created no duplicate post.
- `LM_MARKETING_PUBLICATION_CHAIN_ENABLED` defaults to `false`, historical
  backfill has no implicit default, and the legacy
  `ai.anicca.life-manager-daily` LaunchAgent remains loaded
  (`runs=1`, `last exit code=1`). This is a handoff/idempotency proof, not a
  cutover or a claim that Instagram is repaired.

The fourth slice repairs the Life Manager-owned Instagram profile without
posting or modifying the legacy source:

- Browser authorization reached Instagram home after dismissing the provider's
  automated-behavior warning, and the authenticated profile link was exactly
  `/anicca.affirms2/`. No different logged-in browser account was accepted as
  evidence.
- The Life Manager-owned saved session then passed a read-only feed probe,
  launcher probe, and `account_info` identity check for `anicca.affirms2`.
  Recovery atomically changed only that tenant profile row from
  `poisoned_manual_backup` to `ready`, removed the poison fields, preserved file
  mode `0600`, and recorded `recovered_at`.
- A subsequent read-only verification returned `ok=true`, 12 Reels, including
  `/anicca.affirms2/reel/DbPPpXCMjrf/` and
  `/anicca.affirms2/reel/DbKkdfjsaTZ/`. This proves session and account parity;
  it does not claim a new publication.
- A mismatched authenticated username now fails closed: it cannot refresh the
  saved settings or recover the profile. A `ChallengeRequired` remains a
  quarantine event; the private API never retries a password login.
- The legacy `~/.cloak` account row remains
  `poisoned_manual_backup`, the publication chain remains disabled, and
  `ai.anicca.life-manager-daily` remains loaded. No external post or scheduler
  cutover occurred in this slice.

The fifth slice establishes truthful publication measurement without activating
a competing scheduler or claiming unavailable data as zero:

- Every new distribution result carries the provider's post ID and route into
  the immutable publication receipt. Historical receipts remain verifiable but
  cannot be observed unless those join keys already exist; immutable history is
  never rewritten.
- Each publication is observed independently. Deterministic, reference-only
  jobs are created only when its 2h, 24h, 72h, or 7d window is due. Repeated
  scheduler scans rely on the durable job ID for idempotency and cannot create
  duplicate observations.
- An isolated PostgreSQL proof scanned one completed publication receipt,
  created four due observation jobs on the first pass and zero on the second
  (`true,true,true,true` then `false,false,false,false`). A real worker claim
  completed all four controlled-empty observations as `insufficient` with
  `views=null` and `reward.effect=no_change`; the proof database was then
  removed.
- The observation receipt preserves product, creative, platform, clickable
  public URL, provider ID/route, video/caption hashes, exact window timestamps,
  platform metrics, product metrics, and reward eligibility. A measured zero is
  valid; a missing, delayed, unsupported, or unattributed metric remains
  `value=null` with a controlled reason.
- Postiz's per-post analytics route is wired for views, likes, comments, and
  shares. The current product-metric provider truthfully reports
  `attribution_not_configured` until App Store Connect, RevenueCat/product
  analytics, and proceeds sources are added.
- A read-only check of the real B01 TikTok post could not obtain metrics:
  TikTok blocked the direct downloader from the current IP, and Postiz returned
  an empty analytics array. Therefore B01's current measured state is
  unavailable, not zero, and it causes no learning change.
- `LM_MARKETING_OBSERVATION_ENABLED` defaults to `false` and requires an
  explicit tenant, product, cutoff, and worker capability. The existing
  LaunchAgent is unchanged; no post, message, credential mutation, or scheduler
  cutover occurred in this slice.

The sixth slice begins the shared Larry/ReelClaw producer migration with the
measured working Honne JA path and no external effect:

- The one-time importer copied 24 Honne JA hooks and four verified MP4 files
  into the Life Manager data root and immutable object store. Its runtime
  manifest contains only tenant/product/format/locale IDs and
  `object://sha256/...` refs; generation never reads `~/.openclaw` or
  Profitable Claude.
- The generic `marketing.video.generate` adapter is product-, format-, locale-,
  and tenant-scoped. It chooses the least-recent active hook from the imported
  prior-use state plus durable Life Manager receipts and rotates media
  deterministically by schedule slot.
- An isolated PostgreSQL worker proof enqueued one Honne JA job, completed one
  immutable `marketing_video_artifact` receipt, selected `HJA-007`, and emitted
  content-addressed video and copy refs. Re-enqueue returned `created=false`;
  the database remained at one job and one receipt.
- This adapter is a no-effect producer. It did not call Postiz, Instagram,
  TikTok, or YouTube. The existing `ai.anicca.reelclaw-honne-ja` LaunchAgent
  remains loaded at 12:30 and 21:30. Its current launchctl process counters
  were reset by a later service reload (`runs=0`, never exited); the schedule
  and legacy owner remain intact and were not cut over by this slice.
- Measured Larry and Anicca ReelClaw paths are not silently promoted: their
  current logs include missing media/hook/API inputs and non-zero exits. Each
  gets its own repair, import, shadow, and seven-expected-run proof after the
  working Honne slice.

The seventh slice wires Honne JA generic video scheduling into the Life
Manager scheduler in shadow mode with no external effect:

- `apps/life-manager/lib/honne-ja-shadow-schedule.js` encodes exactly the
  legacy `ai.anicca.reelclaw-honne-ja` cadence — `StartCalendarInterval` 12:30
  and 21:30 Asia/Tokyo, verified read-only via `plutil` — as exact-instant
  schedule slots, and `runSchedulerOwner` gained a Honne JA shadow scan behind
  `LM_HONNE_JA_SHADOW_ENABLED`. The flag defaults to `false`, only the
  deliberate exact value `true` enables it, and it is enabled nowhere; the
  legacy LaunchAgent remains the loaded production owner.
- A manual one-shot trigger (`scripts/honne-ja-shadow-cycle.js run`) executed
  one real shadow cycle against the running local durable store on 2026-07-30.
  The one-time importer copied the 24 Honne JA hooks and four MP4s into the
  runtime data volume (pack `object://sha256/609d5414…`), and the cycle
  enqueued and completed generation job
  `marketing-video-generation:0f19ddbb…` for slot `2026-07-30T03:30:00.000Z`
  through the same `createWorkerHandlers`/`executeCapabilityJob` worker path
  as the HJA-007 proof. It selected `HJA-008` — the least-recent active hook
  after HJA-007 in the imported prior-use state — and emitted lineage whose
  `video_sha256`
  (`7658b8130ff2e750a143bd09462d11c30ace49d06aa587754bd088f27399165f`) equals
  the legacy `v2.mp4` SHA-256 byte for byte.
- The chained Instagram and TikTok publication jobs were enqueued durably and
  HELD: both remain `queued`, a durable hold row with status `shadow_held`
  records their job IDs, no worker holds the `marketing.video.publish`
  capability in shadow, and no Instagram, TikTok, or Postiz call occurred. A
  replay of the same slot returned `created=false` for all three jobs, claimed
  zero jobs, and appended no duplicate hold row.
- `scripts/honne-ja-shadow-status.js` reads the durable store and reports the
  count of consecutive EXPECTED 12:30/21:30 JST slots with exactly one
  verified shadow generation receipt each against the §13 seven-expected-run
  gate; expected slots that passed without a receipt row reset the count and
  are reported as `missed_slots`, and duplicate receipts for one slot also
  reset. No ownership cutover occurred and none is claimed.

The OpenClaw store also contains enabled entries for Larry, ReelClaw, app
reviews, Capafy publishing, CFO sync, and other jobs. Because the scheduler
currently exposes no active jobs and no next wake, these are treated as stale
configuration until a real run receipt proves otherwise.

### 3.3 Evidence and inference are separate

**Evidence:** launchd logs show real posts and executions; the shared marketing
runtime has no ledgers.

**Inference:** repetition is not primarily a prompt-quality problem. The
production generators cannot consume learned weights that were never produced
from attributed observations.

**Evidence:** the existing financial report is based on a wallet ledger and API
cost ledger.

**Inference:** it is an agent-economy P&L report, not yet a personal net-worth
or whole-business financial-health report.

## 4. External constraints and sources

| Source | Core statement | Design consequence |
|---|---|---|
| [Apple Analytics Reports](https://developer.apple.com/documentation/analytics-reports) | “Apple does not generate reports until you create a valid Analytics Report Request.” | Connector setup creates the request once, then polls and downloads all segments; missing requests are an explicit setup state |
| [Railway Cron Jobs](https://docs.railway.com/reference/cron-jobs) | “Services configured as cron jobs are expected to execute a task, and terminate as soon as that task is finished.” | Railway cron only enqueues bounded jobs; long rendering, browser, and learning work runs in leased workers |
| [The Twelve-Factor App: Codebase](https://12factor.net/codebase) | “One codebase tracked in revision control, many deploys” | Local and cloud use the same source and release artifact; deployment configuration changes, business logic does not |
| [Telegram Bot API](https://core.telegram.org/bots/api) | “The Bot API is an HTTP-based interface” | Telegram is a delivery surface, not the financial source of truth |
| [Moneytree LINK](https://docs.link.getmoneytree.com/docs) | Moneytree LINK exposes standardized financial data after user authorization and uses OAuth 2.0 Authorization Code Grant with PKCE | Production users connect through Moneytree LINK/OAuth; raw bank credentials never enter Life Manager |
| [Postiz Post Analytics](https://docs.postiz.com/public-api/analytics/post) | “Get analytics data for a specific published post.” | Keep Postiz during migration and collect post-level metrics by provider post ID instead of scraping immediately after publication |
| [Postiz public analytics controller](https://github.com/gitroomhq/postiz-app/blob/39516ab97fab8de49c00300a617bd39e0c325c77/apps/backend/src/public-api/routes/v1/public.integrations.controller.ts) | The public controller delegates `GET /analytics/post/:postId` to `checkPostAnalytics(postId, date)` | Treat provider post ID as a required future receipt join key and keep the observation window explicit |
| [instagrapi best practices](https://github.com/subzeroid/instagrapi/blob/master/docs/usage-guide/best-practices.md) | “Use the settings file next time” after one successful login and verification | Reuse a saved device/session; quarantine challenges instead of hammering password login, and require exact provider identity before recovery |
| [Microsoft SkillOpt](https://microsoft.github.io/SkillOpt/) | “SkillOpt makes the skill document itself the optimization target.” | Skill changes use scored rollout evidence, bounded edits, and a held-out keep/revert gate; production skills are never rewritten unconditionally |
| [GitHub repository archival](https://docs.github.com/en/repositories/archiving-a-github-repository/archiving-repositories) | “You can archive a repository to make it read-only for all users and indicate that it's no longer actively maintained.” | Preserve `life-manager-v0` history without permitting new writes, but only after its unique-content manifest and equivalence gate pass |
| [Stripe subscriptions](https://docs.stripe.com/billing/subscriptions/overview) | “Subscriptions require coordination between your site and Stripe” | Cloud scheduling and worker access follow durable webhook-derived entitlement; a client redirect or checkout page never grants access by itself |

## 5. Alternatives considered

| Approach | Strength | Fatal weakness | Decision |
|---|---|---|---|
| Railway-only monolith | Simple deployment and multi-user SaaS | API, scheduler, browser, rendering, and posting contend for one failure and scaling boundary | Rejected |
| Local-only Life Manager | Maximum privacy and simplest first migration | Lights-out, earthquakes, and machine failure stop production; cannot host thousands of tenants | Supported deployment, not the default |
| Cloud-only Life Manager | Always on and commercially scalable | Blocks the required safe migration path and excludes privacy/self-hosting users | Rejected as the only mode |
| Permanent split runtime where cloud requires a local worker | Reuses local browser sessions | Cloud uptime still depends on the user's machine | Rejected |
| One portable runtime with local and cloud deployment adapters | Removes OpenClaw first, preserves self-hosting, then adds always-on scale without rewriting loop logic | Requires strict adapter contracts and parity tests | Selected |

## 6. Target architecture

```text
                         COMMAND + REPORT SURFACES
       ┌───────────────┬──────────────────┬────────────────────┐
       │ Telegram bot  │ Web/PWA panel    │ CLI / Codex client │
       └───────┬───────┴─────────┬────────┴──────────┬─────────┘
               └─────────────────┼───────────────────┘
                                 ▼
                    LIFE MANAGER PORTABLE CORE
       ┌───────────────────────────────────────────────────────┐
       │ API/auth · tenant/product registry · policy engine   │
       │ scheduler · leased jobs · receipts · event ledgers   │
       │ finance projector · experiment/learning controller   │
       │ connector + loop + storage + secret interfaces       │
       └───────────────┬───────────────────────┬───────────────┘
                       │ same contracts/images │
          ┌────────────▼────────────┐  ┌──────▼────────────────────────┐
          │ LOCAL DEPLOYMENT        │  │ CLOUD DEPLOYMENT             │
          │ Docker Compose          │  │ Railway control plane        │
          │ local API/panel         │  │ managed PostgreSQL           │
          │ PostgreSQL              │  │ S3-compatible object store   │
          │ local object adapter    │  │ tenant cloud secret vault    │
          │ OS keychain/vault       │  │ autoscaled worker pools      │
          │ local worker pools      │  │ multi-tenant fair queue      │
          └────────────┬────────────┘  └──────┬────────────────────────┘
                       └──────────────┬────────┘
                                      ▼
       ┌───────────────────────────────────────────────────────┐
       │ API │ browser │ media │ publish │ observe │ learn    │
       │ finance │ mobile marketing │ writer │ gig │ Capafy   │
       └──────────────────────────┬────────────────────────────┘
                                  ▼
       App Store · Moneytree · Stripe · social platforms
                                  │
                                  ▼
                    receipts → metrics → decisions
```

Local and cloud are deployment profiles, not separate products. Local mode is
fully functional and OpenClaw-free. Cloud mode uses the same versioned
application packages and adds managed availability, tenant isolation, and
horizontal worker scaling. Codex running on the Mac may submit commands through
the authenticated API or CLI, but scheduled production work does not depend on
that Codex session or the Mac when the tenant uses cloud mode.

### 6.1 Canonical repository layout

This section is the only SSOT for the program-wide repository layout. The
Agent Economy ownership overlay, wallet/payment-provider boundaries, live
earnings attribution, and financial-independence stages are owned by
[`2026-07-19-anicca-one-repo-consolidation-spec.md`](./2026-07-19-anicca-one-repo-consolidation-spec.md).

The repository boundary is exact:

```text
GitHub SSOT:  Daisuke134/life-manager       (repository ID 1248111245)
legacy only:  Daisuke134/life-manager-v0    (repository ID 1273052304)
```

All new canonical code and operating specifications live in the active Life
Manager monorepo. The target layout extends its existing conventions:

```text
apps/
  life-manager/             # API, panel, Telegram, reports, cloud scheduler
adapters/                   # provider/transport boundaries
runtime/                    # portable scheduler and worker runtime
services/                   # deployable long-running services
skills/                     # generalized capabilities, never product credentials
packages/
  loop-core/
  job-protocol/
  runtime-adapters/
  finance-engine/
  marketing-engine/
  connector-contracts/
  product-packs/
    anicca-ios/
    honne-ai/
deploy/
  local/
    compose.yaml
  railway/
docs/
  migrations/
    life-manager-v0/        # signed file/behavior disposition and equivalence evidence
  superpowers/
    specs/                  # program/design SSOT
    plans/                  # ordered executable slices
```

`life-manager-v0` files are not copied blindly into a second top-level product.
All 35 tracked files are classified behavior-by-behavior; missing required
behavior is zero, the README is redirect-only, and the repository is archived.
Local checkout names are never runtime inputs: jobs use installed release/data
roots rather than either absolute checkout name.

The actual implementation follows existing repository conventions instead of
forcing this exact folder shape where it would create churn. Responsibility
boundaries and single-repository ownership are mandatory even if paths differ.

### 6.2 Job protocol

Every action is a durable job:

| Field | Meaning |
|---|---|
| `job_id` | globally unique idempotency key |
| `tenant_id` | owner boundary |
| `loop_id` | finance, marketing, writer, gig, or another registered loop |
| `capability` | collect, research, generate, render, publish, observe, learn, report |
| `worker_pool` | api, browser, media, publish, observe, learn, or report |
| `resource_class` | cpu/memory/gpu/browser requirements used for placement |
| `deployment_id` | local or cloud runtime that owns the lease |
| `input_refs` | immutable database/blob references, never embedded secrets |
| `lease_owner`, `lease_until` | single-writer worker claim |
| `attempt`, `max_attempts` | bounded retry |
| `effect_class` | read, draft, publish, money |
| `status` | queued, leased, succeeded, failed, dead-lettered |
| `receipt_ref` | immutable evidence of the real effect |

Workers advertise capabilities and heartbeat. The scheduler never knows
whether a worker is local or cloud, nor whether the implementation is Claude,
Codex, Hermes, or deterministic code. OpenClaw is not an adapter or fallback.

### 6.3 Runtime adapter contract

| Interface | Local implementation | Cloud implementation |
|---|---|---|
| Database | Docker PostgreSQL | managed PostgreSQL |
| Queue/leases | PostgreSQL claims | the same PostgreSQL claim protocol |
| Objects | local filesystem adapter or MinIO | S3-compatible object storage |
| Secrets | OS keychain or encrypted local vault | tenant-scoped cloud vault |
| Browser profile | encrypted local profile | encrypted tenant-scoped cloud profile |
| Scheduler | Life Manager scheduler service | the same scheduler service |
| Workers | local service containers | autoscaled service containers |
| Observability | local logs/receipts in panel | centralized logs/receipts in panel |

Business logic may depend only on these interfaces. It may not branch on
OpenClaw paths, machine usernames, or repository locations. Migration tests
run with `~/.openclaw` inaccessible.

### 6.4 Multi-tenant execution rules

| Concern | Required behavior |
|---|---|
| Isolation | every job, object, secret, browser profile, artifact, and receipt carries `tenant_id`; authorization fails closed |
| Fairness | tenant queues use weighted fair scheduling; one tenant cannot consume every worker |
| Limits | per-tenant publish, browser, rendering, spend, and connector rate limits |
| Idempotency | scheduler retries may create attempts, never duplicate external effects |
| Browser state | encrypted, tenant-scoped cloud profiles; ephemeral execution containers; no shared cookies |
| Scaling | each worker pool scales independently from queue depth and job age |
| Recovery | leases expire; another eligible worker in the same deployment reconciles before retrying an unknown effect |

Local mode keeps the same `tenant_id` boundary even for a single user. This
prevents local-only shortcuts from breaking later cloud migration.

### 6.5 Connector contract

Every source implements:

```text
connect() -> authorization state
sync(cursor) -> immutable source events + next cursor
health() -> freshness, last success, actionable error
normalize(events) -> canonical ledger rows
```

Initial connectors:

| Domain | Connectors |
|---|---|
| Cash and net worth | Moneytree LINK, manual balance, exchange/wallet read-only APIs |
| Mobile apps | App Store Connect Analytics/Sales, Mixpanel, and product-pack metric inputs |
| Web products | Stripe |
| Autonomous income | uGig, Capafy, clipping affiliate, writer, x402, bounty |
| Distribution | TikTok, Instagram, YouTube, X through OAuth/API where available and isolated cloud-browser adapters where necessary |

An unavailable connector returns `unavailable` with its last successful
snapshot. It never returns a fabricated zero.

## 7. Financial-health model

### 7.1 Canonical statements

| Statement | Contents |
|---|---|
| Personal balance sheet | cash, investments, crypto, receivables, liabilities, net worth |
| Daily cash flow | money in, money out, transfers, fees, realized gains/losses |
| Business P&L | revenue, refunds, platform fees, API/compute/ad costs, contribution profit by business |
| Recurring revenue | MRR, active paid, trials, new MRR, expansion, contraction, churn |
| Liquidity and risk | runway, tax reserve, emergency reserve, concentration, stale sources |

Every amount stores original currency, original amount, FX rate source,
converted amount, and timestamp. Transfers are excluded from income. Unrealized
asset appreciation is separated from earned business income.

### 7.2 Business dimensions

Initial business keys are:

`life_manager`, `anicca_ios`, `honne_ai`, `gig_work`, `capafy`,
`clipping_affiliate`, `writer`, `nisa`, `crypto_yield`,
`crypto_trading`, `x402`, and `bounty`.

The list is data, not code. Users can add products and businesses without a
deployment.

### 7.3 Telegram financial report

Agent Economy revenue attribution and live amounts MUST come from
[`2026-07-19-anicca-one-repo-consolidation-spec.md` §0.4](./2026-07-19-anicca-one-repo-consolidation-spec.md#04-agent-economy-earnings-ssot).
Unverified income, self-pay, seed capital, and principal recovery MUST NOT be
rendered as revenue; unavailable amounts render as `$0.00` or `unavailable`.

Daily report time defaults to 20:00 in the user's timezone, after the existing
financial-report convention. Each tenant can configure a different report
time; no second scheduler or report contract is created.

```text
FINANCIAL HEALTH · 2026-07-29

Net worth          ¥X       today +¥Y
Liquid cash        ¥X       30-day runway N months
Income today       ¥X       month ¥Y
Costs today        ¥X       month ¥Y
Operating profit   ¥X       margin Z%

Business           Today    Month    MRR
Life Manager       ...
Anicca iOS         ...
Honne AI           ...
Gig / Capafy       ...
Crypto / x402      ...

Mobile growth
Anicca: installs N · trials N · paid N · MRR $N
Honne:  installs N · trials N · paid N · MRR $N

Data health
Moneytree fresh · product metrics fresh · ASC delayed 1d

Action taken
Promoted hook rule H-17 after 72h canary; paused format F-04.
```

Delivery policy:

| Message | Cadence |
|---|---|
| Financial health | Daily |
| Weekly CFO review | Sunday evening |
| Month close | First complete day after month-end data is available |
| Exception | material source failure, unexpected spend, payment failure, abnormal revenue drop |
| Physical health | Separate daily message in a later release |
| Mental health | Separate daily message in a later release |

The daily message stays concise. Details open the authenticated panel.

### 7.4 Telegram UI/UX

Telegram is the daily command surface; the web panel is the detailed system of
record. The bot sends one scheduled digest per health domain plus
exception-only alerts, rather than narrating every background job.

```text
                         TELEGRAM TO-BE

 /start
   │
   ├─ identity + tenant
   ├─ choose Local or Cloud
   ├─ create Base/Solana public addresses and start zero-balance crypto core
   ├─ connect additional Finance / Health / Products capabilities when needed
   ├─ choose timezone + report times
   └─ first source-health check
             │
             ▼
 ┌──────────────────────────────────────────────────────────┐
 │ LIFE MANAGER · TODAY                                     │
 ├──────────────────────────────────────────────────────────┤
 │ Financial   —        no verified change yet              │
 │ Physical    —        no verified change yet              │
 │ Mental      —        no verified change yet              │
 │ Income      gross $0.00 · cost $0.00 · net $0.00         │
 ├──────────────────────────────────────────────────────────┤
 │ Next report: Financial Health at 20:00 JST               │
 │ Runtime: Cloud · healthy · Mac not required              │
 ├──────────────────────────────────────────────────────────┤
 │ [Financial] [Physical] [Mental]                          │
 │ [Income loops] [What changed?] [Open web panel]          │
 └──────────────────────────────────────────────────────────┘
             │
             ├─ scheduled separate reports
             ├─ user-requested drill-down
             └─ material exception alert
```

Report ownership is tenant-scoped:

| Recipient | Receives |
|---|---|
| Personal user | only their financial, physical, mental, products, loops, actions, and connector health |
| Business/product operator | their product funnel, revenue, publishing, experiments, and blocked actions |
| Life Manager platform owner/admin | aggregate SaaS MRR, active tenants, infrastructure cost, job reliability, and anonymized system health; never another tenant's raw ledger or health data |

The daily set is:

| Report | Core fields |
|---|---|
| Financial Health | net worth, cash, runway, income, costs, profit, MRR, source freshness, material deltas |
| Physical Health | sleep duration/quality, HR/HRV when available, steps/activity, recovery trend, one highest-leverage action |
| Mental Health | mood, stress, focus, screen time, habits/reflections, risk trend, one bounded intervention |
| Income & Growth | revenue and funnel by business; jobs attempted/won; posts, reach, installs, trials, paid, retention; best/worst experiment; rule kept/reverted |
| Runtime Health | local/cloud mode, last successful cycle, failed connectors, blocked jobs, stale data, required authorization |

Financial Health example:

```text
┌──────────────────────────────────────────────┐
│ LIFE MANAGER · FINANCIAL HEALTH              │
│ Wed, Jul 29 · data through 19:58 JST         │
├──────────────────────────────────────────────┤
│ HEALTH SCORE  72 / 100        ▲ 4 today      │
│ Net worth     ¥12,340,000     ▲ ¥31,400      │
│ Cash runway   14.2 months     Healthy        │
│ MRR           $1,240          ▲ $84 MTD      │
├──────────────────────────────────────────────┤
│ TODAY                 MONTH                  │
│ Income   ¥42,100       ¥611,300              │
│ Costs    ¥11,900       ¥203,800              │
│ Profit   ¥30,200       ¥407,500              │
├──────────────────────────────────────────────┤
│ BUSINESSES                                   │
│ Life Manager      ¥18,400  MRR $620          │
│ Anicca iOS         ¥7,900  38 installs       │
│ Honne AI            ¥3,100  21 installs       │
│ Gig / Capafy       ¥10,800                    │
│ Crypto / x402       ¥1,900                    │
├──────────────────────────────────────────────┤
│ NEEDS ATTENTION                              │
│ ⚠ App Store data is 26h old                  │
│ ↓ Honne install→trial fell 18% vs 7d base    │
├──────────────────────────────────────────────┤
│ LIFE MANAGER DID                             │
│ ✓ Published 8 creatives                      │
│ ✓ Kept hook H-17 after 72h canary            │
│ ↩ Reverted format F-04                       │
├──────────────────────────────────────────────┤
│ [Open dashboard] [Explain changes]           │
│ [Mobile apps]   [Fix connection]             │
└──────────────────────────────────────────────┘
```

Income & Growth example:

```text
┌──────────────────────────────────────────────┐
│ LIFE MANAGER · INCOME & GROWTH               │
│ Today · compared with 7-day baseline         │
├──────────────────────────────────────────────┤
│ TOTAL        ¥30,200 profit    MRR $1,240    │
├──────────────────────────────────────────────┤
│ MOBILE APPS                                  │
│ Anicca   8 posts · 38 installs · 2 trials    │
│           1 paid · $620 MRR · CPA ¥—         │
│ Honne    6 posts · 21 installs · 1 trial     │
│           0 paid · $180 MRR                   │
│ Best: H-17 confession hook · +42% installs   │
│ Next: test a distinct demo-first challenger  │
├──────────────────────────────────────────────┤
│ OTHER LOOPS                                  │
│ Gig       12 applied · 2 replies · 1 won     │
│ Capafy     4 published · ¥8,400 attributed   │
│ Writer     1 published · ¥0 confirmed        │
│ Crypto     ¥1,900 realized · risk within cap │
├──────────────────────────────────────────────┤
│ AUTONOMOUS CHANGES                           │
│ ✓ kept H-17 after 72h revenue canary         │
│ ↩ reverted F-04 after trial conversion drop  │
│ ⚠ Instagram session needs authorization      │
├──────────────────────────────────────────────┤
│ [Apps] [Experiments] [Loops] [Fix account]   │
└──────────────────────────────────────────────┘
```

Conversation flow:

```text
/start
  → Create tenant
  → Connect money sources
  → Add products/businesses
  → Connect App Store + channels
  → Choose timezone/report times
  → First reconciled snapshot

Scheduled digest
  → scan health and exceptions in under 30 seconds
  → tap a problem or business
  → receive a compact drill-down
  → open the authenticated web panel for ledger/experiment detail

Exception alert
  → state what changed, financial impact, and evidence
  → offer only safe actions: explain, retry sync, pause loop, open panel
  → money movement or expanded public broadcast requires its own authorization
```

Default delivery:

| Time | Message | Interaction |
|---|---|---|
| 08:00 | Physical Health | sleep/activity/recovery summary and one action |
| 20:00 | Financial Health | net worth, income, business P&L, mobile funnel, actions, data health |
| 20:10 | Income & Growth | product funnels, loop earnings, experiments, autonomous changes |
| 21:00 | Mental Health | mood/stress/attention summary and reflection |
| Immediate | Material exception only | source failure, payment failure, abnormal revenue/spend, blocked effect |
| Sunday 20:30 | Weekly CEO/CFO review | week-over-week financial, product, loop, health, and priority review |
| Month close | Monthly statement | net-worth change, P&L by business, MRR bridge, costs, taxes/reserves, retained learnings |

Users can disable or reschedule any non-critical digest. Immediate messages are
limited to material exceptions and authorization requests; successful
background jobs appear in the next digest rather than generating notification
spam.

## 8. Self-improving mobile marketing loop

### 8.1 Loop

```text
                           LIFE MANAGER SHARED MARKETING ENGINE
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Tenant → Product pack → Audience/account → Goal                                 │
│                       Anicca JA/EN | Honne JA/EN                                │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 v
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 1. OBSERVE                                                                      │
│ Market/source URLs → viral-format DNA → rights/source receipt → format library  │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 v
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 2. PROPOSE                                                                      │
│ Planner selects a portfolio; it does not force one producer forever             │
│ Larry slides | ReelClaw UGC+demo | Remotion | MoneyPrinterTurbo | future packs  │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 v
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 3. PRODUCE + GATE                                                               │
│ Distinct hook/format/scene/CTA → duplicate + proof + locale + policy + QA gates │
│ artifact_id + source_id + skill_version + product_id + account_id are immutable │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 v
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 4. PUBLISH                                                                      │
│ Postiz first → IG / TikTok / YouTube → provider post_id → exact public URL      │
│ Later replace each Postiz adapter independently without changing the contracts  │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 v
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 5. OBSERVE AT THE RIGHT HORIZON                                                 │
│ 2h delivery/hold | 24h engagement | 72h install/activation | 7–35d paid/retain  │
│ Postiz/platform + App Store Connect + product analytics                         │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 v
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 6. REWARD + LEARN                                                               │
│ revenue/retention > paid > trial > activated install > click > watch > view     │
│ One blamed rule → bounded SkillOpt edit → challenger → held-out/canary gate     │
│ keep or revert + rejected-edit memory + next-run consumption proof              │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                 ┌───────────────┴────────────────┐
                 v                                v
      Telegram: raw public URLs + result    Panel: read-only receipts,
      + app/revenue delta + source health   funnels, learning and failures
                 │                                │
                 └───────────────┬────────────────┘
                                 └──────────────────────────────→ next generation
```

### 8.2 What is shared and what is isolated

| Shared across products | Isolated per product/channel/audience |
|---|---|
| job protocol, ledgers, experiment controller, canary/revert, dashboards, connector interfaces | promise, proof, offer, forbidden claims, hook weights, format library, platform account, locale, attribution, reward |

This prevents an Anicca hook winner from silently changing Honne output.

### 8.3 Format DNA

The engine learns structure, not verbatim creative:

| Slice | Examples |
|---|---|
| Hook | confession, contradiction, threat, curiosity gap, specific outcome |
| Narrative | problem–agitation–proof, before/after, demo, reaction, list |
| Visual grammar | first-frame text density, cuts, slide count, product reveal timing |
| Audio | voice, music energy, silence, sound-effect timing |
| CTA | install, comment, save, trial, direct proof |

Each format records source URL, observed date, public metrics, extracted
structure, allowed reuse, and similarity fingerprints. Copyrighted assets are
not copied into the product.

### 8.4 Variation gates

A candidate fails before rendering when:

1. Its normalized hook equals a hook used by the same account in the recent
   exclusion window.
2. Semantic similarity to a recent hook exceeds the configured product limit.
3. The same format family would exceed its rolling share cap.
4. Product proof, locale, platform, or CTA does not match the product pack.
5. The visual checksum or transcript is effectively a duplicate.

Variation is measured, not requested with a prompt.

### 8.5 Reward hierarchy

| Horizon | Signal | Use |
|---|---|---|
| 2 hours | valid publication, views, first-frame hold | detect delivery or creative failure |
| 24 hours | hold, completion, saves, profile/product clicks | rank hooks and formats |
| 72 hours | attributed installs and activated users | promote acquisition winners |
| 7–35 days | trials, paid users, proceeds, retention | promote revenue winners |

The optimizer uses the deepest available reward. Views cannot override a
measured loss in paid conversion. Missing revenue remains unknown rather than
zero.

### 8.6 Anicca and Honne product packs

| Pack | Required proof |
|---|---|
| Anicca iOS | notification/Nudge experience, actual intervention outcomes, supported problem types, real paywall and price |
| Honne AI | real product demo, language-matched assets, actual transformation, real store/paywall path |

Each pack owns JA and EN audiences separately. Existing Larry and ReelClaw
producers become adapters behind the same artifact/publication contracts.

## 9. `$10k MRR` operating model

No verified product-level subscription baseline is imported into Life Manager.
The plan therefore treats the figures below as target mechanics, never as a
claim about Anicca or Honne revenue.

Twelve-month scenarios:

| Scenario | Blended MRR / active subscriber | Install→paid | Monthly churn | Active subscribers needed | New paid/month needed | Installs/month needed |
|---|---:|---:|---:|---:|---:|---:|
| Best | $8.00 | 5.0% | 5% | 1,250 | 136 | 2,714 |
| Base | $6.00 | 3.0% | 8% | 1,667 | 211 | 7,021 |
| Worst | $4.17 | 1.5% | 12% | 2,399 | 367 | 24,449 |

These are target mechanics, not forecasts. The first growth gate is not
“post more”; it is:

1. Restore trustworthy per-product install and revenue collection.
2. Establish one complete attribution chain from publication to paid.
3. Raise the number of genuinely distinct tested hooks per week.
4. Improve the weakest measured funnel step.
5. Scale publishing only after a challenger beats its product-specific
   baseline without retention or revenue regression.

## 10. To-Be Life Manager UI/UX

### 10.1 Navigation

```text
┌──────────────────────┬───────────────────────────────────────────────┐
│ LIFE MANAGER         │ TODAY                                         │
│                      │                                               │
│ ● Today              │ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ │
│ Health               │ │Finance │ │Physical│ │Mental  │ │Income  │ │
│   Financial          │ │72 ▲4   │ │64 ▼3   │ │78 ▲6  │ │59 ▲2  │ │
│   Physical           │ └────────┘ └────────┘ └────────┘ └────────┘ │
│   Mental             │                                               │
│ Income Loops         │ Net worth / runway / profit / MRR             │
│   Portfolio          │ Business contribution and mobile funnel       │
│   Mobile Apps        │                                               │
│   Web Apps           │ ┌───────────────────────────────────────────┐ │
│   Gig/Affiliate      │ │ Attention                                 │ │
│   Capafy/Writer      │ │ ASC stale · IG authorization · 1 blocked │ │
│   Crypto/Bounty      │ └───────────────────────────────────────────┘ │
│ Marketing Studio     │                                               │
│ Reports              │ Recent actions · receipts · source health     │
│ Connections          │                                               │
│ Settings             │ Runtime: Cloud  [Switch/export to Local]      │
└──────────────────────┴───────────────────────────────────────────────┘
```

### 10.2 Today

The first screen answers three questions:

1. Am I financially healthier than yesterday?
2. What made or lost money?
3. What did Life Manager do, and what needs attention?

Top cards:

| Card | Content |
|---|---|
| Net worth | current value, day/month delta, freshness |
| Income | today and month-to-date |
| Operating profit | revenue minus attributable costs |
| Recurring revenue | total MRR and target progress |
| Attention | failed connector, anomaly, blocked job, required authorization |

Below the cards: business contribution, mobile growth funnel, recent autonomous
actions, and source-health strip.

### 10.3 Financial Health

Four tabs:

| Tab | Contents |
|---|---|
| Overview | net worth, liquid cash, runway, income, expenses, profit |
| Businesses | P&L and MRR by product/business |
| Assets | bank, NISA, crypto, yield positions, liabilities |
| Ledger | reconciled transactions, classifications, provenance, freshness |

All numbers show source and last sync. Unknown values display “Unavailable”,
never `0`.

### 10.4 Mobile Apps

Portfolio row per app:

`installs → activation → paywall → trial → paid → retained → MRR`

App detail includes acquisition by channel/creative, store conversion,
subscription cohorts, experiment history, content calendar, and the current
bottleneck. Anicca and Honne never share learned weights.

### 10.5 Marketing Studio

| Area | User sees |
|---|---|
| Content | published artifact thumbnail/title plus the raw TikTok, Instagram, or YouTube URL |
| Queue | planned, rendering, scheduled, published, observing |
| Format library | source, format DNA, product fit, recent usage, performance |
| Learning audit | changed rule, blame evidence, canary, keep/revert, consumption proof; read-only and autonomous |
| Accounts | platform health, last successful post, rate/quality limits |

There are no user-facing experiment buttons and no public artifact page. The UI
exposes receipts, not agent narration. A green state requires a real platform
URL or verified metric row.

### 10.6 Connections and deployment

Users connect App Store Connect with an API key, social platforms with
OAuth/session adapters, and banking through Moneytree LINK. Raw passwords are
not a product interface.

| Mode | User experience | Availability |
|---|---|---|
| Cloud, recommended | sign in from phone/web, authorize connectors, Life Manager remains online without a personal computer | managed multi-tenant services and autoscaled workers |
| Local/self-hosted | install Life Manager, run one command, use localhost/PWA and optional Telegram | runs only while that machine is online |
| Local→Cloud migration | export an encrypted tenant bundle, import it to cloud, reconcile cursors and receipts, then switch scheduler ownership | no loop runs from both schedulers during cutover |

The panel shows the active deployment, scheduler owner, last successful cycle,
and whether turning off the current machine would stop work. Mac Codex commands
use `life-manager` CLI or the authenticated API in either mode.

## 11. Failure handling

| Failure | Behavior |
|---|---|
| Source delayed | retain last good value, mark stale, exclude from fresh delta |
| Duplicate webhook | inbox idempotency key returns existing receipt |
| Local worker or cloud worker dies | lease expires; bounded retry on an eligible worker in the same deployment |
| Publish result unknown | reconcile platform before retry; never blind repost |
| Metrics unavailable | observation becomes insufficient; no learning change |
| Canary regression | restore prior weight hash and record revert |
| Cross-tenant/product evidence | reject and dead-letter |
| OpenClaw stopped during shadow | new path continues; any dependency failure blocks cutover |
| Local→cloud transfer interrupted | scheduler ownership remains with the source until import reconciliation succeeds |
| Internet/power loss in local mode | show offline/stale state; resume idempotently when available; do not claim always-on execution |
| Mac unavailable in cloud mode | no effect; API, workers, schedules, and reports continue in cloud |

## 12. Ordered delivery plan

The order below is the program source of truth. Milestone A is a hard gate:
cloud migration work does not begin until every retained loop is demonstrably
OpenClaw-independent and running under Life Manager locally.

Order 0 consolidation completed:
`AE-X402-SOURCE-CONSOLIDATE-1`. `OSS-SECURITY-BASELINE-1` merged in PR
#1274 with all exact-five security checks green. `REPO-V0-RETIRE-1` then
completed 35/35 disposition, issue transfer, redirect, archive, and
runtime-reference-zero. Evidence:
`docs/evidence/security/2026-07-29-oss-security-baseline.md` and
`docs/evidence/repository/2026-07-29-life-manager-v0-retirement.md`.
The x402 nine-route seller is present in canonical
`services/x402-endpoint`; historical and canonical suites pass 68/68, the
migration contract passes 1/1, ledger regression passes 22/22, and dependency
audit is zero. PR #1295 merged as `4d5c60b9…`; Railway source/root/commit,
deployment `cee9598d…` SUCCESS, nine paid gates, settlement target exactly1,
ledger real-loop duplicate1, exact-five, and 251/251 cutover health are read back.
`OSS-MERGE-1` PR #1268 is merged as canonical `8d47689d3…`; that exact `main`
commit passes a clean fresh clone, 647/647 app tests, all eight evals, panel
privacy, the seven-source manifest, and the single canonical runner contract.
The current migration subcursor is the generic Honne JA
`marketing.video.generate` shadow slice under Order 11.

| Order | Deliverable | Exit evidence |
|---:|---|---|
| 0 | Finish single-repository consolidation | **done** — PR #1268 merged as `8d47689d3…`; exact-main fresh clone, source manifest, single runner, security boundary, v0 archive, and x402 source cutover are verified. Browser/parity/cloud/remaining-legacy gates continue under their own ordered rows |
| 1 | Freeze all scheduler/runtime inventory | machine-readable inventory covers every captured OpenClaw store row and user LaunchAgent, including disabled, unloaded, and parse-error rows, with redacted command, cadence, source boundary, load state, and latest available receipt |
| 2 | Decide every legacy job | each row is marked `migrate`, `replace`, `retire`, or `retain-external` (vocabulary amendment, decided: third-party/system rows whose command references no openclaw/legacy path stay outside migration scope with owner `system`) with Life Manager owner and rollback action; no unowned enabled/loaded job |
| 3 | Define portable domain contracts | tenant/product/business/loop/job/artifact/publication/source-event/receipt schemas and adapter interfaces pass contract tests |
| 4 | Create Life Manager local deployment | one command starts API, panel, scheduler, PostgreSQL, object adapter, and workers without OpenClaw |
| 5 | Establish Life Manager-owned paths | code, prompts, media templates, state, logs, and config live in the monorepo or configured Life Manager data root; dependency scan rejects legacy absolute paths |
| 6 | Move secrets out of OpenClaw | every retained connector reads OS keychain/encrypted Life Manager vault references; `~/.openclaw/.env` is inaccessible in tests |
| 7 | Implement durable local scheduler and job protocol | enqueue, claim, heartbeat, retry, dead-letter, idempotency, effect reconciliation, and receipts pass restart tests |
| 8 | Extract reusable Profitable Claude contracts | registry, schemas, learner, canary, terminalizer, and dashboard logic run from Life Manager packages |
| 9 | Migrate Telegram command/report delivery | Life Manager owns bot routing, tenant mapping, digest schedules, raw public URLs, receipts, and anti-spam policy; no experiment buttons or public artifact page |
| 10 | Migrate existing financial-report loop | current x402/TaskMarket/USDC daily and weekly outputs run locally from Life Manager with matching snapshot hashes |
| 11 | Migrate Larry/ReelClaw Anicca and Honne | all retained slideshow/video generation, rendering, posting, schedules, assets, and sessions run through Life Manager jobs |
| 12 | Migrate Capafy, clipping, writer, gig, bounty, and other income loops | every retained income job produces a Life Manager receipt and no legacy-path read |
| 13 | Migrate retained personal, school, comedy, SEO, mail, memory, and maintenance jobs | all remaining retained enabled/loaded workflows are Life Manager loops or explicitly retired |
| 14 | Switch local scheduler ownership | launchd, if retained only as a boot trigger, starts Life Manager; no launchd command invokes OpenClaw or legacy repositories |
| 15 | Prove Milestone A: OpenClaw-free local | stop gateway, deny/rename `~/.openclaw`, run seven expected cycles, reconcile real effects, scan zero runtime references, preserve signed rollback inventory |
| 16 | Archive non-v0 legacy runtime sources | create signed read-only archives and retention policy for OpenClaw, Profitable Claude, and retired checkouts; no production fallback to archived code (`life-manager-v0` already closes at Order 0) |
| 17 | Package supported local/self-hosted mode | versioned installer/Compose bundle, upgrade, backup/restore, health check, and local documentation pass on a clean machine |
| 18 | Implement cloud deployment adapters | managed PostgreSQL, object storage, tenant vault, isolated browser profiles, and provider-neutral worker placement pass the same contracts |
| 19 | Deploy cloud control plane and worker pools | Railway API/panel/scheduler plus API/browser/media/publish/observe/learn/report workers operate from the same release version |
| 20 | Add multi-tenant isolation, fairness, and autoscaling | row/secret/profile isolation, quotas, rate limits, weighted scheduling, queue-depth scaling, and noisy-neighbor tests pass |
| 21 | Implement local→cloud tenant migration | encrypted export/import preserves IDs, cursors, artifacts, receipts, settings, and secrets; exactly one scheduler owns each loop |
| 22 | Shadow cloud against local | cloud replays read-only/duplicate-safe work and matches local artifacts, reports, and decision hashes |
| 23 | Canary and cut over Dais to cloud | real retained posts and reports run in cloud; local scheduler is stopped after reconciled parity |
| 24 | Prove cloud-default availability | Mac Mini powered off through seven expected cycles; retained loops, reports, and alerts continue without duplicates |
| 25 | Ship monthly cloud subscription | phone/web signup, Stripe monthly entitlement, cloud connector authorization, quotas, source health, export/delete, cancellation, and self-host option |
| 26 | Prove 1,000-tenant scale and recovery | synthetic workload demonstrates fair scheduling, credential isolation, idempotent effects, worker loss recovery, and bounded queue age |
| 27 | Add financial connector framework | cursors, freshness, original currency, FX provenance, transfer handling, and explicit unavailable states |
| 28 | Add Moneytree and App Store Connect | bank balance plus per-product installs, proceeds, and connector health; subscription metrics arrive only through a product-pack input owned outside Life Manager |
| 29 | Add Stripe and read-only crypto/investment assets | net worth and business P&L reconcile across supported sources |
| 30 | Ship Financial Health UI and Telegram | panel and Telegram render the same snapshot hash with daily, weekly, monthly, and exception receipts |
| 31 | Create Anicca and Honne product packs | independent JA/EN offers, attribution, rewards, weights, accounts, and forbidden claims |
| 32 | Complete publication lineage | every Larry/ReelClaw artifact joins product, campaign, experiment, publication URL, and real effect receipt |
| 33 | Add metric collectors and app attribution | 2h/24h/72h/7d platform metrics join installs, trials, paid users, proceeds, and retention without converting unavailable to zero |
| 34 | Build viral-format intake and variation gates | source/right receipts, format DNA, duplicate hooks, semantic similarity, format concentration, proof, locale, and visual/transcript gates |
| 35 | Activate bounded self-improvement | one-rule blame, challenger, canary, keep/revert, and next-run consumption proof work for Anicca and Honne separately |
| 36 | Add Physical and Mental Health | separate daily messages, dashboard sections, source freshness, risk policy, and one-action interventions |
| 37 | Design and build mobile-app development loop | metrics and feedback drive bounded app iteration before generalized creation/release |
| 38 | Generalize web-app development loop | reuse portable runtime, product, finance, marketing, experiment, and deployment contracts |

### 12.1 Remaining work from the measured state

The numbered program above remains the SSOT. Until Order 26 passes, only
runtime-migration work is active:

| Now | Work | Why it is still missing | Done evidence |
|---:|---|---|---|
| 1 | Repair and freeze the machine-readable scheduler inventory | the OpenClaw store and live scheduler disagree, and launchd is the real owner of many loops | every stored and loaded job has one `migrate`, `replace`, or `retire` decision and an owner; measured: all 399 captured rows and all 269 enabled-or-loaded rows now have exactly one disposition and a non-null owner |
| 2 | Decide every legacy job and freeze new legacy writes | inventory without disposition cannot drive a safe cutover | each job has a Life Manager owner, target adapter, effect class, verification command, and rollback action; measured: 214 migrate, 40 replace, 132 retire, and 13 retain-external rows are recorded with rollback actions, and verification commands are set only for the five adapters that already exist |
| 3 | Build the portable local runtime foundation | current loops lack one shared Life Manager data root, secret provider, durable generic job protocol, and local service bundle. A legacy-path dependency scan now exists and passes (`apps/life-manager/scripts/scan-legacy-paths.js` + `scan-legacy-paths.test.js`, wired into `npm test` as `test:legacy-paths`): it walks the monorepo runtime (`apps/life-manager`, `runtime/`) plus every skill the runtime actually loads or spawns — `skills/video/daily-lm-video`, `skills/video/lm-distribution`, `skills/tools/telegram-user`, `skills/life-manager`, and `skills/earn/marketing-engine` (whose `run_agent.sh` is spawned by `life-manager-daily.sh` and `life-manager-dev-d0.sh`) — and fails on any non-allowlisted `.openclaw`/`profitable-claude`/`life-manager-v0` reference or legacy anicca code-root reference (`$HOME`-, `${HOME}`-, or `~`-rooted anicca checkout and the anicca-oss checkout). The allowlist holds only (a) line-pinned denial regexes and copy-only migration tooling and (b) an explicitly tracked, line-and-content-pinned set of five pre-Order-12 holes: the x402-sell/taskmarket/payout earn-loop boot defaults that still point at the legacy anicca code roots, each named with its owning Order (Order 12); `verifyAllowlist` fails the scan the moment any pinned line moves, changes, or disappears. The runtime's own legacy-path dependencies in that scope were removed: `daily-dev-loop.js` defaults its state dir to `<data root>/state/life-manager-dev` via `resolveDataRoot` in `runtime-paths.js` (`LM_DATA_DIR`, falling back to `~/.local/state/life-manager`), the four launchd boot scripts (payout, x402 ledger, taskmarket ledger, ugig observer) load `LIFE_MANAGER_ENV_FILE` (default `~/.local/state/life-manager/.env`) through a shared guarded loader that warns-but-boots when the file is absent and refuses (exit 1) any env file beneath a legacy runtime root, the taskmarket/ugig installers and the dev/taskmarket/ugig launchd templates write logs beneath `~/.local/state/life-manager/logs`, and the daily video generator's argless defaults resolve to the same `<data root>/state/lm-video` paths `life-manager-daily.sh` exports. Existing on-disk legacy state (lm-video recordings/render state, dev-loop `done.jsonl` dedup history) is migrated copy-based via `apps/life-manager/scripts/migrate-legacy-state.sh` (idempotent copy with size readback, never move/delete — the legacy loop stays owner until cutover); until that copy has run, `generate.py` and the dev loop fail loudly naming the migration script instead of silently starting empty or silently reading the legacy path. Still OPEN in this row (not claimed): the shared secret vault/provider (Order 6) and the legacy-env-inaccessibility proof (cutover gate 6: denied `~/.openclaw` access without interruption); no Order is marked done by this slice | one command starts API, panel, scheduler, database, objects, and workers while all legacy roots are denied |
| 4 | Finish Telegram command migration and shadow the current financial report | the bounded report adapter is complete, but the rest of bot command routing and seven-run cutover evidence remain. An unbounded enqueue defect in the report scheduler was measured and fixed: the scheduler derived the report instant from POLL time (`Math.floor(Date.now() / LM_FINANCIAL_REPORT_POLL_MS) * LM_FINANCIAL_REPORT_POLL_MS`), so every 5-minute poll minted a new `job_id`/`effect_key`. The running local stack held 14 distinct `queued` `report.financial.telegram` jobs between 04:32:25Z and 05:02:25Z on 2026-07-30 (one daily+weekly pair per poll, about 576/day, grown to 24 rows by 05:35Z), all at `attempt = 0` and none executable, because their instants were mid-afternoon local while the report only releases from 20:00 local. Job identity is now anchored to the CADENCE slot in one new source of truth, `apps/life-manager/lib/financial-report-schedule.js` (daily 20:00 local, weekly Sunday 20:05 local — the exact window `dueReportKinds` enforces, which `financial-report-runtime.js` now delegates to instead of keeping a second copy), and the scheduler passes real `Date.now()` plus `LM_FINANCIAL_REPORT_TIME_ZONE`. Measured against the real local store inside a rolled-back transaction, three polls in one due window plus one poll in the next period minted 6 rows under the old algorithm and 2 rows under the new one (exactly one per due period, repeated polls are no-ops), and outside the release window the scan enqueues nothing at all. The 24 littered rows were listed and then removed by the new idempotent, dry-run-by-default cleaner `apps/life-manager/scripts/financial-report-cleanup-jobs.js`, which deletes only never-attempted, never-leased, receipt-free `queued` rows whose instant is not an exact cadence slot and re-asserts that predicate inside the DELETE (24 scanned, 24 off-cadence, 24 deleted, 0 rows remaining). A shadow-hold path for the report now exists mirroring the Honne JA shadow contract: default OFF behind `LM_FINANCIAL_REPORT_SHADOW_ENABLED` (enabled nowhere in repo compose), and when enabled the worker computes the snapshot FOR REAL (real tenant, wallet ledger, cost totals, and on-chain balance reads, real `snapshot_hash` — proven byte-identical to the sending path's hash in tests) but HOLDS the send: `runFinancialReport` returns `shadow_held` before the Supabase send ledger is read as authority, claimed, or patched, no Telegram secret is resolved, the injected sender throws if anything attempts a send, and each hold is recorded durably twice (runtime receipt with status `shadow_held` plus an idempotent `held.jsonl` hold ledger beneath the tenant data root). That keeps the legacy launchd owner `ai.anicca.life-manager-financial-report` the sole real sender, because a shadow-written `pending` receipt row would have made that owner see a duplicate and skip its real send. A seven-run gate reader `apps/life-manager/scripts/financial-report-shadow-status.js` reports n/7 with EXACTLY the `honne-ja-shadow-status.js` semantics — the expected-run grid is expanded backward from now over the interleaved daily+weekly cadence, only the trailing run of consecutive expected runs each holding exactly one verified receipt counts, an expected run released with no receipt row breaks the streak and is listed in `missed_runs`, a duplicate receipt for one expected run is a gate violation that also resets, and an off-grid or not-yet-due run is never counted and never reported missed. Its gate truth is the durable runtime `shadow_held` receipts, with `--source legacy` available as an explicit cross-check of the legacy Supabase send ledger that fails loudly without `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` instead of printing an unmeasured 0/7 or 7/7; read against the real local store it prints `0/7` with `rows_read: 0`, because shadow is enabled nowhere yet. The financial report test family (snapshot, schedule, runtime, migration, shadow runtime, gate reader, cleaner) was previously absent from `npm test` and is now registered as `test:financial-report`; the whole suite passes 1,884 node tests plus 8 python tests with zero failures. No Order is marked done by this slice: command routing, shadow enablement, and the seven-run evidence itself remain open | **report slice proven:** local Life Manager sent real `message_id=432`, stored matching snapshot/effect receipt, and read no OpenClaw env; remaining command routing and seven-run shadow stay open |
| 5 | Import shared execution contracts needed by retained loops | the shared adapter registry, content-addressed object import, tenant profile boundary, and financial/first marketing adapters are complete; most marketing and income loops still execute through legacy paths | Life Manager owns the remaining minimum runner, schemas, artifacts, publications, receipts, and verification adapters needed to preserve behavior |
| 6 | Migrate Larry/ReelClaw, Capafy, clipping, writer, gig, bounty, and all retained loops | `ai.anicca.life-manager-daily` now has real portable generation and TikTok distribution receipts, a fixed visible-hook render, an idempotent generation→Instagram/TikTok durable-job chain, a read-only verified Life Manager-owned IG profile, and a generic due-window observation pipeline. Honne JA now also has a generic Life Manager-owned 24-hook/four-media producer with a completed durable `HJA-007` shadow receipt and idempotent replay. A generic (product-agnostic) marketing video publication adapter now exists at `apps/life-manager/lib/marketing-video-publication-adapter.js`, binding product/format/form/locale/slot/creative to one platform-scoped publish effect and passing its contract tests (job build, Instagram+TikTok planning, tenant-scoped provider execution with lineage/URL, and cross-product/mismatched-provider rejection); its job identity now agrees with its effect identity (job_id is derived from tenant + effect_key, slot is lineage only), so a replay of the same bytes+caption+platform at a new slot can never violate the database's `UNIQUE (tenant_id, effect_key)` rule or double-post. Its reconcile path is now proven by passing tests: `distribute.py` writes format/form/locale/slot lineage into every ledger row, a ledger-recovered receipt passes the adapter's own verification before "present" is returned, `provider_reconciled` is propagated from the ledger row (never fabricated), the absent path returns the reconciler-required receipt shape (`lookup: "ledger_no_published_row"`), and legacy shadow rows without lineage resolve to "unknown" without crashing the reader; the distribution subprocess also runs on an allowlisted environment instead of the full parent env. Reconcile provenance is now propagated on all paths (the ledger short-circuit reports the existing row's `provider_reconciled` instead of fabricating true, and the subprocess allowlist passes the real chain's `INSTAGRAPI_PYTHON`/`CDP_HOST`/`CDP_PORT` through), unknown reconciliation now ages (a durable per-attempt counter dead-letters the job with `RECONCILE_UNKNOWN_EXHAUSTED` after 5 consecutive unknown reconcile results, reset on resolution, per `migrations/20260730_runtime_reconcile_unknown_aging.sql`), and the chain's two-platform fanout is sequential fail-fast (a first-platform enqueue collision stops the remaining platform's enqueue in the same scan), all proven by passing python/node/postgres tests. It is not yet wired into any scheduler or the loop-adapter registry manifest. A generic `marketing-video-publication-chain.js` now chains one generic video generation receipt into exactly two independent durable Instagram/TikTok publication jobs product-generically, with an end-to-end fake-store proof (enqueue→claim→execute→complete, then full replay with 0 new jobs, 0 claimable jobs, 0 additional provider executions, under the enforced `(tenant_id, effect_key)` unique rule) and cross-product/hash-mismatch/different-slot rejection all proven by passing tests; it is not yet wired into any scheduler. Honne JA generic video scheduling is now wired into the Life Manager scheduler in shadow mode behind `LM_HONNE_JA_SHADOW_ENABLED` (default `false`, enabled nowhere), with slots encoding exactly the legacy 12:30/21:30 Asia/Tokyo launchd cadence (`lib/honne-ja-shadow-schedule.js`); one real manual shadow cycle (`scripts/honne-ja-shadow-cycle.js`) against the running local durable store completed generation receipt hook `HJA-008` (job `marketing-video-generation:0f19ddbb…`, slot `2026-07-30T03:30:00.000Z`, `video_sha256` equal to the legacy source bytes) through the same worker path as the HJA-007 proof, and enqueued both Instagram/TikTok publication jobs durably in a held state (`queued` + durable `shadow_held` hold row, zero provider calls, idempotent replay with no new rows); a seven-cycle status reader (`scripts/honne-ja-shadow-status.js`) counts, per §13 semantics, only the trailing run of consecutive EXPECTED 12:30/21:30 JST slots each holding exactly one verified receipt — an expected slot that passed with no receipt row (scheduler off/stopped) breaks and resets the count and is reported in `missed_slots`, and a duplicate receipt for one slot is a gate violation that also resets — so scattered receipts can never reach `gate_met`; it reports n/7 toward the §13 seven-expected-run gate. The legacy Honne launchd owner remains untouched and no cutover is claimed. Product attribution, bounded learning, the remaining broken Larry/ReelClaw slices, and all other loops remain open; all new fanout stays disabled during shadowing. Local compose stack shadow enablement was performed on 2026-07-30 13:33 JST (scheduler `LM_HONNE_JA_SHADOW_ENABLED=true`, worker capabilities generate-only — `runtime.noop,marketing.video.generate`, `marketing.video.publish` granted nowhere — via a gitignored `deploy/local/compose.override.yaml` that leaves repo compose defaults off), so seven-cycle shadow evidence now accrues automatically at the 12:30/21:30 JST slots (status read 1/7 with zero missed slots after restart; both held publication jobs remained queued with zero attempts) | every retained effect executes from a Life Manager job and produces a machine-verifiable receipt |
| 7 | Switch scheduler ownership and prove OpenClaw-free local | launchd and OpenClaw can still become competing writers | seven expected local cycles pass with the gateway stopped and all legacy roots inaccessible, without missed or duplicate effects |
| 8 | Package the supported local option | a working checkout is not yet a reproducible self-hosted product | clean-machine install, upgrade, backup/restore, health check, and uninstall verification pass |
| 9 | Deploy the same release to cloud | current Railway service does not yet own every retained loop or worker class | API, scheduler, and worker pools run the same contracts and release hashes as local |
| 10 | Add cloud tenant isolation and monthly subscription | hosted operation needs durable entitlement and fair resource isolation | Stripe webhook entitlement, tenant isolation, quotas, cancellation/export, and noisy-neighbor tests pass |
| 11 | Shadow, cut over, and prove Mac-independent cloud | cloud cannot become scheduler owner without parity evidence | reconciled shadow, Dais canary, then seven expected cycles with the Mac Mini powered off and no duplicate effects |
| 12 | Resume product feature work | finance expansion and marketing self-improvement are intentionally frozen during migration | Order 26 is complete; Orders 27–38 become active in sequence |

## 13. Cutover gates

No legacy job is disabled until its replacement passes:

1. Seven consecutive expected runs have complete receipts.
2. At least one real publication per selected account is reconciled to a
   platform URL.
3. Financial panel and Telegram share a snapshot hash.
4. Local worker restart does not create duplicate effects.
5. OpenClaw dependency scan is empty for migrated runtime paths.
6. Forced OpenClaw shutdown plus denied access to `~/.openclaw` does not
   interrupt local Life Manager.
7. Rollback restores the prior scheduler state from a signed inventory.

Cloud becomes Dais's scheduler owner only after:

1. The same release passes local and cloud contract tests.
2. Local and cloud shadow outputs reconcile.
3. One scheduler-owner lease prevents double execution during transfer.
4. Real posting and Telegram delivery succeed from cloud.
5. A powered-off Mac does not interrupt seven expected cloud cycles.

## 14. Security and commercial constraints

| Constraint | Requirement |
|---|---|
| Tenant isolation | every row and job is tenant-scoped; cross-tenant joins fail closed |
| Credentials | encrypted at rest; references only in jobs; redacted in logs and reports |
| Local secrets | OS keychain or encrypted Life Manager vault; never `.env` files inherited from OpenClaw |
| Cloud secrets | tenant-scoped vault with audited access and rotation |
| Bank access | Moneytree LINK/OAuth; no raw MUFG credentials |
| Apple access | App Store Connect API keys/delegated roles; no stored Apple ID password |
| Financial action | read-only in this spec |
| Publishing | explicit connector authorization and auditable publication receipt |
| Data export/delete | user-controlled export and deletion without deleting financial audit records required by law |
| Claims | no guaranteed income or “automatic $10k MRR” promise |

## 15. Success metrics

| Layer | Metric |
|---|---|
| Independence | retained loops with zero OpenClaw/legacy-path references; unowned scheduler entries |
| Portability | contract suite passing unchanged in local and cloud modes; tenant export/import reconciliation |
| Reliability | expected jobs with valid receipts; duplicate effects; stale sources |
| Variety | unique hook fingerprints; format concentration; duplicate rejection rate |
| Acquisition | attributed installs per 1,000 impressions and per publication |
| Monetization | install→trial, trial→paid, paid retention, MRR, proceeds |
| Learning | scorable observations, kept challengers, reverted regressions, consumed weight receipts |
| Finance | reconciled net worth coverage, classified income coverage, source freshness |
| Product | users whose measured monthly benefit/revenue exceeds subscription cost |

## 16. Spec self-review

| Check | Result |
|---|---|
| Placeholder scan | No unresolved implementation placeholders |
| Internal consistency | One portable core and job protocol run in local and cloud deployments; Telegram/panel are projections of the same PostgreSQL-ledger contracts |
| Scope | Program is decomposed into OpenClaw independence, supported local packaging, cloud deployment and SaaS scale, then financial/growth closure and later health/development loops |
| Ambiguity | Local is a supported full deployment; cloud is Dais's eventual default; cloud never requires a local worker; OpenClaw is neither adapter nor fallback |
| Evidence honesty | Current ASC snapshots are marked inconsistent; unavailable product metrics never become zero |
