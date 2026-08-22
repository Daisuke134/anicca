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

1. **Operating headroom is a configurable 512 MiB last-resort guard, not an availability gate.** The lane's
   bounded evidence GC runs on every admitted wake. The guard only refuses a new allocation below
   512 MiB by default; `GIG_DISK_HEADROOM_KIB` may raise it per device. Ordinary disk pressure does
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
   candidate, form or click. Action 343 then reached `replied` revision 2: official thread
   `10104078`, verified intent/card hash `267da3020abb...`, seller timestamp `1787242065`, and
   intent state `verified`. The ¥9,000 estimate path is therefore closed. A later buyer purchase
   acknowledgement exposed `estimate_event_conflict`: an untouched stale estimate action blocked
   the newer normal message. Queue handoff now closes only a pending estimate with no intent/click,
   then atomically retries the newer buyer event; prepared or clicked estimates remain protected.
   The live loop closed action 344 with `nothing_to_say:buyer_message_after_estimate`, created action
   349 for the buyer's purchase acknowledgement, replied and officially read it back with matching
   intent/card hash `7100055b48c6...`; buyer-to-seller latency was about 11m26s, inside the 30-minute
   product SLO. The final old blocked action 304 still has the same buyer head; a fresh official
   head-only read now reports `sending_unavailable: false`, while its fixed exponential backoff
   would otherwise wait two hours. The continuous supervisor now probes only
   `submit_rejected_sending_unavailable` blocks and revives one immediately only when the exact
   source identity is unchanged and the official send-unavailable marker is explicitly false.
   The server still rejected action 304 despite that marker, so proof-triggered immediate revives
   stop after three attempts; later retries return to the durable exponential-backoff owner instead
   of burning sends every 30 seconds. A current 30-row inbox-head audit found all 30 identities
   durably bound: 29 have official-readback or intentional-no-send terminal dispositions; action
   304 is the sole nonterminal row, blocked after five official server rejections with its bounded
   backoff owner. No inbox identity is missing. The reporting gap came from the continuous runtime:
   its workers persisted results but never called the legacy per-wake Telegram adapter, so
   `reply_wake` created no row after report 7992 while the other lanes continued reporting. Every
   continuous worker result now enters the existing durable outbox: verified replies use the
   action/revision-keyed `reply_verified` path, while estimates, intentional no-send and blocked
   outcomes use the run-keyed `reply_wake` path. The five-minute reconciliation result uses that
   same path, so an idle but healthy inbox remains owner-observable. Business processing remains
   parallel; completed results enter one dedicated reporter queue so two workers cannot race the
   Telegram provider or spend their next-work capacity waiting for delivery. Stale work that loses
   its binding as `already_closed` is persisted but not presented as a buyer outcome. The real loop
   created new reports 9033 onward; reports 9036/9037/9038 reached provider ACKs 26441/26446/26445,
   proving owner delivery after the twelve-hour reporting gap. The later Manledge commitment-line
   question also closed naturally: action 351 replied with official readback in 2m08s. Its fresh
   order snapshot already contained the ¥9,000 purchased order, so the loop correctly replied
   without submitting a duplicate estimate. Estimate submission remains for agreed buyer intent
   only while no paid fence exists.
   Completion still requires a
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
   The latest receipt exposed `18169583=file_builder` before any builder evidence existed. Root
   cause: the source-census controller required all three hardcoded optional skills
   (`music-score-omr`, `buyma-work`, `ai-video-work`) even for an unrelated Illustrator/image
   order, while none exists on main. The controller now copies only approved skills actually
   present; absence of an unrelated skill no longer prevents the native-vision census or builder.
   The next natural pass proved that fix by running the real Sol file owner for `18169583`. It
   produced the PC/responsive Illustrator package, a valid ZIP, a 46-mapping source-correspondence
   receipt and matching package SHA256, then exposed the next controller boundary defect:
   `acceptance_delta` was a nonempty string because the owner prompt did not specify its JSON type,
   while validation accepts only a string array. The boundary now canonicalizes a nonempty string
   to a one-element array and the owner prompt explicitly requests that array contract. The next
   natural v2 owner produced the array correctly and exposed the adjacent status-vocabulary split:
   it wrote manifest `status: PASS` while the controller requires `status: ok`. The same boundary
   now canonicalizes that producer spelling and the prompt explicitly requires `ok`. Live fresh
   review then ran and correctly rejected a circular v2 source-correspondence proof. That same-pass
   revision exposed a controller handoff bug: the owner prompt rendered its existing trusted census
   as `None` because the census path was resolved only before the review finding existed. Census
   resolution now runs on every build/revision entry and reuses the trusted receipt without another
   model call. The v3 revision fixed real missing modifier classes but remained blocked because its
   owner had read the census before production and listed v2 as an input source. Review policy v18
   now enforces two ordered phases: raw-source-only artifact construction and hash finalization,
   followed by controller-census correspondence. Necessary wording overlap alone is not circular;
   pre-hash census/prior-candidate access is, and is a repairable `needs_revision` when raw sources
   are available. The live v18 re-review returned `needs_revision` exactly as designed and launched
   a v4 raw-source rebuild. That run proved the remaining architecture defect: a single owner still
   performs both production and post-hash correspondence; after opening the census it found missing
   copy, modified the same candidate and rehashed it, destroying the phase boundary. Prompt ordering
   is not sufficient isolation. The next slice must run production in a staging root containing only
   accumulated requirements and raw buyer sources, then copy the fixed artifact into the durable
   project and let a separate controller/reviewer process read the census. Live fresh
   Policy v19 implements that physical split: each production round receives a temporary staging
   root containing only requirements, raw buyer sources, non-proof context and state; macOS sandbox
   denies reads and writes to the durable project. Only artifact, acceptance and manifest are
   promoted. The producer is forbidden to create correspondence; the separate read-only reviewer
   receives the controller census and raw sources after the artifact hash is fixed and owns the
   exhaustive semantic/modifier comparison. The first natural v19 run re-reviewed v4 and rejected
   it before delivery: direct inspection found clipped/obscured copy across both PC and responsive
   artboards and proved that two buyer-supplied illustrations were loose package assets rather than
   used in either layout. The controller persisted the complete class-wide finding under policy v19
   and launched the exact next v5 producer from a temporary `paid-file-owner-*` staging root. That
   root contains requirements, raw buyer sources, non-proof context and state, but no controller
   census, prior candidate, review state, authorization or correspondence receipt. Live corrected
   v5 then passed the isolated owner's own artifact validator but exposed two controller handoff
   defects before promotion: relative manifest paths were resolved against the controller cwd, and
   the copied runner summary still pointed at its deleted temporary result. Promotion now resolves
   relative paths inside staging only and rewrites `result_path` to the copied durable evidence file;
   both fixes preserve the physical read fence and keep buyer-visible effect at zero on failure.
   The corrected v5 was promoted and independently reviewed, but the reviewer rejected incomplete
   source correspondence in both layouts: omitted/changed source copy and modifiers, missing
   testimonial illustrations/final CTA, and whole infographic images embedded instead of isolated
   supplied illustration regions. The isolated loop produced v6 from that class-wide finding; its
   hash-bound package and manifest promoted successfully, proving the handoff fixes. Fresh review
   rejected v6 before delivery because its SVG/PDF files were raster wrappers around repeated source
   PNG sections rather than editable vector reconstruction, and its responsive layout merely scaled
   the PC raster instead of reflowing it. The same live controller persisted that complete finding
   and launched isolated v7 production automatically. That run exposed an outer-boundary defect:
   the parent preparation subprocess still used the generic 35-minute step deadline even though
   the bounded file workflow permits three 60-minute production rounds plus three 30-minute fresh
   reviews. The parent therefore recorded `remote_resume` and exited while its v7 owner continued
   orphaned. File preparation now has a six-hour outer deadline, longer than every permitted inner
   round combined; other Paid steps keep the generic bounded timeout. A later non-orphaned v7 run
   reached fresh review and proved real editable vector reconstruction and responsive reflow, but
   was rejected before delivery: both layouts retained two wrong source phrases, omitted the full
   final CTA, FAQ chevrons and testimonial illustrations, used mismatched icon classes, and embedded
   both supplied marketing JPEGs whole instead of isolating the required illustration regions. The
   controller persisted the exhaustive finding and automatically started isolated v8 production.
   The isolated v8 producer then completed and promoted a hash-bound package whose own acceptance
   receipt is PASS: both layouts contain the complete source copy, final CTA, five FAQ chevrons,
   three testimonial illustrations and five isolated buyer-supplied illustration regions, with no
   whole source JPEG embedded. The separate fresh reviewer opened that durable package and verified
   its hash, archive, XML and extracted copy, but the old outer parent exited during the review
   before a final verdict. No buyer-visible delivery occurred (`effect: 0`). The active immutable
   release contains the six-hour file-preparation deadline; a direct launchd kickstart from the
   current GUI context remained rejected with `141 Reentrancy avoided`, but the next scheduled
   launchd wake naturally resumed the persisted v8 package through the real loop. The fresh reviewer
   rejected v8 before delivery after proving two remaining source-copy substitutions, one responsive
   right-edge clip, and bad crops in all five reused illustration assets. The controller persisted
   the complete class-wide finding and automatically launched isolated v9 production under the
   fixed six-hour parent. v9 completed, promoted a hash-bound package and passed its producer-side
   render/archive checks, including embedded assets and width-aware card wrapping. Its fresh
   reviewer then disproved that self-PASS while effect remained zero. Its final `needs_revision`
   finding covers every analogous instance in both layouts: three missing feature cards; shortened
   demand copy; altered risk/benefit/FAQ/testimonial/summary text; missing badges, chevrons, icons and
   final-CTA elements; unsupported sections; and false README dimensions. The controller persisted
   round 2 and automatically launched isolated v10 production under the same live parent. That
   parent remained alive past 35 minutes while still owning v10, directly proving that the old
   generic 35-minute outer timeout no longer terminates the file workflow. v10 fresh review, one
   delivery effect, exact-room official readback and replay zero remain to be proved.
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

