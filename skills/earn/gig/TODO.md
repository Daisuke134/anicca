# Open work on the Coconala loop

Ordered. Each item says what was measured, not what is suspected. Anything without
evidence does not belong on this list.

The four lanes run from `~/gig/releases/life-manager/<sha>/`, cut from `main` by
`gig_release.py`. See `README.md` for how the whole thing is installed.

## Current scoped milestone: finish the public Coconala package

The repository and `skills/earn/gig/` tree are already public on
`Daisuke134/life-manager` under the repository MIT licence. Publication is not the
remaining work. The current milestone is complete when a third party can inspect and
validate this package without this seller's private checkout, credentials, customer data,
or runtime state.

The public product principle is **fast, cheap, accurate, and minimal-human-loop**. Human work is
front-loaded into one guided setup session. Before any 24/7 lane starts, the installer collects and
completes every marketplace identity, SMS, eKYC, bank and consent step required for uninterrupted
selling and bank payout. After activation, ordinary operation asks no questions and waits for no
owner approval. The installer and loops own dependency installation, permitted signup/login automation,
mailbox verification, capability discovery, listing construction, pricing research, application
selection, negotiation, estimates, production, validation and delivery. They must not turn any
of those responsibilities into an owner questionnaire or approval queue. The four independent
lanes then run in parallel. Apply finds and submits only work that a concrete preflight proves
the installed system can deliver; Negotiate answers buyers and returns estimates; Paid builds,
verifies and delivers paid work; Storefront creates, measures and improves listings. Revenue
claims come only from official marketplace/payment readback.
The public package must not promise guaranteed income or describe unverified activity as
revenue. Owner notifications use a provider adapter; the distributable default is email,
not this operator's Telegram identity.

### Target one-session onboarding contract

The public command is `./install.sh coconala`. One interactive setup session completes all required
owner input before starting the loops. The wizard asks only for facts the official marketplace or
bank rail requires; it never asks the owner to describe skills, choose categories, write listings,
set prices, approve applications, approve replies, approve estimates, or approve deliveries.

1. Inspect the device and install or configure the declared runtime, model route, browser, email
   adapter, four lane jobs and release watcher.
2. Collect the notification/registration email, create or recover exactly one Coconala account with
   the signup/login skill or CLI, and consume email verification through the mailbox adapter. Never
   create a second account when one already exists.
3. In the same setup session, complete the official seller-information form (name/furigana, address,
   birth date and gender), mobile-number SMS verification, required terms/consents, eKYC document and
   face capture, and matching domestic bank-account registration. Sensitive values remain only on
   official surfaces or in the minimum private local credential store; documents, OTPs and bank
   details are never committed, logged, placed in model prompts or sent in reports.
4. Discover executable capabilities from installed tools and prove them with a bounded local
   preflight. Import any existing official listings and history. When the account is new, build the
   initial sellable listing, price, scope, FAQ and assets from verified capabilities and observed
   marketplace demand. Unknown capability fails closed; it does not become a human question.
5. Verify before activation that account/session, seller information, SMS, eKYC and payout account
   are accepted by the official site. Invoice registration remains optional and is not invented as a
   setup requirement.
6. Activate Apply, Negotiate, Storefront and Submission plus their browser/release owners, then
   report official receipts and bank-payout state to the configured email. Ordinary operation has no
   approval gate. Login expiry uses autonomous session recovery; if the marketplace later introduces
   a new non-delegable identity ceremony, the loop reports the exact blocker without pretending to
   be 24/7 complete.

The onboarding acceptance is not “the installer exited zero.” From a clean Mac and one setup
session, it must finish every current official prerequisite, reach four loaded 24/7 owners, establish
a truthful storefront, and eventually produce the four natural official business receipts plus a
real bank-arrival receipt without copying this operator's account, capability bundle, state or
credentials. Coconala balance is not bank income.

## Execution order to end

The first unfinished item is always the first failed live lane, not the first planned feature.
The current product priority is **coverage first, Negotiate latency second, Paid quality over
latency**. Apply must submit every currently eligible opportunity without omissions or duplicates.
Negotiate must account for every buyer-authored message, reply to every actionable one quickly, and
send an estimate exactly once only after the buyer has requested it and scope/price/delivery terms
are sufficiently settled. Submission/Paid is intentionally not accelerated: preserve the existing
builder → fresh reviewer → revision loop → quality gate → one official delivery path. Its deadline is
the accepted buyer deadline, not the Negotiate response SLO.
The order to the end is:

1. **Operating headroom is a 1 GiB last-resort guard, not a 10 GiB availability gate.** The lane's
   bounded evidence GC runs on every admitted wake. The guard only refuses a new allocation below
   1 GiB, where browser and SQLite writes face direct corruption risk; ordinary disk pressure does
   not stop earning work.
2. **Apply current production behavior is complete.** Natural pass
   `gig-apply-direct-1787217964823259000-24476` finished `ok` through immutable release
   `8d5fb3bfd`; its parent and planner runner resolved to that same SHA. It observed 40 requests,
   submitted two and officially read back both with `failed: 0`: request `5223231` at ¥8,000 and
   request `5223204` at ¥8,000. It also terminally classified `5223143` as video/animation and
   `5223145` as physical/on-site. The loop finished naturally and was not stopped or killed. The
   three preceding passes ended
   `parent_failed_rc_2` because the temporary required `price_basis` field made the old parent and
   new planner schemas disagree; that field and all code-owned price replacement are deleted.
   The semantic planner's single `price_jpy` is now the send price, with an explicit buyer amount
   preserved and otherwise a roughly 20%-below-budget competitive price. A later 80-request pass
   selected eight current jobs and officially confirmed seven; its one browser failure remains
   durably retryable. Old pre-fix intents remain duplicate fences and reporting history, not a reason
   to replay stale proposals or delay current applications. The temporary historical replay path is
   deleted. → detailed evidence: section B.
   The live owner is not disabled: launchd evaluates it every 60 seconds and prevents overlapping
   Apply passes. Verified applications are designed to emit an immediate per-job Telegram report;
   the terminal pass summary is additional evidence, not the only report. The immediate reporter's
   outer process previously timed out after 90 seconds while its Telegram transport was allowed 180
   seconds. Slow sends were killed after `send_started` and became
   `executor_lost_after_send_start`. Release `1b72c4329` raises only the outer deadline to 240
   seconds. Missing application `5217848` was recovered through the real reporter with provider ACK
   `26036`; the following natural application `5223432` produced immediate ACK `26037`, official
   application readback and terminal summary `26038`. A new natural Apply parent is now pinned to
   immutable release `1b72c4329`. Telegram Web on this Mac currently presents its QR login screen,
   so provider receipts and the operator's device remain the readback sources until the user logs
   that browser in; production bot polling must never be stolen for readback.
3. **Negotiate is accelerated but not complete.** One continuous process probes every 30 seconds
   with two workers, so another lane no longer delays inbox observation. The exact-thread head
   preflight and stale-event rebind are deployed. Natural Manledge replies on thread `10104078`
   reached official readback as actions 338 and 340. The next buyer message accepted the bounded
   commitment, semantic action 342 selected a ¥9,000 single estimate, and estimate action 343
   durably retained the exact 100-listup/50-approach/four-day terms. The remaining defect is retry
   latency: a pre-click form failure superseded the current revision, then every retry paid for the
   same semantic judgement even though the immutable prior estimate intent and source inbox event
   were already durable. The current slice reuses that intent only when a fresh head-only official
   read proves the source inbox identity is unchanged; a changed head falls back to fresh semantic
   judgement. A live first click moved action 343 to `reconcile_pending`; its next pass exposed a
   second ordering defect where a new semantic candidate ran before delivery-unknown readback.
   Reconcile now exits directly through read-only official-card matching before any new estimate
   candidate, form or click. Completion still requires action 343's one official estimate-card readback and a
   durable disposition for every buyer-authored message: replied with official readback, estimate
   sent with official readback, intentionally no-send with a bounded policy reason, or still pending
   with an observable retry owner. Missing from the queue is never a valid disposition.