#### Current cursor and non-skippable order

Operationally the four launchd lanes remain independent and may run concurrently, but development
completion has exactly one cursor and may not jump forward because a later lane has live customer
work. Apply remains live and is rechecked in the final four-lane audit. The current non-skippable
development order is **Paid/Submission → Negotiate → Storefront → four-lane durability → OSS
third-device acceptance**. A successful example, live PID, local ledger row, Telegram report or
partial readback never closes a lane while any unchecked acceptance item in that lane remains.

Current truth: Apply has a live verified application path but its final maximal-coverage/replay
receipt remains part of the four-lane audit. **Paid/Submission is the active development cursor**
because purchased orders are not reliably receiving context-complete artifacts. Negotiate remains
live independently but is not complete: total coverage, competitive repricing, bounded terminal
no-send, replay-zero and a new natural sub-30-minute official reply/estimate proof remain unchecked.

#### Remaining TODO snapshot — authoritative order to the end

Do not advance the development cursor until every unchecked item in the current stage has official
evidence. Independent production lanes continue running while development follows this order.

**Live handover state.** The loaded Paid owner uses an immutable release with up to eight independent
project workers. Its launchd environment ignores the shared preventive `disk-pressure.block` and
`disk-writers.stop` flags while retaining the 512 MiB last-resort guard and expiring operator brake.
The published Paid release is `227111b43c5ec0ed6527ee902faaa11063e419cb`. It includes the prior
`d24a9dbb3e86ce9df648965aac4aadcdf7bce56a` safety boundary, which removes all
`undeterminable`/review-exhaustion delivery authorization, requires the builder to copy the exact decision
asset contract, and preserves a failed staged candidate under private owner evidence before cleanup. The newer
release also reuses hash-verified saved buyer attachments instead of redownloading all six Haru files on every
readback. The existing Paid launchd job read back the immutable release, but these code paths are not yet
production-proved. The latest completed
natural receipt remains
`status=failed`, `observed=7`, `actionable=5`, `effect=0`, `readback=2`, `failed=5`, `pending=0`;
silent pending is now zero, but parallel artifact production therefore does not yet prove
parallel buyer delivery. X-post talkroom `18171850` remains the sole closed item in the current
four-client set: approved v1 has already been sent and officially read back with formal delivery OFF.
The natural owner pass violated the no-regeneration boundary before the durable non-PASS guard took effect:
review-article talkroom `18171890` changed from v4 to REVIEW_READY v5
`28199b8fb6479915d5ec372f3e57df83899f449a705ac7157dd9ad59867907d1`, and Manledge `18169985`
changed from acceptance-PASS v20 to REVIEW_READY v21
`b0588d9e2e99fd998896e611ddb52d61c98bacf56750b130e082580de5bd4c2e`. Do not regenerate either
artifact again; decide whether the truthful v5/v21 records may be preserved or whether the existing v4/v20
hashes must be restored without sending. The current failures are `18171890=file_non_delivery_disposition`
and `18169985=file_validation`. Haru `18169583` remains acceptance-PASS v31
`bceca32db8a9272330fd12798d44da06e14aab51e83e17d81e030aa37665d185` in
`BOUNDED_REVIEW_SHIP` round 4. An account-owner Coconala screenshot now proves the v31 filename was
buyer-visible at 05:30, but the buyer replied at 11:13 that the design had reverted again and asked
whether it had been sent without proper checking; the seller apologized at 11:47 and promised another
verified submission. The fresh reviewer had returned `undeterminable` because native Illustrator provenance
could not be proved, while calling the package otherwise useful, and the controller incorrectly converted
that verdict into shipment without proving retention of the buyer-approved latest design. The latest natural
owner pass now fails Haru closed at `file_validation`; it has neither resent v31 nor produced a proved
correction. Codex is the explicit incident lead for Haru: it must inspect the complete buyer attachment/message
sequence and candidate visually, decide what correction is truthful, and authorize only a reviewer-PASS
artifact. The existing Paid owner remains the sole browser/effect executor so the repair is durable and
replay-safe; do not create a manual browser shortcut or one-off Haru script. Neither the incorrect shipment
nor the apology is a successful Paid completion. The already-closed X room incorrectly re-entered `file_builder`, and room `18062411`
still fails `remote_resume`. Paid completion is therefore still one officially delivered/read-back artifact
out of four, not four.

The incident lead visually compared the saved buyer source `5372ec073081-image.png` with v31 and confirmed
the buyer's report: v31 reverted the designed heading rails, cards, diagrams and large comparison sections to
a sparse generic page. The natural owner then generated a claimed v32 correction, but its manifest renamed the
decision's required asset ids and failed `asset contract mismatch`; cleanup removed the temporary v32 ZIP before
independent visual inspection. This is not a review PASS and must not be reconstructed from the self-report.
The surviving v32 PC/responsive style previews were subsequently opened directly: unlike v31 they restore the
inquiry artwork, comparison table, special-vacant-house diagram and designed content hierarchy. They remain
insufficient for authorization because the package, editable AI files and exact asset contract no longer exist
for hash-bound inspection.

A later natural reconstruction attempt exposed the decisive lineage defect before any customer effect. The
Paid owner was instructed to revise rejected v31 and preserve everything not named by the latest finding, so it
again produced v31's card-based page hierarchy with the latest inquiry artwork added. Direct full-preview
comparison against durable v27, v29, v30 and v31 proves that v27 is the last artifact that preserves the
buyer-supplied base design's two-column heading rows, wide section rails, side-by-side illustration treatment,
horizontal process, FAQ, voices and summary composition. The buyer's messages after v27 requested only the
inquiry-section replacement and higher-resolution Illustrator output; they did not authorize a page-wide
redesign. Codex stopped only that isolated Haru builder before promotion. No v32 entered durable delivery and
no Coconala message or attachment was sent. The attempt nevertheless proved that all six saved buyer inputs and
the generated PNG/PDF/AI/SVG files can persist as non-zero local files; persistence alone does not make the
candidate fit for delivery. The next candidate must branch from v27's approved visual lineage, replace only the
PC/responsive inquiry sections with `2424.png` and `2.png`, regenerate every derivative, and be rejected if a
full-preview comparison shows any unrelated page-wide layout regression.
The minimal generic repair now stages every durable prior ZIP for the isolated owner and explicitly requires
the manager to inspect previews plus the complete conversation and select the last buyer-accepted visual
lineage; highest version is no longer treated as synonymous with accepted. It adds no Haru-specific branch,
workflow state or new dependency. This source change is syntax-verified but is not production-proved until a
published natural owner pass selects v27, builds the next version and passes the visual/effect gates below.