4. **Storefront observes but does not yet sell/mutate completely.** Its `e4337a2f` process reads 13
   official services and completes cleanly, but the current receipt remains `actionable: 0 /
   effect: 0 / readback: 0` with `no_executable_unfenced_mutation_contract`. Resolve one valid
   mutation contract and prove one official listing create/update readback.
5. **Submission (Paid/delivery) quality architecture is accepted; natural completion proof remains.**
   Do not shorten its cadence or split it merely for speed. Preserve independent production, fresh
   review, revision until the quality contract passes, and one fenced official delivery. Its process
   is alive.
   The latest receipt is `completed / observed: 3 / effect: 0 / readback: 2 / failed: 0 /
   pending: 1`. Prove a new natural paid order through validated artifact, one delivery
   effect, exact-room official readback and replay zero.
6. **Prove 24/7 control-plane durability.** Browser, Apply, Negotiate, Storefront and Paid must each
   survive process exit and start again from the immutable release. The current shell cannot read
   the launchd domain (`launchctl` returns 141, `Reentrancy avoided`), although browser CDP and new
   Apply, Negotiate, Storefront and Paid PIDs are simultaneously visible. Process presence is not
   durable registration
   proof; capture two successive natural starts per lane and a loaded-definition readback from a
   valid GUI launchd context.
7. **The code-level public-package gate is closed at `f90898caf`, but anyone-device acceptance is
   still open.** Exact-archive acceptance passes 194 package
   tests, compilation, four empty-HOME plist renders, gitleaks and the owner-ID/path denylist.
   The remote `main` now points to `e4337a2f`. A clean third-party/friend install must still prove
   no effect before authentication and one natural official receipt for each of the four lanes.
8. Finish the remaining product items in this file: **4 listing contract/product truth** →
   **2 stable paid-feedback identity and credential handling** → **5 storefront attribution** →
   **1 browser-major qualification** → **6 merge the already-pushed legacy-removal branch when its
   unrelated merge clears**.

The system is complete only when all four business outcomes have natural official receipts:
application, buyer reply/estimate, listing create/update, and paid delivery. A running process,
Telegram/email report, dry run, model response or local ledger row is not completion.

### Atomic remaining checklist

Execute top to bottom. A checked diagnostic is evidence, not lane completion.

#### A0. Stabilize release activation before more lane fixes

**Overview and evidence.** Immutable SHA releases are the correct rollback unit; the defect is that
each generated launchd plist embeds one release's absolute path. The plist on disk can name the new
SHA while launchd continues to own and respawn the previously loaded SHA, and control-plane error
`141 Reentrancy avoided` prevents a reliable reload. Capistrano's documented deployment structure
keeps immutable releases behind a single `current` symlink and changes that pointer only after a
successful deployment. Apple's launchd contract makes `ProgramArguments` part of the loaded job
definition. GitHub's deployment concurrency contract permits only one writer for one deployment
group. Apply those established patterns here; do not keep reloading SHA-specific job definitions.

**Acceptance criteria.** All business-lane launchd definitions point through one stable `current`
path, never to `~/gig/releases/life-manager/<sha>/...`. A validated deployment atomically changes one
`current` pointer after verifying that its target is inside the release root and has the expected
lane code. Only the release controller (the watcher or an explicit activation using the same code)
may publish the pointer, under one deployment lock. Publishing does not bootout,
bootstrap, unload or reload the four business jobs. Rollback is the same pointer operation to the
last known-good release. Cleanup retains current and previous releases and never removes a release
referenced by the pointer or a live process. Two successive natural starts of every lane must resolve
the desired SHA, and no old SHA may respawn afterward.