**E2E judgment.** This work changes no owned application UI, so Maestro is not applicable. Completion
requires the real launchd owner to act through the authenticated Coconala browser and an exact-room
official DOM/readback receipt; local artifact PASS, process liveness or Telegram alone is insufficient.

#### Paid harness reconstruction — authoritative

**Decision.** Stop extending the current business-semantic state machine. Haru is the emergency recovery:
Codex owns the complete context, visual decision and submission directly, using the existing authenticated
Paid browser tools only as mechanical tools. After Haru has an exact corrected artifact and fresh PASS, Codex
attaches that exact hash immediately with formal delivery OFF and obtains official DOM readback. No v31 resend,
no self-reported v32 reconstruction and no shipment from preview images is allowed.

The subsequent Paid repair is a harness reconstruction, not another error-type patch. It copies proven code
patterns from the following locally cloned, commit-pinned OSS references after checking their licenses and the
exact source files; prose summaries alone are not implementation authority.

| Reference | Pinned commit | Pattern to copy into the existing owner |
|---|---|---|
| `openai/openai-agents-python` | `904bc6988fd8e855c565de7fa65b223847101ed0` | One manager retains conversation ownership and invokes specialist agents as tools |
| `openai/openai-cs-agents-demo` | `bd7bfca0f5abf50529370814c3e7c88542011925` | Customer-context triage, specialist tools and one current conversation owner |
| `anthropics/cwc-long-running-agents` | `ad107a974bced5244f74dd283dbf2bfd3baee3a1` | Fresh-context evaluator, default-fail evidence gate and durable handoff |
| `langchain-ai/deepagents` | `23b83ad50f63d241d0069a3dc426d43b211adf2e` | Model-driven tool loop with middleware limited to context, persistence and safety |
| `anthropics/launch-your-agent` | `c9e0f1378a252bd42deb7e9eb02ac0cbd07160bc` | Explicit done criteria, grading and resumable long-running progress |

Do not add these frameworks as dependencies or transplant a demo wholesale. Copy the smallest relevant code
shapes into the existing `agent_runner.py`/Paid owner, retain license notices for any copied code, and delete
the replaced semantic routing. The manager decides buyer intent, artifact work and replanning. Deterministic
code only enforces exact room, artifact/hash integrity, formal-delivery policy, secret boundaries, effect
dedupe, official readback and lease ownership. Raw tool failures return to the manager; an enum may describe
an observed failure but may never prescribe shipment or the next business action.

**Atomic reconstruction order.** Do not execute an item before its preceding spec checkbox exists here.

1. [ ] Haru incident lead: regenerate one durable next-version package from the durable v27 visual lineage,
   preserving every unrelated v27 layout while replacing only the inquiry sections from saved latest PC
   `2424.png` and responsive `2.png`; open both full previews beside v27 and the buyer source, inspect
   AI/PDF/PNG members and hashes, and reject any page-wide regression; obtain
   fresh evidence-backed PASS; submit the exact package directly through the existing browser tool with formal
   delivery OFF; obtain exact-room official DOM readback; repeat read-only and prove replay-zero.
2. [ ] Produce a code-level adoption map: for every copied OSS pattern record pinned source file/function,
   local destination, license, behavior retained and behavior deliberately omitted. No article-only rationale.
3. [ ] Make one Paid manager own the complete room conversation, accumulated contract, current artifact,
   buyer-visible goal and final response. Specialists are tools; no handoff may lose conversation ownership.
4. [ ] Replace hardcoded business-semantic error-to-transition routing with raw structured tool results returned
   to the manager for replanning. Retain only deterministic safety invariants and delete obsolete shipment enums.
5. [ ] Make artifact production a tool with durable inputs/outputs: every buyer asset and generated asset is
   saved once, content-addressed, package-bound and available after failure/restart; temporary cleanup cannot
   erase the only candidate or its review images.
6. [ ] Make the fresh evaluator a read-only agent-as-tool that opens the actual source, candidate and package.
   Its delivery result is only PASS or NEEDS_WORK; missing evidence, uncertainty and timeout fail closed and
   return concrete findings to the manager.
7. [ ] Make browser send/readback tools mechanical and idempotent: exact-room preflight, exact artifact hash,
   formal delivery OFF before approval, send fence, official DOM receipt and replay-zero. They never decide copy,
   artifact fitness or buyer intent.
8. [ ] Replace workflow-state completion with an append-only factual handoff/effect ledger that survives crash,
   restart and model context loss. Manager reconstructs the next action from facts; no stale state authorizes an
   effect.
9. [ ] Migrate every purchased Paid room through the reconstructed manager, preserve already-proved effects,
   close every silent pending/failure with an owned disposition, and prove one natural multi-project pass with
   official readback and replay-zero for every effect.
10. [ ] Only after Paid proves the architecture, apply the same manager/tool/evaluator/effect-ledger shape to
    Negotiate, Storefront and Apply in the existing authoritative lane order; then continue device durability,
    clean third-device acceptance, real withdrawal and OSS audit.

#### Paid buyer-visible media contract — authoritative

**1. Overview.** A saved screenshot, generated image or linked asset is part of the buyer-visible
deliverable, not transient model/browser evidence. The current generic file path can mark an incomplete
draft PASS when the draft merely lists missing contract-required media as unresolved. This allowed
`18171890` v4 to pass locally with zero supplied/candidate/reference images and three required screenshots
still absent. The durable Paid owner must bind required media before building, save every produced asset,
prove package membership and visual review, and distinguish a truthful review-stage draft from a completed
buyer output.

**2. Acceptance criteria.** All criteria are mandatory before this slice closes.

- Before the builder runs, the accumulated buyer contract records `required_assets`. Each entry binds a
  stable `asset_id`, media kind, minimum count, buyer-visible purpose, source authority (`builder`, `buyer`
  or `account_owner`) and whether the file must be a member of the delivered archive.
- Every produced or supplied buyer-visible file records an `artifact_assets` entry with a project-owned
  absolute path, non-zero byte count, MIME/type, SHA-256, provenance class and archive member path when
  applicable. A transient browser/model path is not an artifact.
- `acceptance_status=PASS` requires every `required_assets` entry to be covered by the required number of
  readable, non-empty, hash-matching `artifact_assets`. For ZIP output, every required member must exist,
  be readable and match the recorded bytes/hash. Missing, zero-byte, corrupt, hash-mismatched or omitted
  required media fails closed.
- A requirement whose source authority is `account_owner` and cannot truthfully be delegated produces a
  durable `BLOCKED_NON_DELEGABLE` disposition with one exact minimum owner action. It cannot become PASS
  because a draft documents the gap. `REVIEW_READY` may describe and send a useful truthful draft with
  formal delivery OFF only when the accumulated contract permits buyer review before those inputs exist;
  it never counts as completed Paid delivery.
- The fresh visual reviewer receives every candidate and reference image named by the contract and records
  the inspected hashes. `required_assets` containing visual media with zero attached review images is a
  validation failure, not “visual inspection not applicable.”
- A contract with no buyer-visible media requirement remains valid without synthetic images. Manledge is
  the regression case for asset-free output; Haru is the regression case for a ZIP containing real media;
  tests use synthetic fixtures and never copy customer files into the public repository.
- Completion still requires the generic launchd owner to attach the exact hash-bound artifact, obtain the
  exact-room official DOM readback with formal delivery OFF where required, and prove replay-zero.

**3. As-is / To-be.**

| Boundary | As-is | To-be |
|---|---|---|
| Requirement capture | Media can remain prose in `unresolved` | Required media is a structured pre-build contract |
| Persistence | Evidence images may exist without deliverable binding | Buyer-visible assets have durable path, size and hash |
| Package validation | Top-level artifact existence/hash is sufficient | Required archive members and their bytes are verified |
| Acceptance | Missing screenshots may be recorded as a PASS check | Missing required media is FAIL, REVIEW_READY or BLOCKED |
| Visual review | Zero attached images can be called non-applicable | Required visual hashes must all reach the reviewer |
| Completion | Bounded draft can look like completed delivery | Review-stage and completed effects have distinct dispositions |

**4. Test matrix.** No separate review ceremony is added; these are direct regression checks for the
existing owner and validator.