**As-is → to-be.** As-is is `launchd plist -> immutable SHA entrypoint`, which couples job ownership
to deployment and creates two competing truths (disk plist versus launchd's loaded definition).
To-be is `fixed launchd plist -> atomic current pointer -> immutable SHA entrypoint`.
There is one repository (`life-manager` main), one release publisher, one active pointer and bounded
rollback releases; old checkouts and branches are not runtime owners.

**Verification matrix.** Successful publish: next natural wake records the new desired/resolved SHA.
Failed validation: pointer and running SHA remain unchanged. Concurrent publish attempts: one writer
wins and the other waits or exits without mutation. Rollback: next wake resolves the retained previous
SHA. Cleanup: current, previous and all live-process releases survive. Restart: each lane exits and is
started again by its unchanged launchd label. This is process/control-plane E2E; no UI or Maestro
coverage is required.

**Boundaries and execution.** Do not rewrite Apply, Negotiate, Storefront or Submission business
logic in this slice; do not delete active releases; do not change customer-facing effects. First add
the atomic validated publisher, then render all lane plists through its stable `current` path,
activate the fixed definitions once, capture two natural starts per lane, and only then garbage-collect
inactive releases/checkouts. This item supersedes further SHA-specific plist reload attempts.

**Current evidence.** Commits `9ff582293`, `11d122454` and `6e1ac2850` implement the atomic
validated `current` publisher, stable plist rendering, continuous-owner migration and a fail-closed
watcher when launchd readback is unavailable. The real watcher published
`current -> 6e1ac2850ea5...` and naturally started Negotiate, Storefront and Paid through `current`;
Storefront then produced a second natural `current` start and Paid produced a second natural receipt.
Commit `7f6e44d4f` restricts the exceptional migration path to an exact Apply PID whose latest durable
receipt is `status: operator_brake / effect: 0`. At the next real watcher tick, the release controller
published `current -> 7f6e44d4f...`, replaced the legacy `05b75fc29` definition once and read the
loaded Apply command back as `/current/.../gig_disk_guard.py`. The brake was then released. Apply's
first post-migration natural business start, PID 90319, resolved both `application_direct.py` and
`agent_runner.py` through `/current/`; it completed with 40 observed, four submitted, four official
readbacks, zero failed and three durable pending. The next natural start, PID 51887, again resolved
both entrypoints through `/current/`. The loaded plist contains only `/current/` paths and no live
process contains `05b75fc29`. Apply therefore joins Negotiate, Storefront and Paid on the stable
definition and A0 acceptance is closed.

#### A. Restore safe operating headroom

- [x] Record and retain the active/rollback releases, browser profile, live state and private config.
- [x] Remove one bounded set of inactive regenerable backups/installers/binaries; retain all Codex
  sessions. The first cleanup reached 10.051 GiB and passed the write/read probe.
- [x] Leave Git worktrees intact because the free-space gate no longer requires their removal.
- [x] Prune unused immutable gig releases while retaining `8fefa7a0`, `2ce5474f`, `b2abe2b00` and
  `f90898ca` for active/rollback use.
- [x] Inventory the whole Mac by independent lanes: containers/developer assets, media/documents and
  backups/app support. Docker/Colima is stopped with effectively zero payload; it is not the source.
- [x] Protect unique/active assets: about 1.96 GB of non-duplicate research CSVs, active Rust,
  Ollama, crawl4ai, Xcode/Simulator, Adobe, Codex/Claude, credentials, state, memory, dirty worktrees
  and customer artifacts.
- [x] Identify the current reclaim source: closed public-audit clones under `/private/tmp`
  (`life-manager-public-accept.*`, `life-manager-oss-rewrite.*`,
  `life-manager-rewrite-verify.*` and small acceptance HOME clones) occupy about 4.6 GiB; `lsof`
  reports zero open files for each measured directory.
- [x] Remove only the exact closed `/private/tmp` audit clones and their temporary HOME trees. Some
  immutable copies required adding owner-write permission inside those exact temp roots before
  deletion; no path outside the measured roots was touched.
- [x] Remove the closed `/private/var/tmp/SpeechModelCache` files (1,432,680 KiB, no open files) and
  closed `/private/tmp/lbj` (162,404 KiB) instead of removing CommandLineTools or user data.
- [x] Use the tracked `scripts/verify-fresh-clone.sh` entrypoint for public clone audits. Its EXIT
  cleanup now restores owner-write permission inside its exact temporary root before removal, so
  immutable release copies cannot strand the clone. Ad-hoc audit clone commands are not accepted.
- [x] Add `scripts/gig_disk_guard.py` before browser/SQLite/evidence work in Apply, Negotiate,
  Storefront and Paid. Below 10,485,760 KiB it emits `state/disk-headroom.json` with
  `failed: 1 / effect: 0 / readback: 0` and skips the child; at the exact threshold it preserves
  the child argv and environment. It fails closed when free-space measurement is unavailable and
  never auto-deletes user files from a business lane. Focused guard coverage: 4 passed.
- [x] Read back 10,617,248 KiB and then 10,616,160 KiB free across separate samples; successfully
  write, fsync, read and remove a 4 KiB probe in the gig state filesystem.
- [x] Keep secondary candidates documented but untouched; the 1 GiB guard makes further deletion
  unnecessary:
  old diagnostics (~150 MiB), unselected CommandLineTools (~1.84 GiB after reference audit), and an
  inactive `skillopt` venv (~109 MiB). Do not delete installed apps or dirty worktree videos by size.

#### B. Restore Apply and prove one new application

- [x] Restore immediate per-application Telegram reporting. The parent reporter deadline was 90
  seconds while the inner provider deadline was 180 seconds, which killed valid slow sends and left
  them `delivery_unknown`. Release `1b72c4329` makes the parent outlive the transport at 240 seconds;
  its focused timeout/redrive suite passes 6/6. Known-missing application `5217848` was redriven once
  and provider-ACKed as `26036`. Natural application `5223432` then reached official history and
  immediate Telegram ACK `26037`; its pass summary followed as `26038`.
- [x] Preserve full eligible-set coverage on natural passes: every observed open request is
  either officially applied, already applied, or carries one bounded truthful ineligibility reason.
  Missing structured decisions, provider failures and candidate wedges stay durably retryable rather
  than disappearing from the denominator; a transient row does not stop later candidates or the lane.
  Pass `gig-apply-direct-1787203527469043000-43647` exposed four post-submit official-history
  navigation timeouts, including `5222409`. Their structured decisions were present; the Telegram
  formatter incorrectly called every transient failure a missing decision. Source now distinguishes
  decision failure from readback failure and retries official readback once on a fresh target without
  clicking submit again. Natural `current` pass
  `gig-apply-direct-1787210299529825000-90319` observed 40, submitted and officially read back four,
  failed zero and retained three confirmation-pending rows for the next pass. The next natural pass
  recovered `5222772` and `5222946` with official readback, but reported pending zero while durable
  v2 intent `5222911` remained `prepared / irreversible_attempt_started`. Current source now merges
  every such durable unresolved v2 intent into the terminal receipt only; phase-level traversal still
  uses the current snapshot, so historical reconciliation debt cannot suppress deeper exploration.
  Historical pre-fix intents remain visible as duplicate fences so they can never cause a blind
  second submission; they are not current work and do not suppress source traversal. Three passes on
  the temporary mixed price schema ended
  `parent_failed_rc_2`; they are failure evidence, not coverage proof. Natural fixed pass
  `gig-apply-direct-1787217964823259000-24476` then finished `ok` through release `8d5fb3bfd` with
  parent and planner pinned to the same SHA: 40 observed, two submitted, two officially read back
  and zero failed. A later 80-request pass selected eight current jobs, officially confirmed seven
  and retained one browser failure for automatic retry. This is the continuing production contract;
  replaying old proposals is not an Apply completion gate.
- [x] Restore semantic scope fidelity before another exhaustive pass. Request `5217691`
  (`発泡ウレタンで等身大の女性を製作したい`) had repeatedly been classified correctly as
  `physical_or_onsite`, but pass `gig-apply-direct-1787206162452874000-19745` re-planned it as
  `submit_required` and officially submitted ¥18,000. The official text asks for a Tokyo-resident
  sculptor to teach a life-size urethane build; the proposal improperly narrowed that into a remote
  written procedure. Do not implement a keyword gate. Commit `32c516870` instead requires the planner
  to compare the buyer's required outcome, means, place and participation with the proposal and forbids
  inventing a remote substitute. Physical work remains eligible when the buyer explicitly requests a
  digital design, drawing, data file, written guide or remote advice and no handling/presence is
  required. The first natural `current` pass selected digital social-reply work `5222771`, preserved
  its ¥27,000 decision and completed official history readback. In the same snapshot it classified
  request `5222807`, which requires residence in or frequent visits to the Ibaraki Rokko area, as
  `hard_prohibited / physical_or_onsite`. This proves both sides of the semantic boundary without a
  keyword gate. The earlier isolated canary timed out and is not used as acceptance evidence.
- [x] Preserve an official exact price through the whole commercial path. Request `5217126` explicitly
  requires a ¥15,000 proposal and its durable planner result correctly contained ¥15,000, but the
  final application decision replaced it with ¥27,000. Exact buyer price instructions outrank category
  normalization and must reach the form unchanged. The temporary `price_basis` schema is removed:
  it added a failure mode without adding information. The semantic planner now owns the single final
  `price_jpy`: preserve a buyer's explicit amount; otherwise choose roughly 20% below the budget cap
  without making delivery uneconomic. Code preserves that price and only the official form boundary
  may clamp it to a platform limit. Direct readback proves ¥15,000 remains ¥15,000. Apply resolves
  the planner-runner symlink once at pass start, so a later `current` publish cannot mix an old parent
  schema with a new planner. The repeatable price rewrite is fixed; replaying this single historical
  application is deliberately not required.
- [x] Preserve the deployed failure report and form recovery behavior. `5217126` had a structured
  proposal were present; execution failed with `cdp_Page.navigate_timeout_after_30s` at the browser
  boundary. The legacy `05b75fc29` formatter falsely reported “structured decision missing.” The
  current source distinguishes planner absence from navigation/readback failure and retries official
  readback without a blind second submit. Current natural passes report browser failures as browser
  failures and leave them durably retryable; the old misleading formatter is no longer executable.
- [x] Restore intent-planner availability without a code change. Pass
  `gig-apply-direct-1787199355888187000-44491` completed four Luna batches successfully and again
  produced official application readbacks; quota failure is no longer the active defect.
- [x] Project the minimum verified seller facts needed for application questions into the planner:
  derived current age band from private date of birth, engineering role/current status, verified
  enterprise AI-agent work, and shipped consumer products. Do not expose address, full birth date or
  unrelated private facts to the model. The source projection now emits only `20代` and `東京都`
  from candidate identity while reusing the existing professional-fact allowlist; compile and direct
  fragment readback pass. Live planner/application proof remains below.
- [x] Make `mandatory_attribute_fabrication` compare the requested answer with projected verified
  facts. A numbered field label such as `5 年代` is not evidence of required fabrication. Reject only
  when the listing requires a specific attribute value that conflicts with verified facts or cannot
  be answered truthfully. Source prompt inspection passes; live request `5222525` remains the proof.
- [x] Invalidate pre-fix ineligible decisions with cache schema v2 so the corrected planner actually
  re-evaluates `5222525` instead of suppressing it for the seven-day cache TTL.
- [x] Re-plan request `5222525` and prove it becomes an honest application answering all six requested
  fields, then obtain official submission readback and replay zero.
  Live pass `gig-apply-direct-1787202286379991000-66643` re-planned it as `submit_required`
  with the six truthful answers and obtained official applied-list readback (`missing_count=0`,
  `unresolved_count=0`). The commercial contract incorrectly replaced its grounded ¥2,000 planner
  price with a ¥90,000 category median; source is corrected to preserve the planner price when the
  official form exposes no numeric bounds. Following pass
  `gig-apply-direct-1787203334368728000-39509` observed `5222525` in `already_applied_ids` and omitted
  it from `request_details`, proving replay zero. Release `05b75fc29` then preserved every
  no-official-bounds planner price unchanged (11/11) instead of applying a category median. The
  already-submitted ¥90,000 offer is a one-off manual correction if desired; do not build an
  automated historical-offer editor for it.
- [x] Preserve per-request structured decisions durably before execution. Each completed planner
  batch writes its owned `attempt-01.result.json` before any effect; dropped IDs are projected as
  `planner_missing_request_ids` and retried, never converted into a terminal refusal. Live pass
  `gig-apply-direct-1787203527469043000-43647` preserves both batch artifacts before form execution.
- [x] Repair the post-confirmation CDP boundary exposed by request `5222490`: the valid ¥90,000
  proposal reached the official final `応募する` screen but returned as a candidate-owned wedge.
  Later official applied-history evidence proves the click succeeded and the original failure was
  lost readback, so no blind resend is needed.
- [x] Obtain exactly one official applied-history readback for `5222490`, then replay it and prove
  zero duplicate submission. Pass `gig-apply-direct-1787202286379991000-66643` recorded
  `missing_count=0` and `unresolved_count=0`; the following two snapshots contain it only in
  `already_applied_ids` and omit it from `request_details`.

- [x] Diagnose the current outage: recent passes end in `parent_failed_rc_2`; both intent-provider
  attempts report `transient_quota`, and another pass hits `cdp_Page.enable_timeout_after_30s`.
- [x] Recheck before changing production: the existing cheap Luna route returned successfully and
  the lane recovered naturally; do not add an unproven provider fallback.
- [x] Recheck the CDP boundary before changing production: one navigation timeout was isolated to
  one item while two other applications completed with official readback; no reconnect change is
  justified without a reproducible failing case.
- [x] Keep the loaded Apply release unchanged; no Apply-only release is needed for a non-code fix.
- [x] Read back a natural terminal full-source pass with `observed: 100 / failed: 0 / pending: 0`.
- [x] Read back two natural official applications with `submit_verified: true` and
  `applied_page_verified: true`.
- [x] Read back the following pass with 45 already-applied filters and zero application effects,
  proving replay creates no duplicate submission.

#### C. Close Addres88 and prove fast Negotiate

Coverage and speed are both hard gates. Every newly observed buyer-authored message receives one
durable action identity before semantic work. The producer keeps discovering while both consumers
are busy. A message may end only as official reply readback, official estimate readback, explicit
policy no-send, or owned pending retry; it may never disappear because another thread/model/browser
operation is slow. The product SLO is official reply readback within 30 minutes of the buyer's
message. Thirty-second polling is the operating mechanism, not a promise to send a reply every 30
seconds.

Source fix `da5e16627` now coalesces a changed buyer identity onto the current durable action and
selects the newest coalesced event for restart dispatch. Commit `c366586ac` additionally binds a
seller-last closure to the dispatch-time revision, so a newer coalesced buyer event cannot be
silently closed by stale work. `644db7d95`/`9aa6a506c` add the exact direct-thread head preflight
and URL/identity fence before semantic judgement. `650c8418f` bounds the normal candidates (Luna,
Claude, Hermes) to 40 seconds inside the 120-second route deadline; the configured local proxy gets
90 seconds only when it is preferred and present, while the route still retains fallback candidates.
`3ed2f3dee` makes Hermes' user-local executable visible under launchd. The loaded-definition and
natural readback gate remain open until the continuous owner runs this release and one authorized
action completes.

- [x] Stop the repeated `targeted_inbox_identity_changed` cycle by preflighting the exact official
  thread head before semantic judgement, then binding the targeted job to the latest buyer-authored
  event without paying for an obsolete event (`644db7d95`, `9aa6a506c`; live result now reaches
  semantic authorization instead of the stale-identity error).
- [x] Fence seller-last closure by dispatch-time action revision; a buyer event coalesced after the
  stale result remains pending and cannot be closed by that result (`c366586ac`, 49 concurrency
  tests pass).
- [x] Give Luna, Claude and Hermes explicit per-candidate timeout caps within the single 120-second
   deadline, and keep every reply-semantic candidate unable to call tools (`650c8418f`; focused
   route suite passes; Hermes launchd path is fixed in `3ed2f3dee`).
- [x] Add the machine-local loopback provider fallback inside the existing tool-less semantic
  route. `claude-direct` uses the private `~/.cli-proxy-api-key` only when the configured loopback
  flag is present and selects `gpt-5.3-codex-spark`; a live canary returned a schema-valid object
  in 12.5 seconds. The fallback adds no browser or send capability and is not itself an official
  reply receipt.
- [x] Tighten the semantic prompt's evidence boundary: after `cycle_start_message_id`, every
  effect-bearing evidence ID must come from a buyer message in that cycle; older buyer IDs are
  explicitly forbidden. The previous natural run was rejected safely as
  `semantic_title_evidence_invalid` for violating this boundary.
- [x] Prefer the configured loopback semantic proxy before the unavailable network Codex route,
  while retaining the other candidates as fallback. The real schema-boundary canary now selects
  `claude-direct / gpt-5.3-codex-spark` in one attempt (about 12 seconds); its conversation-sized
  input receives a 90-second candidate cap inside the existing 120-second route deadline instead
  of expiring at the old 40-second cap. No marketplace effect is part of this canary.
- [x] Assign every newly observed buyer-authored message to a durable observable owner. The
  continuous supervisor probes every 30 seconds, uses two workers, and now prioritizes targeted
  estimate and reply reconciliation before new semantic work.
- [x] Open and bind the official Addres88 conversation to thread `10099067`; action 276 is verified
  against the official thread URL and outgoing hash without a duplicate send.
- [x] Bind each latest buyer-authored identity to its exact official thread and classify reply,
  estimate, clarify or no-send. Inbox evidence now retains the bounded counterparty name, which
  corrected the earlier audit-only misidentification of Manledge as thread `10103980`; the official
  mapping is Manledge `10104078`, o8sume Studio `10103980`, seto_wardog `10104195`.
- [x] Send and read back one complete natural reply through the existing lane. Manledge action 338
  proposed 100 controllable list-up tasks and 50 approaches, separated buyer-dependent outcomes
  from guarantees, and reached official `replied` readback at 00:19 with no duplicate effect.
- [x] Send and read back an explicitly requested estimate through the existing lane. Addres88 action
  276 reached exact-thread official estimate readback; later purchased threads are handed to Paid
  and all unfinished Negotiate actions are closed without a resend.
- [ ] Treat a buyer's competing bid or desired ceiling as a semantic renegotiation signal. Choose a
  deliverable, platform-valid competitive price from the whole current cycle without a hard-coded
  discount, revise the existing pre-purchase estimate when needed, and require official readback of
  the revised amount. The Haru thread's manually revised and purchased ¥1,800 proposal is historical
  evidence only; the loop must demonstrate this behavior naturally on a future conversation.
- [x] When a buyer asks the seller to set a feasible commitment line, propose concrete controllable
  work volume from the current conversation and verified application instead of repeating the
  question. Separate controllable activity guarantees from outcome targets, then send the official
  estimate only after the buyer accepts the resulting scope, quantity, price and delivery terms.
  Manledge action 338 is the natural reply/readback proof; estimate-after-acceptance remains covered
  by the separate 30-minute end-to-end acceptance item below.
- [ ] Permit terminal no-send only for illegality, safety, deception, or truthful inability to
  deliver. Ordinary ambiguity or a broad request must receive a clarifying reply or a scoped offer;
  generic `対応できません` is not a valid escape disposition.
- [ ] Replay the event and prove zero duplicate replies and estimates.
- [ ] For a new natural actionable buyer message, prove official reply/estimate readback within 30
  minutes from the buyer's official message timestamp.

#### D. Make Storefront mutate real listings

- [x] Remove operator capability paths from public defaults and load them from the private install
  configuration via `GIG_STOREFRONT_CAPABILITY_EVIDENCE`.
- [ ] Activate `f90898caf` or a descendant for the loaded Storefront job, then read back the loaded
  environment with two configured evidence paths without exposing their values.
- [x] Reconcile the sellable product truth before any mutation: the private 4313386 contract now
  binds to the latest official version `3c862a33…`, and the official seller form reads back both
  paid options (¥3,000 and ¥5,000). The natural pass at 2026-08-19 23:22 JST reports
  `stale_listing_contracts=[]` across all 13 observed services; no option is quoted from a stale
  contract.
- [x] Delete the unused listing-envelope protocol instead of exposing a half-built consumer;
  `storefront_direct.py` no longer writes or reports envelopes/ACK state (24 focused tests pass).
- [ ] Produce one valid, scoped, unfenced create/update mutation contract.
- [ ] Execute exactly one official listing create/update and read back the resulting live listing.
- [ ] Replay it and prove zero duplicate or wrong-service mutations.

#### E. Prove natural Paid delivery

**Accepted architecture — do not optimize Paid for lower latency.** A production worker builds the
buyer-requested artifact, a fresh reviewer checks it independently, the worker incorporates review
findings and repeats until the quality gate passes, and only then does the delivery owner perform one
fenced official submission with exact-room readback. Speed changes that reduce review independence,
iteration depth, artifact validation or duplicate-effect protection are regressions. Paid is complete
when it meets the agreed buyer deadline with quality and official delivery proof, not when it matches
Negotiate's reply time.

- [x] Recheck the natural order boundary: the latest official orders pass observed 3 open cards,
  read back 2 already-owned/deduplicated states, and left 1 pending with `failed=0`. The pending
  room is an existing revision/owner-decision state, not a new artifact that can be safely built
  or delivered from the current contract; no delivery effect is claimed.
- [x] Give paid feedback/delivery a stable order/message identity independent of the capture window.
  The collector now merges the current talkroom capture with the append-only official
  message ledger before choosing the seller-attachment boundary. New paid cycles record
  `feedback_identity_sha256` plus opaque buyer `feedback_message_identities`; that digest
  excludes capture time, local paths, byte-download success, and display-size guesses.
  Legacy sidecars keep their old digest while the request text is unchanged, so an already
  accepted artifact is not rebuilt during rollout. New or changed requests use the stable
  identity digest. `py_compile` passes for the collector, paid lane, and context packet.
- [x] Complete credential handling and email-first owner notification without public operator
  identity or secrets. Marketplace credentials remain in the private browser/session vault;
  owner reports use `telegram_report.OpenClawTelegramTransport` → `owner_notify` and sendmail
  when `GIG_NOTIFY_EMAIL` is configured, with Telegram only as the explicit fallback. This
  machine leaves email unset, so its latest Paid report is `delivery_unknown` on the fallback;
  that is notification transport state, not paid-delivery proof.
- [ ] Detect one new natural paid order from official state.
- [ ] Build its requested artifact from the accepted scope.
- [ ] Validate the artifact before delivery.
- [ ] Deliver it exactly once.
- [ ] Read the delivery back in the exact official room and prove replay creates no second delivery.

#### F. Prove four-lane 24/7 control-plane durability

- [x] Make release watching fail closed when `launchctl print` returns macOS
  `141 Reentrancy avoided`: the watcher now checks the lane's real script process and leaves a
  busy Apply/Storefront/Paid pass untouched instead of treating it as idle and booting it out.
- [x] Extend that fence to the continuous Negotiate owner: when the launchd control plane cannot
  be read, a live reply-detector process is kept in place instead of being booted out for a
  reload. The new release stays on disk and is picked up after a natural owner gap.
- [ ] Restore a valid GUI launchd readback without restarting or killing macOS base services.
- [ ] Read back loaded definitions for the browser, Apply, Negotiate, Storefront, Paid and watcher;
  each must point to the intended immutable release and private environment.
- [ ] Prove each lane has its own overlap fence while all four independent lanes can run in parallel.
- [ ] Capture two successive natural starts for each lane.
- [ ] Prove each lane recovers from an isolated process exit without killing shared browser or OS
  services.
- [ ] At the next natural login/reboot or an explicitly approved maintenance window, prove automatic
  persistence and repeat the loaded-definition readback.
- [ ] Keep reports receipt-based: no process PID, local ledger or notification counts as a business
  effect.

#### G. Prove the OSS package for another owner

- [x] Remove known operator IDs, private payloads and absolute operator paths from the distributable
  tree and pass the exact `f90898caf` public acceptance.
- [x] Provide email-first notification plus documented install, status, upgrade and uninstall.
- [ ] Add the public `./install.sh coconala` entrypoint and one-session wizard. Before activation it
  completes registration/recovery, seller information, SMS, eKYC, bank registration and all current
  mandatory official consents; no ordinary setup prompt may appear after lane activation.
- [ ] Add the local mailbox adapter and permitted Coconala signup/login skill/CLI path so account
  creation, session recovery and email verification do not become recurring human tasks. Preserve
  platform-mandated CAPTCHA, passkey, terms and identity ceremonies as explicit resumable exceptions.
- [ ] Replace the private capability-bundle onboarding requirement with automatic installed-tool
  discovery, bounded production preflights, official listing import and new-account storefront
  generation. Unknown capability must fail closed without asking the owner what they can do.
- [ ] Perform a fresh third-party/friend install through one continuous setup session; do not copy
  this operator's marketplace account, configuration, capability bundle, state or credentials.
- [ ] Prove the clean install causes no marketplace effect before its own account/session is
  authoritatively established.
- [ ] Prove the installer starts all four independent owners and the release watcher, and that each
  survives two process exits plus a login/reboot lifecycle.
- [ ] Prove all four lanes with the same four natural official receipts: application, buyer
  reply/estimate, listing create/update, and paid delivery; each must also replay with zero duplicate
  effect.
- [ ] Before activation, read back approved eKYC and a matching domestic payout account from the
  official site. Then prove the first bank withdrawal receives the money without another setup step,
  and stores neither documents nor bank details in the public checkout, logs, prompts or reports.
- [ ] Keep README and reports explicit that income is not guaranteed and revenue exists only after
  official payment readback.

#### H. Remaining bounded design/merge work

- [ ] Item 4: finish listing-contract/product truth and its real consumer after the Storefront proof.
- [ ] Item 2: finish stable paid digest identity and credential handling after the Paid proof.
- [ ] Item 5: record storefront attribution from official facts captured during Negotiate instead of
  relying on buyers pasting listing URLs.
- [ ] Item 1: qualify the current CloakBrowser major against the real marketplace before upgrading it.
- [ ] Item 6: merge the already-pushed profitable-claude removal branch after the unrelated upstream
  merge clears, and verify no Coconala loop remains there.

The public-package regression gate remains:

1. Audit the tracked `skills/earn/gig/` tree and its reachable Git history for credentials,
   customer content, account identifiers, absolute owner paths, and committed runtime evidence.
   Remove or redact any public-data violation before continuing.
   **IN PROGRESS:** allowlist-free current-tree gitleaks and PII-shape scans are clean, but the
   semantic audit found tracked seller storefront ids/profile/contracts/assets. Reachable history
   also contains the real customer messages, delivery files, attachment/account paths and operator
   address introduced by `944ca1fc1` and only deleted—not purged—by `478b8a1b2`. The seller bundle
   now lives under the configured private root, passes the pre-browser bundle check, and launchd
   reads that root back. Public source no longer carries the seller contracts/assets or real service
   IDs, and the repository fallback is inert. Next, purge the already-deleted customer artifacts and
   removed seller bundle from reachable public history. **DONE:** the five affected public heads
   were rewritten with force-with-lease after a local recovery bundle was created; the 38 private
   paths and known owner/service identifiers are absent from their reachable history. Coconala-only
   historical gitleaks findings are zero.
2. From a fresh clone of public `main`, run the package's non-mutating tests and configuration /
   plist generation using only documented local configuration. Do not reuse this machine's
   private state as proof of portability.
   **DONE:** public commit `c5eeefce4d568fd4c8236ed49e32c1249e1c3750` compiles the changed runtime,
   renders all launchd plists with an empty temporary HOME, sends through the email adapter using a
   local no-op sendmail executable, and passes the package current-tree gitleaks scan. No private
   install file existed in that HOME. Broad pytest was intentionally omitted per operator direction.
3. Make `README.md` match that clean-clone evidence: exact dependencies, local secret/state
   boundaries, install, status, upgrade and uninstall steps. Every documented command must be
   exercised from the fresh clone.
   **DONE:** README documents the private Storefront boundary, exact Python imports, 30-second
   two-worker Negotiate runtime, email-first owner reports, install/status/upgrade/uninstall and
   non-mutating plist generation.
4. Re-run the public-tree audit and clean-clone acceptance, then record the exact commit and
   evidence here. That closes this milestone. Items 0b, 1, 2, 4, 5 and 6 remain product/runtime
   work and do not block publishing the package unless the audit finds private data in them.
   **DONE:** exact public tree `f90898caf` passes 194 package tests, four-lane compilation,
   four non-loading dry-run plists from an empty HOME, current-tree gitleaks, the PII-shape scan,
   and the known owner-ID/absolute-owner-path denylist. The final audit found one real capability
   project ID still embedded in Storefront defaults; that default is now empty and the operator's
   evidence paths enter only through `GIG_STOREFRONT_CAPABILITY_EVIDENCE` or the existing repeatable
   CLI option. The public Coconala package milestone is closed.

---

## 0a. ~~The apply lane refuses 35% of the board for work it can actually do~~ — WRONG, CLOSED

**I argued this and the seller corrected it: the loop took video editing work once and
delivered it badly. It does not do that work again.** `video_or_animation` stays exactly as it
is, and so do the other six classes. There is no lever here.

The mistake is worth keeping written down, because it is easy to make again: I reasoned from
"this machine has Remotion, reelclaw, monk-factory, so it edits video" to "it can take video
editing jobs". Owning the tools is not the same as delivering an edit a paying client accepts,
and the only evidence that settles it is what happened when it was tried. I had the refusal
counts and no delivery outcomes, and treated the counts as the whole story.

So the honest reading of the numbers below is the opposite of what I wrote: **apply submitting
nothing is not a system problem to be unlocked. Six of seven classes are correct, and the
seventh is correct too.** The board genuinely does not have much this seller can do well, and
the remaining lever is on the storefront and negotiate side — being faster and clearer on the
work that does fit — not on widening what gets accepted.

Fresh production readback confirms the same conclusion. The durable application ledger has
632 `status: applied` rows. Its newest successful row has both `submit_verified: true` and
`applied_page_verified: true`. The latest full pass observes 117 official postings and reports
`actionable/effect/readback/failed/pending = 0/0/0/0/0`; zero is an exhausted eligible set, not
a broken submit path.

Request `5220025` is a separate bounded case: a CDP navigation timeout produced one transient
submission failure and the existing three-strike fence put it into the 48-hour wedge quarantine.
That safety stop does not justify changing Apply's filters or submit path. Release it only through
the existing official-absence readback workflow; unknown submission state is not permission to
retry a potentially duplicate priced proposal.

### The measurement, kept because it is still the map of the board

Measured on `~/gig/b2-ineligible-cache.json`: 249 cached
ineligible postings, and **every one of them is `hard_prohibited`**. Not one was turned down for
being unwinnable, mispriced or outside the seller's skill. Every refusal is a policy class this
loop applies to itself:

| count | class |
|---:|---|
| **88** | `video_or_animation` |
| 55 | `physical_or_onsite` |
| 39 | `mandatory_human_presence` |
| 37 | `mandatory_attribute_fabrication` |
| 21 | `explicit_ai_prohibition` |
| 8 | `missing_legal_qualification` |
| 1 | `illegal_or_unsafe` |

All seven are correct and stay. You cannot go somewhere and assemble a thing, appear on camera,
hold a licence you do not hold, claim a history you do not have, or take work from someone who
wrote "no AI" — and video editing was tried and delivered badly, which is the same answer
arrived at the expensive way.

What the numbers do tell you is the shape of the board: roughly a third of what gets posted is
video work this seller will not take, another fifth needs a body in a room, and the rest is
mostly presence, honesty and licensing. The postings that fit are a thin slice, and the way to
earn more from them is to be first and clearest on that slice — which is items 0b, 3, 4 and 5,
not a wider filter.

## 0b. Negotiate misses the five-minute reply target because its own pass is too long

The previous diagnosis here was wrong. Change detection is working, and the four lanes are
already independent launchd jobs that can run concurrently. They share one logged-in Chromium,
but each owns a distinct target or BrowserContext; there is no global lock serializing all four.
Production also showed Apply and Negotiate running at the same time under different PIDs.

The measured incident is buyer message `2026-08-19 13:40:23 JST` to official seller readback at
`13:50:36`, or **10 minutes 13 seconds**. The pass that snapshotted at `13:39:14` necessarily
missed the message. The next Negotiate pass started at `13:46:21`, discovered it in its
`13:46:22` snapshot, completed the four-page/~118-thread collection at `13:50:24`, then sent and
read back the reply at `13:50:36`. The delay is inside Negotiate's own full collection before
effect, not another lane holding its browser.

Changing `StartInterval` alone cannot guarantee speed because launchd does not start another
instance of the same job while its previous pass is still running. The fix must preserve the
four existing parallel lanes and make each lane maximize its own throughput: prioritize fresh
incremental work before full reconciliation, claim effects by thread/order/listing/application
to prevent duplicates, and begin the next same-lane wake immediately after completion. For
Negotiate, acceptance is official send/readback within five minutes of a buyer message under a
normal healthy session, with the measured operating target at two minutes or less. Full history
reconciliation continues after the urgent effect and must not block it.

**Speed slice 1 is deployed, but this item remains open.** Release `52cdc50e5` changes only the
Negotiate cadence and semantic route: launchd requests a wake every 30 seconds; reply semantic
judgement prefers one tool-disabled Luna-medium candidate, then uses the existing tool-disabled
Claude/Hermes provider candidates within a 120-second runner deadline when the preferred provider
is unavailable. The existing real-model authorization eval passed 6/6 cases,
the focused regression suite passed 8/8, an adversarial Codex invocation could not call shell or
execution tools, and fresh Sol review returned `ship`.

The first rollout exposed and then proved a migration failure: requiring the new runner profile
invalidated 117 otherwise-current receipts and reduced official estimate readback from six to
zero. Production was rolled back before retrying. The corrected rollout accepts only the legacy
`composition-agent` and current `reply-semantic-agent` profile names while retaining prompt,
schema, seller-facts, conversation, latest-message and official-context identity checks. Its
natural pass reports `classification_failed: 0`, `semantic_migration_pending: 0`,
`estimate_readback: 6`, and no duplicate effect.

**Selected architecture (ADR): one Negotiate launchd owner, one long-lived process, internal
producer–consumer concurrency.** A fast producer checks the newest inbox surface at most every
30 seconds and durably claims each new buyer-message identity in the existing
`connector-outbox.sqlite3` before model work. An in-process `asyncio.Queue` may dispatch those
already-durable identities, but it is never the source of truth. A bounded pool starts at two
consumer tasks. Each task owns its CDP page/target, opens one claimed thread, runs the existing
120-second-bounded semantic judgement, rechecks the exact head identity, refreshes the official
open-orders surface so paid-room ownership cannot come from a stale cache, performs at most one
authorized send, and requires official readback. Missing or invalid paid-order proof stops both
estimate and reply effects. A lower-priority reconciler retains the full four-page audit but
yields whenever urgent claimed work exists. Restart resumes durable pending work; a thread/message
claim prevents duplicate effects.

This is still one business lane and one supervised process. It does not add a second observer
service, fifth lane, another agent, database or durable queue. Fully sequential collection before
effect is rejected because model latency blocks discovery. Two independent services are rejected
at the current single-account scale because their lifecycle and cross-process ownership add cost
without improving the required outcome. The primary-source basis is Python's
[`asyncio.Queue`](https://docs.python.org/3/library/asyncio-queue.html) — “distribute workload
between several concurrent tasks”; Playwright
[`Pages`](https://playwright.dev/docs/pages) — “Each page behaves like a focused, active page”;
and Azure's
[`Competing Consumers`](https://learn.microsoft.com/en-us/azure/architecture/patterns/competing-consumers)
— long-running processing does not prevent other consumers from processing concurrently. The
abandoned two-process observer draft was never committed or pushed. A stale production plist did,
however, still point at the absent `reply_observer.py`: launchd ran it 63 times, every run exited
with status 2 before browser or marketplace effect, and it was then booted out and moved
recoverably to Trash. The selected single-process architecture must not recreate that service.

The measured before value is **10 minutes 13 seconds**. The completion gate is not a configured
interval or a model timeout: it is a natural per-message timeline from buyer origin through
detection, judgement, click and official readback. Every actionable buyer message must complete
within five minutes under a healthy authenticated session, with an operating target of two minutes
or less. Explicit stop-contact/返信不要, terminal acknowledgements, duplicates and safety-blocked
messages are intentionally classified and recorded without sending. Until that live timeline
passes, the system may describe the 30-second wake request and 120-second semantic bound, but must
not publish an "after" reply speed or a five-minute guarantee. Tests must prove that a deliberately
slow semantic task does not block claiming a second message, two changed threads can progress
concurrently, restart resumes the durable claim, and replay produces zero duplicate sends. Final
acceptance is a natural buyer-origin → detection → judgement → click → official-readback receipt
within five minutes, with two minutes or less as the operating target.

The first two implementation slices are complete through `6f1c659ba`. The bounded head
collector durably claims a thread-bound message digest before semantics; the targeted worker
then binds the exact action, rechecks the current head, collects fresh complete Paid proof,
uses the shared normal/estimate effect path, and requires exact-thread official readback.
Focused regression is 32/32 and fresh Sol review is `SHIP`. This is not deployed and does not
close 0b: the next active slice is the prompt-only correction for the observed applied-scope
refusals, followed by the two-consumer supervisor and natural under-five-minute proof.

The prompt correction is deliberately not a new lane or subsystem. For a legal, platform-
permitted request inside a verified official application, Negotiate treats the application as
the seller's current commitment, answers capability clearly, and completes the requested next
step through the existing reply/estimate path. It still must not invent an unstated client,
portfolio item or result number. The observed Care Earth Mart refusal and SaaS LP reply are
mandatory regression cases.

That prompt-only slice is complete through `f97c12d37`. Deterministic semantic tests pass
10/10. Two real Luna evaluations also pass: Care Earth Mart now begins with `対応可能です`,
accepts the explicit August 20 15:00 selection-rough deadline separately from the August 21
final delivery, and asks no redundant question; SaaS/Wix confirms the JPY 27,000 applied scope
and states only the verified approximately 3% to 10% conversion result plus its actual design,
upper-first-view CTA and copy scope. Both reply audits have no unsupported claim or unanswered
question. The next active slice is the two-consumer supervisor; 0b remains open until natural
official under-five-minute readback passes.

The two-consumer supervisor is deployed from immutable release `2ce5474f7`. Launchctl holds
one running KeepAlive process with exact argv `--continuous --poll-seconds 30 --workers 2`;
Apply, Paid and Storefront remain on their previous release. The producer now schedules from a
monotonic start deadline rather than sleeping after each probe. Four live bounded head probes
started at epoch seconds `1787141037`, `1787141067`, `1787141097` and `1787141127` — exactly
30/30/30 seconds apart — retained only message digests, and produced no new stderr. A probe that
overruns its deadline may trigger one immediate recovery pass, then resets to a full poll interval;
the exact-duration boundary is not treated as an overrun.
No unread buyer message existed during this observation, so the natural buyer-origin → official
readback latency gate is still pending and no after-speed claim is made.

The clean-public-package rollout was then exercised with all four launchd owners live at once.
Apply observed 40 postings and produced one officially read-back application from two actionable
rows; the other row remained unconfirmed and was safely counted failed rather than duplicated.
Storefront read 13 official listings and completed with no effect after the confirmed-gallery
readback stopped requiring deleted historical asset bytes. Negotiate completed repeatedly with
121 threads, six required estimates, six official estimate readbacks, zero estimate failures and
zero pending work. Paid observed three rooms, retained two owner reservations, produced two
readbacks and zero failures; its one pending room is the already-documented non-waiting case.
Apply, Storefront and the long-lived Negotiate supervisor were simultaneously visible under
different PIDs while Paid completed its own pass. This closes four-lane liveness and isolation;
only the natural new-unread under-five-minute latency sample remains open.

---

## 1. ~~The browser step had no source~~ — RESOLVED, with one thing left to qualify

The binary comes from [CloakBrowser](https://github.com/CloakHQ/CloakBrowser)
(`pip install cloakbrowser`, PyPI `cloakbrowser`): the wrapper downloads its patched
Chromium on first use and caches it under `~/.cloakbrowser/chromium-<version>/`, which
is exactly the layout `scripts/launch_gig_browser.sh` globs for, and `--fingerprint` is
that build's flag. The install step is now written up in the README.

**Left open:** `launch_gig_browser.sh` takes the highest installed version, and its TLS
compatibility switch is bounded to Chromium 145 and 146. A fresh install today gets
whatever CloakBrowser ships now, which may be outside that range — and outside it the
switch is silently not applied, which is the `ERR_TIMED_OUT`-while-curl-works failure the
script's own comment describes. Nobody has qualified a newer major. Until someone does,
a new machine may install a browser that cannot reach the site, and the loop will look
broken for a reason that has nothing to do with the loop.

Do not widen the `145|146` case on faith. Qualify it against the real site, on the real
network path, and record what you measured.

---

## 2. One paid order is stuck on an unstable feedback digest

**Blocks:** the lane finishing an order by itself. Measured 2026-08-19: the buyer on this
order is **not** waiting — their two newest messages confirm the work and say they are done
for the day. The lane holding still is currently the correct outcome, for the wrong reason.

`active_feedback_cycle.buyer_feedback_sha256` is pinned to one value while the live
`feedback_sha256` is another, so `_remote_revision_required()` stays false and the cycle
never advances.

**Root cause: the digest describes a window that is defined to move.**
`persist_latest_paid_buyer_reply()` (`scripts/coconala_queue_snapshot.py:1532`) sets the
revision boundary to `latest_seller_attachment` — the index of the last seller message
carrying an attachment — and `feedback_text` is every buyer message after it. That index is
computed over `talkroom["messages"]`, which is only what the page currently renders;
Coconala lazy-loads older messages on scroll. So the same conversation produces a different
boundary, a different concatenation and a different digest from one poll to the next. The
function already defends the *delivery* consequence of that capture variance, at length, in
its own comment — but not this one. Pinning a hash of a growing, capture-dependent
concatenation means the pin can essentially never match again.

Two further facts to design against, both measured on the live file:
- `feedback_sha256` is **not** the SHA-256 of `feedback_text` in the same file, nor of the
  accumulated rows, nor of their joined hashes. Whatever it digests is not reconstructible
  from what is stored, which makes the mismatch unauditable after the fact.
- Every accumulated row already carries its own stable per-message `sha256`. A cycle that
  named the specific messages it answers, rather than a rolling window, would be stable by
  construction.

`_feedback_cycle_patch()` in `scripts/delivery_project.py:144` is wired but guarded at
`scripts/paid_direct.py` by `if not (root/"state.json").is_file()`, so it only fires during a
project's first bootstrap. **Do not loosen that guard while the digest moves with the capture
window** — the concatenation currently opens with a request the customer already had answered,
and a builder acting on it would redo resolved work on a live customer site.

**Related, and worse:** the buyer text stored under `requirements/` includes a customer's
WordPress admin username and password in plain text, and that text is what gets packed for the
model. Neither the file nor the packet treats it as a credential. That needs its own decision
before anything widens what reads this file.

---

## 3. ~~The estimate lane refuses one thread forever — the counts disagree~~ — CLOSED

Commit `9b3572533` removes the false DOM/mapping count equality from both category waits while
retaining the control-enabled, row-visible, non-empty-option and exact-label requirements. The
installed immutable release `056ee1f1c...` contains that commit. Fresh natural Negotiate passes
now complete with `estimate_required: 6`, `estimate_readback: 6`, and `estimate_failed: 0`; the
former 55-of-56 pass failure is no longer present.

Fresh Sol/High read-only review returned `ship`. It found one fail-open edge before that verdict:
an absent category-type row produced `row_hidden: false`, so the required branch did not prove
that the row existed. The follow-up adds `row_present: !!row` and requires it in both category
wait paths. A targeted regression test failed before that production change and now passes for
both paths while preserving the optional disabled+hidden+zero-option shape and exact-one-label
guard. Final evidence: targeted tests 2/2, Python compilation and `git diff --check` pass; the
full gig suite is 124 passed with one known unrelated stale Storefront fixture failure. The
reviewer's residual risk is that the new regression is a generated-JavaScript contract test,
not a browser execution against a half-rendered DOM. The change only strengthens rejection when
the row is absent; the prior natural-run evidence remains the proof for the normal live path.

**Historical root cause:** estimate revenue on one thread was blocked. It was not a race, and
waiting longer could not help.

`dependent_category_types_not_loaded` sounded like a slow page and is not: the same thread
fails every pass while five siblings submit. The failure now records what it saw, and it says:

```json
{"mapping_loaded": true, "sub_value": "644", "mapping_has_sub": true,
 "mapped_option_count": 3, "control_disabled": false, "row_hidden": false,
 "enabled_option_count": 6}
```

The `required` branch in `scripts/coconala_estimate_browser.py` demands
`enabled_option_count === mapped_option_count`. The page offers **six** selectable
category-type options while `data-master-category-types` maps **three** for that
sub-category, so neither the optional nor the required shape ever holds and the five-second
poll always expires.

**Severity was understated.** This is not one lost estimate: **55 of the last 56 negotiate
passes report `status: failed`, and this thread is why.** One form that never satisfies the
contract marks the whole lane failed, every three minutes, all day.

I guessed the extra three were the previous sub-category's options left in the `<select>`. The
readback now carries the option list, and that guess is **wrong**:

```
sub_value 644   mapped 3   enabled 6
選択してください / サイト修正・更新代行 / バグ修正・不具合解消 /
Webサイトコンサル・集客支援 / サイト高速化・表示速度改善 /
お問い合わせ・各種フォーム作成 / サーバー設定・WPインストール
```

Those six are one coherent family — all website work. Nothing stale is mixed in. So the
`<select>` is right and the `data-master-category-types` blob is the one that disagrees, naming
three where the page offers six.

That inverts the fix. The contract asserts equality between the live DOM and a data attribute,
and treats a mismatch as "not loaded yet" — but the DOM is the authority for what a human could
select, and the mapping is a hint that is allowed to be behind. The properties actually worth
holding are the ones the next step already needs: the control is enabled, its row is visible,
and the intended label appears exactly once among the enabled options.

Dropping the count equality changes a lane that sends priced offers to buyers. Live readback
proves the operational result, but it does not replace the missing fresh adversarial review
named above.

---

## 4. `negotiate_context` can never become "ready" — CLOSED

**Blocks:** the negotiate lane answering a storefront inquiry with the offer it was made
against. Two independent causes, both proven from the live receipt.

**4a. The lane retires its own contracts by doing its job.**
`_load_listing_contracts()` (`scripts/storefront_direct.py:1691`) reads the hand-authored
contracts under `contracts/storefront/`, and each one is bound to one exact listing version:
if `service_version_sha256` no longer equals the live listing's, the contract is dropped as
stale. Editing listings is this lane's entire purpose, so **the lane invalidates its own
contracts**, and with them that listing's inquiry playbook, until a human re-authors the file.

There is exactly one hand-authored contract in the historical snapshot, and the live receipt at
that time showed it stale. The single storefront-origin inquiry on record was on that same
service, so its identity lookup found nothing and no envelope was written.

That was recorded in the wake row as `stale_listing_contracts` and never said out loud — the
report kept printing a healthy-looking active count beside it. It now prints the binding
breakage too.

**Resolution recorded 2026-08-19:** the private contract was re-authored against the current
official version and the next natural pass read back `stale_listing_contracts=[]`. The historical
pricing concern is therefore closed for the observed listing; no hash-only rebind was used.

**This is not a rebind, and rebinding it would be worse than leaving it stale.** Comparing the
hand-authored contract with the listing as last observed: five of six `offer` fields differed in
substance in that historical snapshot. The current official seller form now reads back the two
paid add-ons (¥3,000 for an extra macro, ¥5,000 for monthly maintenance), and the contract is
bound to the same observed listing version.

The product-truth decision is therefore closed. Any later price or copy change must again be
observed in the official seller form before its contract hash is advanced.

**4b. Nothing consumed an envelope. CLOSED by deletion.**
`negotiate_context` reports `ready` only when every context key is also present in
`negotiate-context-acks.jsonl` with `status: consumed`. That file has never been created, and
`storefront_direct.py` is the only file in the repository that names either it or
`inquiry-context-envelopes.jsonl` — which does exist on disk, written and then read by nobody.
The negotiate lane does not know this protocol exists, so even with 4a fixed the state stays
`missing` forever, and `missing` reads as a transient failure when it means "no consumer".

No repository consumer existed, so the unused half-protocol was removed from
`storefront_direct.py`: the envelope writer, ACK path, state-file touch, CLI flag, receipt field
and misleading report line are gone. Existing private state is left untouched; no data cleanup was
required. Storefront now reports only facts it actually owns, and Negotiate remains the sole owner
of buyer-thread context. Focused Storefront suite: 24 passed.

---

## 5. Storefront attribution depends on the buyer pasting a URL

**Blocks:** knowing which lane earns. Measured on `~/gig/storefront-direct/funnel-events.jsonl`:
of 111 inquiry events, **110 are `unknown` and 1 is `storefront`** — exactly the one that
carries a `service_id`. All 8 payment events are `unknown`.

The rule is in `_funnel_events()` (`scripts/storefront_direct.py:~636`): a conversation is
attributed to storefront only when a regex finds `coconala.com/services/<id>` **in the buyer's
own message text**, for exactly one of the seller's current listings. A buyer who opens an
inquiry from a listing page does not then paste that page's URL into their first message, so
the test almost never passes. It fired once in 111, and on the one listing whose contract is
also the stale one from item 4.

That is a proxy standing in for a fact the platform already knows: the talkroom belongs to a
service. `apply` attribution works precisely because it is not a proxy — the apply lane keeps
`applied.jsonl` and therefore knows which postings it answered. Storefront keeps no equivalent
record of which of its listings an inquiry arrived from.

Fixing it means recording that fact where it is observable — the negotiate lane already opens
every talkroom — rather than sharpening the regex. Note also that `source_status:
"latest_completed_log_noncanonical"` is narrower than it sounds: it labels only where the
*observed conversation count* came from, not the attribution. The attribution problem is the
regex, not the log.

---

## 6. Retire the old copy in the other checkout

The Coconala code that used to live in `profitable-claude` at `skills/gig-work/` no longer runs
anything: no loaded launchd job executes from it. Branch `chore/retire-gig-work` removes the
tree and updates that repository's registry, start-all, status, README and tests to match.

It is pushed and unmerged. That repository's working tree is mid-merge on unrelated work
(`skills/reddit/state/STATE.md` unmerged), so it cannot be committed to by anyone but the owner
of that merge. Merge it when that clears.

---

## Not on this list, and why

- **`test_storefront_direct.py::test_noop_...`** fails, and failed identically on the release
  that ran in production before any of this work. The pass now reaches a proposal path that
  opens a real CDP connection the test does not stub. It is a stale test, not a defect.
- **`前回比 閲覧 +0`** in the storefront report is correct. Coconala's analytics window ends the
  previous day (`2026/07/20–2026/08/18`, `complete: true`, coverage 13/13), so two passes on the
  same day read the same window and the true delta is zero.
- **apply submitting nothing for hours** is the board being exhausted, not a regression. Of ~64
  postings observed, 26 are already applied to, 27 are cached ineligible and 28 hit a prohibition.
  The judgement fields either side of the repository move are unchanged; only the
  already-applied and cached-ineligible counts grew, which is what they do.