| # | To-be | Test name | Cover |
|---|---|---|---|
| 1 | Required media is structured before build | `test_required_assets_are_bound_before_builder` | OK |
| 2 | Missing/empty/hash-mismatched media cannot PASS | `test_required_asset_integrity_fails_closed` | OK |
| 3 | Required ZIP members and bytes must match | `test_required_archive_member_is_verified` | OK |
| 4 | All visual hashes reach the reviewer | `test_required_visual_assets_are_attached_to_reviewer` | OK |
| 5 | Non-delegable media becomes durable blocker | `test_account_owner_asset_gap_cannot_pass` | OK |
| 6 | Review draft never counts as completed Paid delivery | `test_review_ready_is_not_delivery_complete` | OK |
| 7 | Asset-free contracts remain valid | `test_asset_free_contract_does_not_invent_media` | OK |
| 8 | Existing customer data stays out of public fixtures | `test_media_contract_fixture_contains_no_customer_data` | OK |

**5. Boundaries.** Do not fabricate firsthand use, seller-authored text, privacy-redacted screenshots or
human publication approval. Do not regenerate Haru v31 or Manledge v20. Do not create a one-off byusco
executor, new agent layer or second Paid owner. Do not formally deliver before buyer approval. Keep secrets,
customer media and private project state out of Git, logs, prompts and public test fixtures.

**6. Atomic execution steps.** Soft target: two production files and one focused public regression file;
reduce scope before exceeding three files or 100 production LOC.

1. [x] Extend the existing Paid decision boundary in `scripts/paid_direct.py` and the existing decision
   schema with the structured `required_assets` contract. Schema/prompt version 4/v8 now invalidates old
   cached decisions, binds every buyer-visible screenshot/image/linked asset before the builder runs, and
   directly rejects malformed, duplicate, zero-count or unsupported asset entries.
2. [x] Extend the existing Paid manifest boundary in `scripts/paid_direct.py` with the structured
   required/produced asset contract and distinct PASS, REVIEW_READY and BLOCKED_NON_DELEGABLE semantics.
   The normalizer now copies the versioned decision's `required_assets`, requires `artifact_assets`, binds
   manifest/acceptance disposition exactly, requires one exact `blocking_action` for non-delegable input,
   preserves the existing PASS-only delivery validator instead of creating a second state machine, and
   stops a durable non-PASS artifact before authorization/build so a later pass cannot silently regenerate it.
   Legacy artifacts may carry their truthful migrated contract in the manifest without forging an old signed
   decision receipt; once a current decision exists, any manifest/decision contract mismatch fails closed.
3. [x] Extend `scripts/paid_work_evidence.py` to fail closed on asset count, path ownership, non-zero bytes,
   MIME/type, hash and required ZIP membership, and to reject required visual media with no review receipt.
   The existing validator now checks project-owned files or exact ZIP members byte-for-byte and requires every
   image hash in the artifact contract to appear in the controller's artifact-bound review manifest.
4. [x] Run the smallest direct synthetic checks for the asset boundary plus the existing Paid disk preflight
   regression; do not add a TDD workflow or separate review ceremony. Direct temporary fixtures proved ZIP
   integrity, missing/count/hash/review failure and the asset-free case; `test_paid_disk_preflight.py` remains
   green at 9/9 without modifying its tests.
5. [ ] Repair the failed private-record migration without another regeneration: Haru v31 must prove its
   existing images/archive members; reconcile Manledge v21 against the preserved v20 hash and its actual
   media-free contract; keep byusco v5 REVIEW_READY/non-delivery and preserve the prior v4 hash as migration
   evidence. Never represent either regenerated artifact as an approved buyer effect.
6. [x] Publish release `097a2e1363929e4724294e8e44fba86bfd3e9d71`, verify its Paid source bytes
   against the Git blob, read back the four loaded launchd program arguments, and observe a natural Paid
   continuation. The continuation produced no effect and exposed the migration failures above; it is not Done.
7. [ ] Obtain exact-room official readback and replay-zero for every safe effect; keep byusco's exact owner
   dependency durable while Haru, Manledge and every other non-blocked purchased room continue.

1. **Paid/Submission — finish first.**
   - [x] Deploy and read back Paid ignoring shared preventive `disk-pressure.block` (20 GiB) and
     `disk-writers.stop` (10/11 GiB hysteresis), while retaining the 512 MiB last-resort guard and
     expiring operator brake; an expired audit file or healthy 10+ GiB headroom must not stop earning.
   - [ ] Haru `18169583`: submit the already acceptance-PASS v31 ZIP with concise text, recover exact-room
     `targeted_readback`, prove the v31 hash buyer-visible and keep formal delivery OFF. Superseded by the
     buyer's explicit defect report: do not resend v31. Preserve it as failed evidence, reconstruct the exact
     buyer-approved latest design from the accumulated attachment/message sequence, require direct visual
     correspondence rather than `bounded_undeterminable`, and send only a genuinely corrected next artifact.
     Atomic order: [ ] persist every candidate before temporary runtime cleanup; [ ] make the builder reuse the
     decision's exact required asset ids instead of renaming them; [ ] regenerate one next-version correction
     from the saved buyer source and latest PC/responsive inquiry references; [ ] have the incident lead and a
     fresh reviewer open the source, both candidate previews and package members and record hash-bound PASS;
     [ ] let the existing Paid owner attach that exact hash with formal delivery OFF; [ ] obtain exact-room
     official DOM readback; [ ] rerun naturally and prove replay-zero.
   - [ ] Manledge `18169985`: submit the already acceptance-PASS v20 deliverable, repair the
     `file_browser` attachment path without regenerating the artifact, obtain official readback and
     keep formal delivery OFF. The buyer has approved the CSV and is now waiting for the community details,
     complete proposed listing copy, individual outreach wording, and the progress-management/reporting method.
     The semantic decision correctly classified that combined response, but the runtime created REVIEW_READY
     v21 while the answer reviewer state remained `APPROVED`, then stopped at `file_validation`; no response
     or attachment is officially visible for the latest buyer request.
   - [x] X-post project `18171850`: approved v1 was attached and officially read back with formal
     delivery OFF.
   - [ ] Review-article project `18171890`: do not represent v4 as a publishable completed article.
     Repair the generic acceptance boundary so missing contract-required screenshots, firsthand-use
     passages and required human editing cannot pass merely because the draft lists them as unresolved;
     persist the exact non-delegable seller action as a durable blocker. Only then repair the
     `file_validation` handoff, send the truthful buyer-review-stage artifact if that bounded effect is
     still contract-valid, obtain official readback and keep formal delivery OFF.
   - [ ] Treat ten reviews as a ceiling, not a quota, and fail closed: a fresh reviewer may return only
     evidence-backed PASS or NEEDS_WORK for delivery authorization. `undeterminable`, missing visual
     correspondence, unavailable provenance and review exhaustion never authorize shipment; preserve the
     artifact, return the raw evidence to the Paid manager for replanning, and request one exact owner input
     only when the missing fact is genuinely non-delegable.
   - [ ] Read back first-artifact staging without a prior `paid-work-result.json`: new projects must
     create v1 from complete context, while existing projects alone receive a prior artifact to resume.
   - [ ] Classify and close every other purchased room as buyer-waiting, formally complete,
     generic-loop actionable or explicitly reserved with a durable reason; no silent `pending`,
     `remote_resume`, `file_validation` or missing project state remains.
   - [ ] Prove one natural multi-project pass with all actionable projects running independently,
     every effect officially read back, formal delivery OFF before buyer approval, and replay-zero.
   - [ ] Verify progress-file upload survives Coconala form re-render: on CDP stale-node error,
     reacquire document and file-input node before retrying; persist non-retryable browser errors.

2. **Negotiate — coverage before latency.**
   - [ ] Account for every buyer-authored message with exactly one durable disposition: replied,
     estimate sent, safely terminal, or retry-owned. Missing/skipped messages must be zero.
   - [ ] Use Job Description + seller proposal + complete DM/thread context for every reply; never
     ask again for facts already present and never use a text-only acknowledgement when an estimate
     or concrete answer is due.
   - [ ] Send or revise one competitive estimate when the buyer requests/agrees to it, preserve
     explicit buyer prices, deduplicate effects and obtain official card/thread readback.
   - [ ] Prove a new natural actionable buyer message reaches official reply/estimate readback in
     under 30 minutes, then prove replay-zero.

3. **Storefront.**
   - [ ] Make every public listing, price, scope, FAQ and option match an actually purchasable live
     product; remove contract-only ¥3,000/¥5,000 options that are not sold or publish them truthfully.
   - [ ] Persist storefront attribution from official facts captured during Negotiate rather than
     requiring the buyer to paste a listing URL.
   - [ ] Prove one natural official listing create/update receipt and replay-zero.

4. **Four-lane durability on this device.**
   - [ ] Re-audit Apply maximal coverage and duplicate fences, then obtain a new natural official
     application receipt without reviving historical replay work.
   - [ ] Verify Apply, Negotiate, Paid and Storefront are all loaded, independently scheduled,
     bounded on browser/model/disk failures, self-cleaning, owner-reported and able to resume after
     restart without split-brain checkouts or an expired brake.
   - [ ] Observe natural official receipts for application, buyer reply/estimate, listing effect and
     paid delivery, followed by no duplicate effect on replay.

5. **OSS third-device acceptance and onboarding.**
   - [ ] From a clean third-party/friend device, run `./install.sh coconala` without this seller's
     checkout, credentials, customer state or private bundle.
   - [ ] Complete one front-loaded setup session covering account recovery/signup, email verification,
     SMS, seller identity, eKYC, required consents and domestic payout account while keeping secrets,
     OTPs, documents and bank data out of Git, logs, prompts and reports.
   - [ ] Start all four lanes with email as the default notification adapter; prove no external effect
     before authentication and one natural official receipt per lane after activation.
   - [ ] Prove a real marketplace balance withdrawal arrives at the registered bank without another
     setup step. Do not call balance, estimates, views, tests or dry runs revenue.
   - [ ] Re-run public-tree/history secret and customer-data audits, clean-clone commands and README
     verification at the final commit; keep the MIT package explicit that income is not guaranteed.

6. **Bounded follow-up after the product proof.**
   - [ ] Qualify the current CloakBrowser major against the real marketplace before upgrading it.
   - [ ] Merge the already-pushed legacy profitable-claude removal branch after its unrelated merge
     clears, then verify no reachable Coconala skill, loop, launchd job or runtime import remains there.

**Ponytail decision and current development cursor.** Do not create a separate email project,
one-off Manledge/Haru executor, new agent layer or parallel implementation track. Reuse the existing
four lanes and make the smallest changes inside their durable owners. Finish in this order:
**generic context-complete Paid continuation -> natural Paid proof using already-open purchased
orders -> Negotiate total coverage -> Negotiate sub-30-minute latency -> Storefront -> four-lane
durability -> OSS third-device acceptance**. Manledge and Haru are production records the
generic Paid owner must consume; they are not manual development steps and Codex must not stand in
for the loop while waiting for a buyer reply.

Negotiate optimizes lexicographically: **coverage before speed**. Every buyer-authored message must
enter a durable per-thread queue and reach exactly one official disposition: replied with readback,
estimate submitted with readback, safely terminal with a recorded reason, or retry-owned with a next
attempt. Missing/skipped messages must be zero before latency is called complete. Independent threads
may run concurrently, while one thread remains serial to prevent stale-context replies and duplicate
effects. After coverage is zero-miss, every newly actionable buyer message must receive official
readback within 30 minutes under a natural loop wake.

**Autonomous continuation contract.** Codex, the operator and an ad-hoc browser script are never the
durable owner of customer work. Every external effect and every remaining obligation must be written
before the current process exits, and the loaded Paid owner must resume the exact next transition on
its next wake. The common state machine is `discover -> permission-check -> contact -> reply ->
marketplace/LINE handoff -> ledger -> formal delivery -> official readback -> replay-zero`. A wake
may advance multiple independent records, but each record has one effect key and one provider or
official receipt; a PID, drafted message, button click or local row without receipt is not progress.
Missing permission for one channel suppresses only that channel and continues every other safe
route. A buyer is asked once only when a new non-delegable legal/account authority is genuinely
required; the loop persists that dependency, continues all non-blocked work and consumes the reply
without a human or Codex re-entering the workflow.

Purchased work is artifact-first. Every actionable buyer request or material work milestone MUST
produce and attach the best truthful artifact supported by the accumulated context, accompanied by
one concise message. Text-only replies are limited to receipt acknowledgement, scheduling, a direct
buyer question whose answer requires no artifact, or the single non-delegable authority request
above. They are never a substitute for starting, revising or submitting the work. Formal delivery
remains off until the full accepted scope passes its quality gate; progress artifacts remain useful,
versioned and deduplicated meanwhile.

Outbound prospect email is an internal Paid provider adapter, not a separate milestone, agent or
personal Gmail browser task. The Paid installer configures it only when the installed workload needs
email: sender identity, authentication, reply mailbox, unsubscribe identity and a real send/readback
probe. Only a provider-accepted receipt increments `sent`; delivery-unknown remains retry-owned and
never becomes a fabricated contact. Failure of this adapter blocks only its dependent effects, not
other orders or lanes.

Existing paid liabilities consumed by the generic Paid owner (not a manual development queue):

1. **Manledge / request 5200847 / thread 10104078.** Reconstruct the original application, all
   pre-purchase DM, purchase scope and talkroom before acting. Deliver a real spreadsheet/CSV of 100
   Osaka-centered food-delivery driver candidates matching the agreed screen (bike or bicycle,
   monthly travel target at least 1,500 km where evidence exists, rating at least 4.5 where evidence
   exists, Osaka-centered activity, no required-day restriction). Required columns are candidate
   identity/handle, source/profile URL, contact route, area, vehicle, mileage evidence, rating
   evidence, eligibility and reason. Perform and truthfully receipt 50 permitted outreach actions;
   record destination, channel, timestamp, exact message, outcome and reply state. Never mark an
   unperformed approach as sent. Attach the candidate file plus outreach ledger with one concise
   apology/summary message and leave formal delivery unchecked. Official attachment/readback and a
   replay with zero duplicate outreach are required; the manual apology is not completion.
   Use the proven driver-recruitment funnel, not bulk unsolicited social DMs: multi-source local
   discovery -> dedupe/enrich/score -> contact-permission check -> short mobile qualification ->
   immediate LINE handoff -> referral expansion. Driver hiring case studies show that LINE/SMS or
   Messenger, a short application, minimum qualification questions and immediate follow-up convert;
   they do not justify indiscriminate outreach. X explicitly forbids automated bulk unsolicited DMs
   and non-API browser automation, so an X profile may support discovery but counts as an outreach
   action only when that person has explicitly invited contact. Prefer job-seeker pools, driver
   communities with recruitment permission, public business/contact forms, referrals and other
   opt-in routes. Reuse the OSS pipeline shape `collect -> dedupe -> enrich -> suppress -> score ->
   export` from Dukotah/leadgen; evaluate KeeLead only as a source adapter, not as a wholesale new
   subsystem. The buyer did not include an official LINE URL in the application, pre-purchase DM or
   purchased talkroom, but live readback of the buyer-owned LOXAD X profile and pinned post resolves
   both public short links to the same existing official destination,
   `https://line.me/R/ti/p/@810akrtq`. Use that destination; do not ask the buyer to resend it and do
   not create a second LOXAD-branded LINE identity. Sources: https://x.com/LOXAD_official,
   https://x.com/LOXAD_official/status/2088109682447810938,
   https://kuzen.io/case/detail/gojob,
   https://markiteasy.com/blog/how-to-recruit-cdl-nemt-drivers/,
   https://help.x.com/en/rules-and-policies/x-automation,
   https://github.com/Dukotah/leadgen, https://github.com/Atum246/keelead.
   The 100-candidate progress artifact is now buyer-visible. The existing Paid browser path sent
   `manledge-osaka-driver-candidates-100-v1.csv` once in talkroom `18169985`, and an independent
   fresh official read found the exact latest seller message plus the attachment while the formal
   delivery checkbox remained off. The file contains 100 rows, 100 unique profile URLs and SHA256
   `99a25f87e135053f5e3f2a26d0df724d97b7a6a55c3b985be8fc28e28885c6fc`; unverifiable mileage
   and ratings remain explicitly marked for direct qualification. Progress delivery previously ran
   the final-contract quality score and therefore rejected every honest partial artifact for its
   declared blocker. Ordinary progress now keeps the deliverable/relevance gate but reserves the
   final-contract score for revision-after-formal delivery. Remaining Manledge work is exactly 50
   permitted, truthfully receipted outreach actions, response/LINE handoff tracking, then formal
   delivery and replay-zero proof; the 100-candidate list must not be resent.
   Manledge atomic status:
   - [x] Reconstruct application, pre-purchase DM, purchased scope and complete talkroom context.
   - [x] Identify the existing buyer-owned LOXAD LINE destination without asking again or creating
     another brand identity.
   - [x] Send and officially read back the 100-row candidate CSV once with formal delivery off.
   - [ ] Perform 50 permitted outreach actions and persist destination, channel, timestamp, exact
     message, outcome and reply state without claiming unsent outreach.
   - [ ] Track interested candidates through qualification and the existing LOXAD LINE handoff;
     record Web-meeting requests when they occur.
   - [ ] Attach the completed outreach ledger, make one formal delivery, read it back officially and
     prove replay causes zero duplicate outreach or delivery.
   - [ ] Move the current `1 sent / 49 remaining` state, listing-authority dependency, candidate
     suppressions and mail-provider dependency under the loaded Paid continuation owner; prove a
     fresh wake resumes without Codex, the operator or a one-off script and does not replay row 1.
   Contact-permission audit: all 100 submitted profiles were rechecked against current first-party
   pages. Three expose a real general/business-contact invitation, but none explicitly invites
   automated recruitment; existence of a DM button is not consent. Wider first-party research found
   two additional Osaka delivery creators with work-request channels. X forbids unsolicited bulk or
   automated DMs and non-API browser scripting; Instagram/TikTok likewise do not permit automated
   cold outreach. Therefore the loop must not turn the 100-row discovery file into 50 fake or
   policy-violating sends. The compliant 50-person acquisition path is an opt-in recruitment pool:
   client-authorized Hello Work direct requests, or a truthful client-authorized listing on the free
   driver community DriverTalk, followed by Jimoty/engage when needed. Those external listings must
   identify the real contracting entity and the seller as recruitment support; they must not
   impersonate LOXAD or create a buyer-owned account without authority. Ask the buyer once for this
   listing authority while sending individualized first contacts only to the verified work-contact
   channels. Sources: https://help.x.com/en/rules-and-policies/x-automation,
   https://www.hellowork.mhlw.go.jp/enterprise/mem_search.html,
   https://lp.drivertalk.jp/, https://jmty.jp/osaka/rec-dis/g-1882,
   https://en-gage.net/expense/.
   The buyer-facing authority request was sent once and officially read back in talkroom `18169985`
   with formal delivery off. One individualized first contact was then actually submitted through a
   candidate's first-party work-request form; the form returned its explicit sent confirmation and
   ledger row 1 stores the destination, timestamp, message hash and pending reply state. The current
   outreach count is therefore `1 sent / 49 remaining`, not 50. Gmail-only work contacts remain
   unsent because the required Google-login skill points to a missing canonical instruction file;
   neither credential recovery nor an unverified local mail relay may replace that authentication
   boundary. Continue from buyer listing authority or a restored approved email adapter, never by
   replaying row 1 or converting uninvited social profiles into sends.
2. **haru haru9 / project 18169583.** Finish the current v10 producer/reviewer cycle, attach the
   accepted PC/responsive editable package in the exact room with formal delivery unchecked, read
   the attachment back officially and prove replay effect zero. Do not ask locality or copy questions
   already resolved by the buyer's 羽曳野 instruction and attachments.
3. Use these records only as natural evidence for the generic Paid owner. It must resume them from
   durable state without Codex/manual execution, including waiting safely when no new buyer message
   exists. After this generic Paid proof passes, move the cursor to Negotiate coverage and latency.

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
  Storefront and Paid. Below the configurable floor (`GIG_DISK_HEADROOM_KIB`, default 524,288 KiB)
  it emits `state/disk-headroom.json` with
  `failed: 1 / effect: 0 / readback: 0` and skips the child; at the exact threshold it preserves
  the child argv and environment. It fails closed when free-space measurement is unavailable and
  never auto-deletes user files from a business lane. Focused guard coverage: 4 passed.
- [x] Read back 10,617,248 KiB and then 10,616,160 KiB free across separate samples; successfully
  write, fsync, read and remove a 4 KiB probe in the gig state filesystem.
- [x] Keep secondary candidates documented but untouched; the last-resort guard makes further deletion
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

**Paid atomic execution checklist.** Close in order; do not replace an earlier unchecked item with
a later successful example.

- [x] P1 — Collect every currently open purchased order from the authenticated official
  `/mypage/received_orders/open` list. Fresh natural evidence at
  `~/gig/evidence/paid-direct-live/orders/orders-only-snapshot.json` observed five official cards
  and emitted five orders with `coverage_complete=true`, `login_redirect=false` and exact
  `cards_count == len(orders)`.
- [x] P2 — Give every collected order one stable marketplace identity. The same receipt contains
  five unique numeric `talkroom_id` values and five matching unique `contract_id` values of the
  form `talkroom:<talkroom_id>`; no local sequence or capture timestamp participates in identity.
- [x] P3 — Bind the original application/proposal to each purchased order's context packet. The
  selected-talkroom collector now follows the already-observed official `offer_reference`, stores
  its authenticated body under `source/proposal/`, and the context compiler includes it in
  `sources_present` and `read_these_first`. Live Haru proof read
  `/direct_offers/edit/6332954`, persisted 1,489 bytes at
  `source/proposal/offer-18169583.json`, and compiled context digest
  `c3c751c400c264e2d098569db4a10d4c625c75049a5f2020850d42a6481df316` with
  `proposal_read_first=true`. Orders without an official application/offer retain explicit absence;
  the loop never invents one.
- [x] P4 — Bind every pre-purchase DM to the same context packet. Paid preflight now invokes
  the existing authenticated DM collector before semantic work; a full-inbox miss is persisted
  as explicit absence while browser/parser/identity failures stop partial-context execution.
  Production proof on Manledge binds official DM thread `10104078` (10 messages, content SHA256
  `25c0352f8530c95cfc322834003c5ff46f300fa3b3121ca74de6c9ff749cf0ce`) under
  `projects/18169985/source/dm/`; the regenerated packet reports `dm` in `sources_present` and
  names that exact thread in `read_these_first` (packet SHA256
  `5c0e3522c7817b3c59ea0b6846743cd5b249a1c783791dc6496d17619284f184`).
- [x] P5 — Bind purchased scope, agreed price and deadline to the same context packet. The
  existing `order` section now keeps the official order label, agreed `price_jpy`, marketplace
  contract identity and `delivery_date` together. Production proof on Manledge reads scope
  `新規事業での配達ドライバー確保のアポイント獲得をお願いします。`, `9000`,
  `offer:6331348`, and `2026-08-25` from one section; packet SHA256 is
  `47280faaff6c534fe0e64902bfbb9440da2f418f58ac4e80b75f21857aee7241`.
- [x] P6 — Bind the complete append-only talkroom history to the same context packet. The
  existing compiler retains the full `source/talkroom/messages.jsonl` ledger and names it in
  `read_these_first` rather than truncating history into the prompt. Production Manledge proof is
  15 ledger rows with 15 unique marketplace message identities (buyer 7, seller 6, system 2),
  and the compiled talkroom receipt independently reports `message_count: 15`.
- [x] P7 — Bind every buyer attachment and its content receipt to the same context packet. Haru's
  official talkroom exposes exactly three buyer files (`image.png`, `kaitori-area_img2-2.jpg`,
  `kaitori-area_img1.jpg`; 1,575,075 / 799,982 / 1,070,716 bytes). The project holds exactly those
  three files, recomputed disk SHA256 equals every `source_refs` receipt, and all three absolute
  paths appear in `combined_context.buyer_attachments` and `read_these_first`.
- [x] P8 — Persist one context digest plus source receipts before semantic work begins. The
  compiler atomically writes `context/current.json`, then fsync-appends
  `context/context-read-receipts.jsonl`; only after that returns does `_paid_decision` construct
  or run its semantic prompt. Manledge's latest receipt binds context SHA256
  `47280faaff6c534fe0e64902bfbb9440da2f418f58ac4e80b75f21857aee7241`, buyer event
  `7fdfbc41…`, and 23 byte/SHA256 source receipts under receipt SHA256
  `b2025e5001f705964a823df5b392f0d3b98ca5576a0402edd862fda14278bd85`.
- [x] P9 — Suppress any question whose answer already exists in the bound context. Semantic
  decision v7 requires a complete packet plus `read_these_first` search before choosing a
  question; the answer owner forbids known-fact questions, and the independent Sol verifier must
  block any candidate question answered anywhere in those sources. This remains semantic and
  buyer-agnostic: no keyword, buyer name or job-category router is introduced.
- [x] P10 — Permit one clarification only for a genuinely absent fact that blocks truthful work.
  Decision v7 and the answer owner permit at most one bounded question only after every cumulative
  source proves the fact absent and that absence prevents truthful work. The fresh verifier rejects
  both answered questions and questions used to postpone useful non-blocked work.
- [x] P11 — Produce every non-blocked portion while that clarification is pending. Semantic
  decision v7 routes a partially blocked file task to artifact work with only the genuinely absent
  fact in `unresolved`. File policy v20 requires the owner and fresh reviewer to ship a useful,
  honest bounded artifact now, while rejecting placeholders, invented facts and false full-scope
  PASS claims.
- [x] P12 — Generate a useful artifact on the first actionable purchased-order transition. A
  first semantic `actionable/file` state has one route only:
  `_prepare_one → _prepare_file → _build_and_authorize_file`; write phase is unreachable until
  the buyer-facing artifact, manifest, acceptance receipt and fresh-review authorization all
  exist. The final natural-order proof remains P31 rather than being conflated with this contract.
- [x] P13 — Reject acknowledgement/status text as a successful Paid effect; an actionable file
  request must remain `mode=file`. The owner explicitly rejects plans, status reports, transaction
  summaries and promises as deliverables; the fresh reviewer rejects the same class, and write
  phase reports success only after the exact attachment is visible in the official talkroom.
- [x] P14 — Build the artifact with the configured `gpt-5.6-sol` executor. Haru's live
  `agent-PAID_FILE_OWNER/summary.json` proves the selected model and a produced v18 package.
- [x] P15 — Review it in a fresh isolated `gpt-5.6-sol` context. Haru's live
  `agent-PAID_FILE_VERIFY/summary.json` and result prove an independent rejection of the producer's
  false PASS after finding four source-copy substitutions.
- [x] P16 — Keep the reviewer read-only and unable to submit. The production verifier command uses
  `--read-only`; only the fenced delivery owner owns marketplace mutation.
- [x] P17 — Persist every reviewer finding and return it to the executor as the next bounded
  revision, including all analogous defects in the same failure class. Haru exposed the exact
  defect: its durable v19 finding was ignored after the owner promoted v20 because resume required
  the rejected artifact SHA to remain current. Resume now binds the finding to the unchanged buyer
  event, requirements and policy, so every unapproved successor receives it until review clears it.
- [x] P18 — Treat an in-pass review-round limit as durable `REPAIR_PENDING`, never terminal
  `file_verifier` failure. `_prepare_one` now returns a pending transition when that durable state
  exists; the parent records `pending` and performs no write effect instead of converting the
  bounded round limit into a failed pass.
- [x] P19 — Attach useful progress with formal delivery off while accepted scope remains. The
  prepared and presend decisions must both remain `progress`; the browser rejects either queue or
  payload unless `formal_delivery_checkbox` is exactly false, and Paid succeeds only after the
  exact message plus attachment is read back from that official talkroom. Natural-send proof stays
  in P31.
- [x] P20 — Enable formal delivery only after the complete accepted scope passes. Formal requires
  the current buyer-side approval identity to exactly match semantic approval evidence, a valid
  fresh-reviewed file authorization, zero delivery blockers, and unchanged presend feedback. A
  prepared progress action may never escalate to formal during sparse presend readback.
- [x] P21 — Give reply, attachment and formal delivery independent durable effect keys. Every
  official browser evidence manifest and DOM receipt now persists content-addressed
  `coconala:reply:<talkroom>:<message_sha256>` and, when present,
  `coconala:attachment:<talkroom>:<file_sha256>` keys. Formal delivery retains its append-only
  ledger identity `coconala:formal:<project>:<file_sha256>` and exposes the same value as
  `formal_effect_key`; the three effect classes cannot cross-dedupe.
- [x] P22 — Read the attachment back in the exact official talkroom. Production progress evidence
  for talkroom `18138707` records an actual send and post-send official DOM readback of
  `カントリーロード_ハンドベル3パート譜_v15.pdf` (1,448,789 bytes) in that exact room; the
  on-disk artifact independently hashes to the manifest-bound SHA256
  `40e1e15059782403a35f107d71070e6a351bcd9a29971bb558a66968ef9bcdbd`.
- [x] P23 — Read formal delivery back in the exact official talkroom. Production formal evidence
  for talkroom `18130722` records `send_performed: true`, then reads the same official room back as
  `納品確認待ち` with its formal control disabled and seller attachment
  `tekokoro-no12-company-review-v2.mp4`. The receipt is bound to formal key/artifact SHA256
  `e862954d76278b6f6311692f735406626743e6d494d41f90c9511d4b7410992a`.
- [ ] P24 — Replay and prove zero duplicate replies, attachments and formal deliveries.
- [ ] P25 — Resume the next transition after an executor/reviewer process exits.
- [ ] P26 — Resume the same transition after a machine/login restart.
- [ ] P27 — Persist buyer-wait as an owned state rather than ending the workflow.
- [ ] P28 — Consume a later buyer reply and resume without Codex/operator execution.
- [ ] P29 — Resume the existing Manledge liability through the generic Paid owner.
- [x] P30 — Resume the existing Haru liability through the generic Paid owner. The live
  `57ac9eb159e0` Paid owner recognized the legacy v26 artifact as already beyond five review
  iterations, performed no v27 build and no additional review, authorized the unchanged artifact
  SHA256 `6ed990f395e0d19c15e46a383a0b0f54f39ec77ec42c6b34efbf5dcc5d16e497` with
  `shipment_basis=max_review_iterations`, selected `delivery_action=progress` with
  `formal_delivery_checkbox=false`, and returned exact-room `effect=1`, `readback=1`, `failed=0`.
- [ ] P31 — Prove one natural order end to end from complete context through one formal delivery and
  replay-zero.

**Accepted architecture — ship within ten reviews.** A production worker builds the buyer-requested
artifact and a fresh reviewer supplies bounded improvement feedback. The worker may revise the same
artifact line for at most ten review iterations; there is no discard-and-rebuild or alternative-
approach branch. A deliverable verdict ships immediately. On iteration ten, the best structurally
valid artifact ships as progress even when the reviewer still requests changes. Review is an
improvement signal, never an unbounded shipping gate. Every pre-approval shipment uses one concise
message and leaves formal delivery off. Corrupt, unreadable, secret-leaking or technically unsendable
files remain blocked because they are not artifacts that can truthfully be shipped. Independent
projects run without waiting for another project's build or review; only effects in the same
talkroom are serialized and deduplicated.

**Submission model route.** Keep the current production routing: the artifact executor is
`gpt-5.6-sol` at medium reasoning and the independent reviewer is a fresh, isolated
`gpt-5.6-sol` context with no authority to submit. Using the same model does not merge the roles or
their context. Do not add a model migration now: buyer-visible artifacts are the product, this route
already exists, and replacing the executor or reviewer with a cheaper model adds work without closing
the current defect. A cheaper route may replace either role only after a measured accepted-artifact
evaluation proves equal quality, revision count and deadline performance. Deterministic validators
and existing bounded artifact judges remain separate from these two LLM roles.

**Paid context and first-action contract — blocking production invariant.** A purchased talkroom is
never a fresh conversation. Before generating any buyer-facing reply or artifact, Paid must compile
one ordered context packet from the original application/proposal, every pre-purchase DM, the full
talkroom history, the purchased-order scope, and every attachment. Information already present in
any of those sources must never be requested again. The default first buyer-visible action after
purchase is useful work: build and attach the best complete artifact supported by the accumulated
context immediately, with the formal-delivery checkbox left off. A short progress message is not a
substitute for the artifact. Ask a question only when one specific missing fact makes truthful
production impossible; even then, produce and attach every non-blocked portion in parallel instead
of waiting idle. The Manledge room violated this contract by asking about DM/requirements already
supplied before purchase and thereby damaged trust. The haru haru9 room originally violated it by
asking which locality to use despite the later buyer message already resolving 羽曳野, then waiting
through repeated revision cycles without attaching usable work. Completion requires replayable
evidence that both classes are impossible for future rooms, not one manual apology or delivery.

**Purchased-talkroom output contract.** Before buyer approval, every actionable Paid cycle is an
artifact cycle: compile the complete context, build or revise useful work, independently review it,
then attach it with one concise message and formal delivery off. Review may improve the current
artifact for no more than ten iterations and may never prevent the tenth structurally valid version
from being attached. The tenth version is not discarded or rebuilt through another approach.
Text-only acknowledgement, plan,
promise, progress report or `対応します` is not a successful effect. A clarification is allowed only
when one fact is absent from every bound source and its absence makes all truthful production
impossible; if any portion is buildable, attach that portion in the same action. After buyer
feedback, repeat the artifact cycle. Only explicit buyer approval of the completed accepted scope
permits one fenced formal delivery. Prompt guidance is defense in depth; code must enforce the mode,
attachment readback, durable repair state and effect fence.

**Haru live failure and required repair.** Talkroom `18169583` is not awaiting buyer input. The Sol
executor produced `habikino-renewal-v18.zip` and self-reported PASS, but the fresh Sol reviewer proved
four buyer-source substitutions across PC/responsive outputs: `物件の状況→物件の状態`,
`相続した実家→相談した実家`, and two removals of the middle dot from `リ・ホーム`. The durable state
is `REPAIR_PENDING`, yet the lane surfaced terminal-looking `failed_step=file_verifier` after its
bounded review rounds and did not attach the artifact. The generic fix is: preserve the finding,
revise the same artifact line for no more than ten iterations, and attach the tenth structurally
valid version even if the reviewer still requests changes. Never discard it, switch to an alternative
approach, ask Haru another question for known facts, or leave it unsent. Formal delivery remains off
until the buyer explicitly approves. `REPAIR_PENDING` may continue iterations one through nine but
must become a shipment on iteration ten.
The resulting v26 shipment exposed a separate visual-contract failure after the buyer replied
`こちらのデザイン、イラストなどが一切ないのですが。。。`. The ZIP did contain both supplied
illustrations in `assets/` and visibly embedded them in the lower PC layout, but the owner replaced
the supplied first-page design language with a materially different white/green card layout. The
reviewer did not catch that because `_file_review_images` supported images and PDFs but returned no
candidate frames for ZIP artifacts; its own log recorded that no candidate/reference review images
were attached. An owner claim or asset presence is not visual correspondence. Every visual ZIP must
be safely expanded into its rendered review images, and the reviewer must receive those candidate
images together with every buyer-supplied visual reference. Missing candidate/reference pairs block
only that iteration; they never authorize a blind PASS. Buyer feedback starts the next artifact
revision cycle from the existing artifact, with formal delivery still off. Paid source census,
owner and blind-audit workspaces live under `~/gig/runtime/<talkroom>/`, outside both the
machine-wide temp tree and the sandbox-denied durable project: unrelated cleanup may never delete
an active job's workspace, while the isolated owner can still access its own staging tree. Owner
workspaces are keyed by the accumulated requirements digest and stable context-input digest; an
abrupt process death leaves the workspace for the next wake to resume, while a new attachment gets
a fresh workspace and a normal success/failure removes it.
Artifact version and review iteration are independent counters. A high historical `vN` may never
advance the review cap; only `paid-review-state.round` for the exact feedback/requirements cycle
counts toward the maximum of ten. A buyer-visible progress artifact does not suppress a durable
`REPAIR_PENDING` cycle: the next wake revises and submits again until approval or round ten.
The read-only targeted refresh is also project-scoped: up to eight fresh hidden CDP targets run in
parallel before the existing project workers, and one refresh failure degrades only that talkroom.
Each target is bounded to one 180-second attempt, so long histories can finish without restarting
their work at 90 seconds while one wedged browser target still cannot hold every other independent
project behind the generic 35-minute step timeout.
When a purchased request exposes both its original request id and a talkroom id, an existing
talkroom project containing the authenticated accumulated requirements is canonical. The resolver
must not select an empty request-id twin and strand article, copy or other new Paid work as pending.
Pre-purchase DM collection is attempted and any discovered thread/attachment remains mandatory
context. When the authenticated offer has no DM reference and discovery returns no usable receipt,
the loop records `dm_collection_unavailable` and continues only if proposal, full talkroom history
and accumulated requirements are all present; it never invents a DM or blocks an otherwise
buildable artifact merely to ask the buyer again.
DM discovery itself is bounded to 180 seconds. A browser process that exceeds that bound becomes the
same durable unavailable receipt and cannot hold its independent project worker for 35 minutes.
That unavailable receipt is reused for one hour while proposal, talkroom and requirements remain
present. A project that returns `remote_resume` immediately after stabilizing its decision retries
prepare once inside the same worker, without waiting for the next five-minute wake.
Remaining brake acceptance: deploy and read back Paid using the shared `gig_brake.sh status`
contract rather than raw file existence. A held lease must stop all effects, malformed/unknown
status must fail closed, and the owner's recorded expiry must free the lane even when the expired
file remains as an audit record.
Every reused semantic decision binds a digest of the compiled context's actual input file
size/SHA256 pairs, not volatile compilation timestamps. If attachments or messages arrive after the
decision, the mismatch forces a new Sol decision before any owner starts; identical inputs reuse the
decision, and an old `unresolved` claim may never survive after the missing source is collected.
The project worker revalidates that decision after DM collection. If DM discovery adds or changes
an input, it runs the Sol decision again in the same worker before choosing file/answer/remote mode;
it may not fall through to `remote_resume` merely because the required context became more complete.
It revalidates once more after a potentially long build/review and before delivery mode selection.
An official receipt refresh may update context during review; the loop refreshes only the semantic
decision and reuses the already approved hash-bound artifact instead of failing `file_validation` or
rebuilding it.
The parent initializes any missing durable state and submits the project immediately; it never runs
a bootstrap Sol decision inline. Decision, DM refresh, build and review therefore remain inside each
of the maximum eight independent project workers rather than serializing queue construction; the
current seven Paid rooms can all progress simultaneously.
The authenticated offer page is the exact bridge from a purchased order to its pre-purchase DM:
persist its `/mypage/direct_message/<id>` reference in the project proposal, then have Paid refresh
that one thread directly. A buyer-name scan incorrectly reported Haru's real DM `10102712` absent
after opening 134 unrelated threads; a negative name-search result is never durable context truth.

**Paid continuation and effect contract — blocking production invariant.** Every purchased order
has exactly one loaded continuation owner from purchase through formal readback. Builder/reviewer
processes may exit, the Mac may reboot and a provider may be temporarily unavailable; none of those
events may erase the next transition or turn the operator/Codex into the worker. The owner persists
artifact version, buyer context identity, permission decisions, outbound effect keys, provider
receipts, reply state, handoff state, outstanding authority and the next due action. It resumes from
that state until the full accepted scope is formally delivered. Email/contact-form/social adapters
share the same receipt and replay fence. A sent count is the number of unique provider-accepted
effects, never the number of candidates selected or messages drafted.

The acceptance proof must include one natural purchased order where the loop: (1) attaches useful
work on its first actionable transition, (2) exits and resumes from durable state, (3) sends at least
one approved external effect through its configured provider, (4) incorporates a reply or authority
decision, (5) submits the completed artifact exactly once, and (6) replays with zero duplicate
messages, outreach or delivery. No manual/Codex effect may be used as that proof.

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
- [ ] Compile and hash the complete application + pre-purchase DM + order + talkroom + attachment
  context before any Paid reply or production decision; expose source receipts for every component.
- [ ] Make artifact-first the purchased-room default: attach useful work on the first actionable
  Paid pass, keep formal delivery unchecked, and never replace the artifact with a status message.
- [ ] Prove already-known facts are never re-asked; a clarification is allowed only for one truly
  production-blocking unknown while all non-blocked work is produced in parallel.
- [ ] Build its requested artifact from the accepted scope.
- [ ] Validate the artifact before delivery.
- [ ] Deliver it exactly once.
- [ ] Read the delivery back in the exact official room and prove replay creates no second delivery.
- [ ] Prove the loaded continuation owner resumes an interrupted multi-step order without Codex or
  operator work, including provider-receipted outbound mail/contact and zero replayed effects.

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
