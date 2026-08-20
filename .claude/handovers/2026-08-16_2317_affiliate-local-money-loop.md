# Affiliate local money loop handover

- SSOT: `docs/affiliate-agent/AFFILIATE-AGENT-SSOT.md`; resume from `Measured planning checkpoint and next TODOs`, then `Remaining autonomous money-loop work — canonical order`.
- Development route: `/Users/anicca/anicca-project/.worktrees/affiliate-life-manager-spec`, branch `docs/affiliate-life-manager-spec`; required base remains `0a7debb58`.
- Installed source: `/Users/anicca/.local/share/life-manager/affiliate/current` → release `0e818458c2b832a2c3f225cb1143f2de4e4c02c6`; its `scripts/local_loop.py` is byte-equal to the candidate source (SHA-256 `6fba105c…776b26`). The release persists an append-only `AFFILIATE_TELEGRAM_DELIVERY` row linked by `wake_event_uuid` and `telegram_event_uuid`, honors the durable provider failure retry window, and keeps wake-history/daily counts free of delivery rows. Existing suite `69/69`, compilation, and temporary no-network delivery/failure-window fixtures passed. The installed existing owner then read back at `2026-08-21T08:27:56+0900`: `COOLDOWN`, unchanged official empty artifact, same 20 placements, and one canonical `NO_PENDING/ALREADY_DELIVERED` row for already-sent Telegram `26335`; no new public effect, provider transaction, or money was created. launchd introspection/install calls still return `141: Reentrancy avoided`, so six loaded owners are not claimed; this owner readback closes the release slice. Any future `skills/affiliate` change requires immutable install and another real owner replay after the release timestamp.
- Latest runtime delta: the installed existing owner ran at `2026-08-21T07:44:21+0900`, read `ALREADY_LIVE`, retained the same public/X object and 20 exact placement rows, and appended one `AFFILIATE_TELEGRAM_DELIVERY` row. The row links wake UUID `fe7c567c…04b750`, Telegram event UUID `4d376adc…452f1`, and provider message `26335`; delivery is `NO_PENDING/ALREADY_DELIVERED`, not a new send. The sent ledger confirms the same message ID, outbox/sent remain `124/124`, and no provider transaction or money was inferred. The earlier `07:12:35+0900` owner receipt `26741` remains the latest new click receipt.
- Release `cf7f19241` is now installed as `current` and source/installed `local_loop.py` bytes match (`34c66744…42b13a80`). Existing `69/69` tests, compilation, and a no-network failure-event fixture passed. The release creates one replay-safe `REVENUE_CYCLE_FAILED` Telegram candidate from the durable failure receipt without exposing raw links or secrets. The installer reached the immutable release and ownership receipt but launchd browser bootstrap still returned `141`; no direct executor was started.
- The existing owner naturally ran the installed release at `2026-08-21T08:06:20+0900`, recovered the same PartnerStack path to `NO_TRANSACTIONS` with new hash-valid artifact `f69af229…6734e3a` observed at `08:06:19+0900`, `source_rows=0`, and `appended_transitions=0`, and sent the recovery receipt as Telegram `26784` (`SELF_HEALED`) under event `3baa51c9…e9b22`; the linked delivery row is `DELIVERED` with provider message `26784`. No provider transaction, settlement, payout, commission, or money changed. The preceding `07:55:09+0900` `stage=links / NONZERO_EXIT` failure remains historical evidence, not zero revenue.
- The next existing-owner wake completed at `2026-08-21T08:17:13+0900` with wake UUID `3b448dc2…9dceca`: Repost observation saw 52 valid actions, `0` exact campaign joins, and 52 unjoined actions (`NO_REVENUE_CREDIT`). Revenue remained in the hourly `COOLDOWN`, so no duplicate or synthetic provider capture occurred; the official artifact stayed `f69af229…6734e3a` with zero commission rows. Telegram message `26794` (`REPOST_OBSERVED`) was `DELIVERED` through event `d7173757…2166ac`, linked to that wake. The next eligible official capture is expected around `09:06:19+0900`; B01 still waits for a non-empty official transaction/settlement row.
- Release `0e818458c` repairs the provider failure retry window: a newest failure receipt suppresses repeated capture until `retry_after`, while a later success completion supersedes that historical failure and restores the normal hourly cooldown. Existing `69/69` tests, compilation, and temporary boundary fixtures passed; source/installed `local_loop.py` SHA is `6fba105c…776b26`. The existing owner read back at `2026-08-21T08:27:56+0900` (wake UUID `7cb9c0f3…636b7`) with `revenue_state=COOLDOWN`, unchanged empty PartnerStack artifact `f69af229…6734e3a`, 20 placements, and rolling net `NO_TRANSACTIONS / NO_APPROVED_OR_PAID_ROWS / NOT_REACHED`. It appended only `NO_PENDING/ALREADY_DELIVERED` for already-sent Telegram `26335` (delivery `38e801bc…3e02d`), with no duplicate public effect, transaction, or money. This confirms installed replay/cooldown behavior only; the failure branch remains fixture-proven, not live-failure-proven. launchctl still reports `141`; all-owner load is not claimed.
- A further existing-owner replay at `2026-08-21T08:38:28+0900` (wake UUID `49c852a3…f67a7`) again stayed in `COOLDOWN`, retained 20 placements and the empty `f69af229…6734e3a` artifact, and appended only `NO_PENDING/ALREADY_DELIVERED` delivery event `cb65ebb4…593b4` for Telegram `26335`. No public effect, capture, transaction, or money changed; this is replay/readback evidence only.
- Current execution cursor is still E1-H/B01: the live ledger has 20 English placements, 20 dedicated provider-link keys, 20 owned URLs, 34 provider-link clicks, aggregate overview clicks 43, and zero official commission rows. Repost has 52 valid actions with 0 exact campaign joins and 52 unjoined (`NO_REVENUE_CREDIT`). The remaining atomic order is B01–B08, C01–C06, D02/D04–D08, E02–E10, F01–F06, G01–G07, then O01–O12 only after the USD 10,000 local proof; the SSOT current-queue summary is authoritative.
- A later existing-owner `launchctl kickstart` attempt at `2026-08-20T15:36:27Z` returned `141: Reentrancy avoided`; `last-run.json` stayed at the prior wake and no placement, provider, Telegram, or ledger mutation occurred. This is not a new owner proof and does not authorize a parallel executor; retain the natural owner receipt above as the runtime evidence.
- Release `90b33832ce293865a20c07e64fc5d9be8131b214` also repairs composition
  starvation after source refresh: unreceipted inboxes now precede receipt-backed
  inboxes. The natural owner wake at `2026-08-20T16:24:22Z` quarantined the
  malformed Google attachment with `EXPERIMENT_PLAN_MISMATCH`; the corrected
  subtitle experiment is the only unreceipted inbox. No publication, provider
  transaction, Telegram event, or money was created or inferred. Its next owner
  composition readback remains open.
- The corrected subtitle experiment then reached `READY_FOR_POLICY` at
  `2026-08-20T16:34:37Z` through the existing composition owner. Its official
  source-set SHA is `5da2a6a4beda152c9da4f60d9f4c4b5ff5c6399b18175b95c8a9601db7ec78bf`,
  result SHA is `ecb967667fd0c5e8b8fdbf77f6a59a25b348e2b25f3738affee27bb936f6225b`,
  and handoff SHA is `7c83e48921b98ee6b9c2e5181162cd1c6b406b4b656c0b96e1a5d6850a132c3e`.
- Release `02e3f5da789a23b893111f1ec5899fdcc47443e4` adds sealed-run recovery to
  the two live-derived guards: only a receipt whose source-set matches the
  current inbox receives policy priority, and a sealed `RUNNER_REJECTED` run is
  reusable when the current bundle returns. The source owner completed at
  `2026-08-20T17:10:35Z` with the stable `5da2…` set after the intervening
  `RUNNER_REJECTED / budget_blocked` receipt. The existing composition owner at
  `2026-08-20T17:35:34Z` reused that sealed result and rebuilt the subtitle
  handoff without another model pass or public effect. The next owner policy
  wake at `2026-08-20T17:45:43Z` returned `PASS` with policy SHA
  `63fdb279…`. The subsequent existing loop at `17:50:38Z` created a dedicated
  link with `VERIFIED / deduplicated=false`; the safety gate returned
  `WAITING_FOR_PLACEMENT_LINK` and wrote no public effect. The next same-owner
  wake must re-read the exact link until deduplicated before publication.
- The next bounded P3 bridge is source-implemented but not yet installed: the
  Affiliate owner will read the existing Repost ledger only through
  `AFFILIATE_REPOST_STATE_DIR`, hash and count valid `posted.jsonl` actions, and
  exact-match `campaign-publications/*/x_url`. It will never start or modify the
  Repost owner and it will persist `POST_ACTION_COUNT_ONLY / NO_REVENUE_CREDIT`.
  Read-only inspection of the real Repost state currently shows 46 valid post
  actions, 0 exact Affiliate campaign joins, 46 unjoined actions, and 0 invalid
  rows. The installed b4e owner proof is complete for this observation bridge;
  the later owned-visit/provider-click/transaction join remains open.
- The first natural wake after installing `7598029bd` exposed an independent
  ordering fault: the PartnerStack `Custom links` Playwright selector timed out
  before the late Repost observer could write its receipt. No public effect or
  money was created. The bounded repair moves the read-only observer immediately
  after the wake lock; the next owner wake must show the same Repost counts even
  if provider recovery remains unhealthy. A second small repair keeps an
  unacknowledged observation transition reportable until a matching wake event is
  durable, preventing a provider failure from swallowing its Telegram receipt.
- The `f41140b31` owner wake at `2026-08-20T15:21:09Z` did run the new observer,
  but launchd retained the pre-install environment, so it recorded
  `source_state=NOT_CONFIGURED` rather than inventing a count. The next repair
  prefers `AFFILIATE_REPOST_STATE_DIR` and falls back only when the existing
  `$HOME/loops/x-repost` directory is present; the real read-only file is still
  46 valid actions, 0 exact campaign joins, and 46 unjoined.
- Repository decision: one Life Manager implementation at `skills/affiliate/`; no Affiliate-only repo, executor, ledger, `apps/api`, or Railway runtime. Private mutable state stays under `~/.local/state/life-manager/affiliate/`. OSS is the same proven Skill packaged for a clean Mac, never a rewrite.

## Current measured truth

- Six Affiliate launchd plists exist: three keep-alive browser owners and source/composition/money jobs at 600-second intervals. CDP `9324`, `9326`, and `9327` each returned HTTP `200`; authenticated tabs showed ElevenLabs home, one exact Affiliate X status, and Impact home.
- The canonical ledger contains **20 dedicated-link placements**, **20 matching Affiliate X/public URL placements**, and **34 provider-link clicks across 11 placements**. Only **3/20** exposure denominators are `OBSERVED`; **17/20** remain `INSUFFICIENT_DENOMINATOR`, so ten mature comparable placements are not proven. The latest aggregate ElevenLabs metric is 43 clicks (42 above its baseline); Repost has 51 valid post actions and 51 unjoined actions. None is money.
- PartnerStack/ElevenLabs is `AUTHENTICATED`; the latest official capture at `2026-08-21T06:51:17+0900` has artifact `de2287adc12eaeec8b9760bd6ecd2be2513c1b874f05fc76c27e73969b91d4fe`, `commission_row_count=0`, `NO_LIVE_ROWS`, empty payout rows, currency display `USD`, tax registration required, and payment-provider selection required. Pending/approved/paid/reversed are therefore zero observed rows. No click is money; real billed costs remain unknown.
- B01 remains `WAITING_FOR_PROVIDER_TRANSACTION`: the existing owner reconciled the official artifact at `2026-08-21T06:51:18+0900` with `source_rows=0`, `appended_transitions=0`, and rolling net `NO_TRANSACTIONS / NO_APPROVED_OR_PAID_ROWS / NOT_REACHED`; no official transaction or settlement ID exists to join. A temporary no-network fixture proved the ready path only: one exact `approved` USD row matched one placement, retained settlement/payout fields, and replayed with `0` new / `1` replayed transition. No test payment, estimate, screenshot, model output, click, or unknown cost is promoted to money.
- At `2026-08-21T07:55:09+0900`, the existing owner reached the next revenue-eligible wake but the official PartnerStack cycle failed closed at `stage=links` with `NONZERO_EXIT`, return code `1`, failure receipt hash `ffdaf00e…5309bf`, and retry-after `2026-08-21T08:55:08+0900`. The latest source artifact remains the prior empty hash `de2287adc…b91d4fe`; no new report, transaction, settlement, payout, ledger transition, or money was created. This failure is retained as runtime evidence and is not treated as zero revenue.
- Telegram outbox and sent ledger both have 124 rows with no pending event. The latest owner receipt is provider message `26741` (`CLICK_DELTA`, +1 provider click and no commission); the preceding Repost receipt is `26729`, the earlier click receipt is `26719`, the prior self-heal is `26700`, and the latest Impact rejection remains `26218`.
- The existing-owner replay at `2026-08-21T07:12:35+0900` returned `ALREADY_LIVE` with the same X/public placement, delivered the queued click receipt, and created no transaction; the launchd kickstart command itself returned `141: Reentrancy avoided` while the registered process still ran.
- Release `0473a3fb5` is installed and source-byte verified. The post-install existing owner wake at `07:33:59+0900` produced a real linked `affiliate_telegram_delivery` row with no duplicate external effect; `launchctl` still reports `141` for introspection/bootstrap, so all-owner load status remains an external runtime uncertainty. No direct `local_loop.py wake` was run.
- The source owner still ran at `07:41:55+0900`, but the composition owner log has remained at `07:07:29+0900` with 18 `READY_FOR_POLICY` handoffs waiting. Existing composition `kickstart`, `start`, and direct same-label `bootstrap` each returned `141: Reentrancy avoided`; no composition artifact, public effect, provider link, or money was created by those attempts. The composition-owner activation gate is now an external launchd blocker, separate from the closed Telegram trajectory and B01's empty provider report.
- At `2026-08-21T07:54:44+0900`, the declared existing-owner `launchctl kickstart gui/$(id -u)/ai.anicca.affiliate-loop` retry returned `141: Reentrancy avoided`; `last-run`, the PartnerStack artifact, and `revenue-cycle.json` were unchanged. No direct executor, manual capture, publication, provider link, transaction, or money was substituted. The current session therefore remains launchd-blocked for the next official B01 capture; the prior hash-valid empty artifact is still the only official revenue readback.
- The subtitle experiment now has campaign state `X_LIVE`, owned receipt `LIVE` at Git commit `65445131769663af45e805c6e5bd2174b585276f`, rendered public readback `curl-resolved` with rendered SHA `0481cd7a…`, and X effect `VERIFIED/LIVE`. The exact provider-link key remains `68bf5a04…`; the placement ledger records zero provider clicks and zero commission rows for this placement. Release `207388ecd7` fixed the starvation class by prioritizing in-flight owned receipts before alphabetically earlier campaigns that can return at a new placement-link gate; the natural owner verified the fix without a duplicate external effect.
- The audio-to-text experiment now has campaign state `X_LIVE`, owned receipt `LIVE` at Git commit `543de8c…`, rendered public readback `curl-resolved` with rendered SHA `3b773d77…`, and X effect `VERIFIED/LIVE`; its exact provider-link key is `a308…`. The previous `DELIVERED/OWNED_NOT_LIVE` state closed on the next natural owner wake without a duplicate effect.
- Repost acquisition remains a real broken edge, not a parser miss: the latest observer receipt is `51` valid actions, `0` exact Affiliate campaign joins, `51` unjoined, and `NO_REVENUE_CREDIT`. A read-only comparison still finds no exact campaign join; no row contains the owned domain. D07 therefore remains open until an existing Repost/original-X effect is deliberately joined through owned visit, provider click, and official transaction.
- The first audit-shell DNS readback failed, so those earlier receipts were not
  promoted to public proof. After the owner resumed, independent DNS-resolved
  readback at `2026-08-20T09:01:49Z` returned HTTP 200 for the music owned page,
  its X object, and its Substack object; the receipts are now fresh for that
  trajectory only.

## Current blocker and safe resume

The prior failure was **not** `XPostError`. `last-run.json` reported
`PUBLICATION_FAILED / FileNotFoundError` because the allowed owned-publication
checkout `/Users/anicca/anicca-project/.worktrees/affiliate-foundation-prod` was
missing. The existing `feature/affiliate-foundation-prod` branch is now
reconnected at that exact path from the parent Git repository, at clean HEAD
`d4170db1e`, with the required landing data path present. Both
`launchctl kickstart` and the one-time `launchctl start` fallback initially
returned macOS `141: Reentrancy avoided`. The existing owner later resumed the
music trajectory and verified owned Git `2254ceb73`, X object
`2090363588603236767`, and Substack object `211974858`; the tiktok-transcript
row still has no owned public URL or terminal owner/X receipt. No public effect
was manually performed. Historical ambiguous X effects are already fenced and
must never be republished.

The prior publication slice A04/A05 is complete for the tiktok row: the existing
owner reached its owned/X terminal receipts and an unchanged replay without a
new commit, X object, link, or placement. The durable Instagram job completed
its owned-publication readback and X step at `2026-08-20T14:23:46Z`; the next
execution slice is B01: capture the first non-empty official provider
transaction artifact, retaining the exact provider transaction/settlement
identifiers and truthful empty/unknown states. Do not create a parallel executor
or manually publish.

## Ordered route to completion

1. P0/A04/A05: publication handoff is complete for the current Instagram row;
   retain the owner `LIVE` receipts and unchanged-replay evidence, then move to
   B01 without creating a duplicate effect.
2. E1-H/P1: ingest the first official provider transaction/settlement ID, currency, status and attribution; join one exact placement; replay safely; preserve pending/approved/paid/reversed/reversal lineage; send one natural Telegram receipt.
3. P2: join known real billed costs, preserve unknown, and build the canonical rolling-30-day approved-or-paid net view.
4. P3: turn the existing `@selawmqt` Repost loop into the bounded English Affiliate acquisition arm under one X effect owner; join every credited action through X exposure → owned article → provider click → transaction.
5. P4: execute the admission-dependent three-provider target: HubSpot USD 4,680 gross, Semrush USD 4,200, and ElevenLabs USD 3,621.86 per rolling 30 days. This USD 12,501.86 gross target closes USD 10,000 net only when official approved/paid rows minus observed reversals and known real billed costs prove it. Unapproved providers contribute zero.
6. P5: allocate 80% only from mature approved-net evidence and 20% exploration; turn newly observed failures into bounded same-job `SELF_HEALED` trajectories.
7. P6: continue unattended until the ledger proves at least **USD 10,000 approved-or-paid net in one rolling 30-day period**, after reversals and known real billed costs. Pending, estimates, clicks, screenshots, tests, mocks, dry runs, model output, and unknown costs never count.
8. P7: only after local proof, ship the same `skills/affiliate/` as a secret-free one-command macOS install with verifier, update/rollback/uninstall, redacted fixtures, and one scratch-Mac unattended reproduction. Public language never guarantees that users can “print money.”

Execution update: A01/A02 restored the exact owned-publication worktree at clean
`feature/affiliate-foundation-prod` HEAD `d4170db1e`. A03 enumerated the two
non-public rows (`music` and `tiktok-transcript-generator`) and matched each to
an existing verified PartnerStack placement-link job in the private job journal;
no replacement job was created. A04 remains open because
`launchctl kickstart`, `launchctl start`, and `launchctl asuser ... kickstart`
returned `141: Reentrancy avoided` before the owner later resumed only the music
trajectory; tiktok still has no terminal owner/X receipt.

Because the launchd owner could not be kicked, one installed read-only
`affiliate revenue capture` diagnostic was run. The official PartnerStack report
captured at `2026-08-20T08:49:11Z` was empty (`commission_row_count=0`,
`commission_row_state=EMPTY`, `payout_row_state=EMPTY`), with
`tax_information_state=REQUIRED`, `payment_provider_state=SELECTION_REQUIRED`,
and `currency_display=USD`; artifact SHA-256 is
`114723950748c3df0daf759a9aa5268d2d23f3e9086803bf44e0e71921bf8e5e`. This is
not a transaction or money proof; B01 remains open. The typed A04 blocker is
`BLOCKED_EXTERNAL_141`; no fourth launcher, bootstrap/reload mutation, parallel
executor, or manual publication is allowed.

A later installed read-only capture at `2026-08-20T09:05:47Z` remained empty:
`commission_row_count=0`, `payout_row_state=EMPTY`,
`generic_transaction_id_available=false`, and `normalizer_state=NO_LIVE_ROWS`;
rendered artifact SHA-256 is
`97ad5b45c0fb1b8e8e51889520817814f1a70aee4b610a05eb12bb57ba134d9e`. It is
not a transaction or money proof; B01 remains open.

The subsequent PartnerStack link-performance capture at
`2026-08-20T09:08:27Z` reports 11 provider rows; both music and
tiktok-transcript have current clicks `0` and delta `0`. Rendered artifact
SHA-256 is `9afdda85363faae596a94f9c33114f4280e33c341e74cee4920715520e2a6c51`.
This is a denominator observation only, not money.

The installed read-only commission reconciliation at `2026-08-20T09:10:48Z`
reports `money_state=NO_TRANSACTIONS`, source rows `0`, appended transitions `0`,
and replayed transitions `0`; source artifact SHA-256 is
`97ad5b45c0fb1b8e8e51889520817814f1a70aee4b610a05eb12bb57ba134d9e` and
placement-ledger SHA-256 is
`f3fe1efffafa5f1962990fe36d7854c3c8a196fa23f05fb7c308e9918690de92`. This
does not close A05 because the unchanged owner replay has not been observed.

After the completed music wake, one additional retry of the existing owner at
`2026-08-20T09:11:43Z` again returned `141: Reentrancy avoided`; no Affiliate
loop process was present afterward and tiktok job-events were unchanged. This
remains `BLOCKED_EXTERNAL_141`; no parallel executor was created.

The next owner wake at `2026-08-20T09:12:53Z` reached the source-bound content
gate and failed closed with `ContentError: required source is stale or does not
support its claim`. The official TTS API pricing capture is unexpired and has
separate current v3, v2 Multilingual, and Flash/Turbo rows; the installed
validator still required a removed combined legacy sentence. The pending repair
changes only validator markers in the canonical worktree; no article body,
provider credential, external link, or public effect is changed.

The validator repair is installed as immutable release
`3cdd8d875115b733c6fd9b99e3e296c10e7a5207`; installed `require_sources` passes
all five TTS API sources. The first owner kick after installation at
`2026-08-20T09:17:16Z` again returned `141: Reentrancy avoided`, no loop process
started, and `last-run.json` still shows the pre-repair ContentError. The code
fix is therefore installed/readable but not owner-E2E verified.

The current launchd capability check at `2026-08-20T09:20:57Z` also fails
outside the service label: `launchctl managername`, `launchctl print user/501`,
and `launchctl print gui/501` all return `141: Reentrancy avoided`, while
`id -un` returns literal `501` rather than a username. The GUI/user launchd
domain is not readable from this session; no bootstrap, reload, OS-service
restart, or parallel executor is an honest substitute.

Despite that readback limitation, the existing owner continued its normal
interval. At `2026-08-20T09:23:59Z` it passed the repaired TTS pricing-source
gate and failed closed at policy: `fresh_sources_match_artifact=false` because
the existing deterministic artifact retained pricing hash
`5333196f…f74a21` while the current official capture is
`de2957b4…c4ceec`. The policy receipt had the other four checks true; no owned
or X effect occurred and the placement ledger remained at 13. The pending
repair changes only the builder's artifact-reuse condition to require the
current source-hash map; an isolated replay proved source rebinding and
five-check policy PASS. It is not yet installed or owner-E2E verified.

The source-hash repair is now committed as `b4fa82c6e` and installed as
immutable release `b4fa82c6e0321f85820f56a3e78b357856632a1e`; installed
`content.py` compiles and the isolated stale-artifact replay passes policy.
The post-install existing-owner kick at `2026-08-20T09:29:47Z` again returned
`141: Reentrancy avoided`; no parallel executor or manual publication was
created, and `last-run.json` remained the pre-install policy failure at that
moment.

The existing owner then naturally ran the installed release. Its policy receipt
at `2026-08-20T09:34:48Z` was `PASS` with all five checks true; the wake ended
at `2026-08-20T09:35:32Z` as `ALREADY_LIVE` with the unchanged X status
`2088809159932465497`. The owned receipt is `LIVE`; independent DNS-resolved
HTTP readback returned `200` for both owned and X, and the body checks found the
owned title/disclosure and X status ID. Telegram message `25964` is the owner
receipt. Revenue stayed `NO_TRANSACTIONS` (`0` rows, `0` transitions), and the
ledger stayed at 13 placements. This proves the source-refresh repair through
the real owner and duplicate-free replay. A04 still remains open because the
tiktok-transcript placement has no public URL. Its historical `budget_blocked`
composition run is superseded: the same plan now has a `READY_FOR_POLICY`
composition receipt and `PASS` campaign policy for source set `ee8d…`. The
publication progress remains `MATERIALIZED` with stale handoff fingerprint
`c116…` versus current `546…`, and neither owned nor X has a receipt. An
isolated replay verified that only this effect-free stale materialization
rebinds; unchanged replay is `ALREADY_LIVE`, while any existing owned receipt
remains `PUBLICATION_CONFLICT` with zero effect calls. The repair is in the
worktree and is installed as immutable release `7147038b3`; the next owner
result is recorded below.

The next installed owner wake began at `2026-08-20T09:45:37Z` but exited before
writing a wake receipt: Playwright raised `TimeoutError` while waiting for the
PartnerStack `Custom links` control in `elevenlabs_link_action`. Both existing
TTS and tiktok link receipts remained `VERIFIED`; no owned/X receipt or public
effect was created, and the tiktok materialization was unchanged. The pending
repair catches only this typed Playwright timeout, reuses the exact verified TTS
local receipt with provider readback pending, and leaves unknown browser errors
fail-closed. Compile and 19 focused tests pass. It is installed in `7147038b3`;
the exact timeout reuse branch has not been independently induced.

The existing owner wake at `2026-08-20T09:57:02Z` executed the materialization
repair. Tiktok progress now carries current handoff fingerprint `546…` and
`rebound_from_handoff_fingerprint=c116…`; the existing PartnerStack link key
`618843f9…` was deduplicated, and owned Git commit `2250d31a6` was delivered
through the configured `affiliate-foundation-prod` checkout to `origin/main`.
The first immediate Netlify/public readback was HTTP `404`, so the owner
recorded `OWNED_NOT_LIVE`, sent Telegram `25979`, and created no X effect. A
later independent DNS-resolved readback at `2026-08-20T10:01:12Z` returned
HTTP `200` for the exact owned slug and found the expected title, affiliate
disclosure, and dedicated-link anchor in the response body. The durable
receipts have not yet been advanced by the owner: progress remains
`OWNED_NOT_LIVE`, the owned receipt remains `DELIVERED` without a public URL,
and no X receipt exists. The existing launchd owner must perform that
readback, then reach X `LIVE`, with unchanged replay; A04 remains open.

After the DNS readback repair was installed as immutable release
`de63ee69057681606c8d508dcc7dd99947949208`, the existing owner wake at
`2026-08-20T10:08:45Z` advanced the same tiktok job to `X_LIVE`. The owned
receipt is `LIVE` at the exact slug, with rendered hash `9f430685…a3bf`; the X
receipt is `LIVE` at status `2090380444655370568`. Independent DNS-resolved
HTTP readback returned `200` for both owned and X pages; the owned body
contains the title, affiliate disclosure, and dedicated-link anchor, while X
contains the canonical status ID. The campaign progress carries one existing
provider link key `618843f9…` and one X receipt; no second external effect was
created. Provider clicks for this placement remain `0`, the canonical ledger
remains 13 placements, and official commission rows remain `0`, so
approved-or-paid net remains USD `0` and actual billed cost remains `UNKNOWN`.

The same wake could not flush its first pending Telegram event: OpenClaw
`message send` timed out after 30 seconds before returning a provider message
ID. The installed repair is commit
`088858bce2965f05783448b4b5f829fa053717ee` (`SEND_TIMEOUT_UNKNOWN`), which
preserves the event in the outbox and the unresolved effect fence without
claiming `SENT`; it is installed as the current immutable release, but its
owner retry has not yet produced a new Telegram message ID. The pending event
is the older unattributed-click report, not a commission receipt. A04's
unchanged replay and Telegram receipt proof remain open at this point in the
timeline.

The existing owner replay at `2026-08-20T10:20:05Z` then returned
`ALREADY_LIVE`. Tiktok campaign, owned, X, and provider-link receipt hashes
stayed byte-identical to the pre-replay baseline; owned Git HEAD remained
`2250d31a6`, the provider link key remained `618843f9…`, the ledger remained at
13 placements, and independent owned/X readback remained HTTP `200`. The
older unattributed-click Telegram event was sent as message `25997`, leaving
the outbox and sent ledger with 96 rows and no pending event at that moment.
The next owner-generated `PLACEMENT_LIVE` receipt is tracked under B08; no
Telegram receipt is treated as money.

This handover records no Codex manual publication, provider write, or ledger
mutation. The installed owner performed the verified music delivery described
above; Codex did not create a parallel executor.

Fresh `@selawmqt:9326` read-only revalidation of X's canonical Article route
returned `Page not found` with zero editor controls. This is a current capability
observation, not a permanent claim; Writer's working X Article belongs to the
separate `@diceai0` identity and is not proof for the Affiliate account.

At `2026-08-20T10:31:14Z`, the existing launchd owner completed another wake as
`ALREADY_LIVE`. `launchctl` introspection and `start`/`kickstart`/`bootstrap`
returned `141: Reentrancy avoided`, but the configured bootstrap still started
the owner process; no parallel executor was created. The owner flushed the
pending tiktok `PLACEMENT_LIVE` event once as Telegram provider message `26004`.
The tiktok campaign, owned, X, and provider-link receipts remained byte-identical
(receipt hashes `933a61…`, `aaef09…`, `16c4c4…`, `280f92…`); landing Git HEAD
remained `2250d31a6`, the ledger remained 13 placements, and DNS-resolved public
readback returned HTTP 200 with the expected owned title/disclosure/link marker
and X status marker. Telegram outbox/sent are both 97 rows with no pending row.

The `10:31` checkpoint's official PartnerStack artifact was empty
(`commission_row_count=0`, `NO_LIVE_ROWS`, `payout_row_state=EMPTY`,
`generic_transaction_id_available=false`, artifact SHA-256 `6bb1c9…`). At that
checkpoint the canonical placement ledger recorded 30 provider-link clicks,
while aggregate provider metrics showed 41 clicks with `+40` unattributed; no
click was money. There were zero official pending/approved/paid/reversed
transaction rows, approved-or-paid net was USD `0`, and real billed cost was
`UNKNOWN`.

The next cooldown-eligible owner wake at `2026-08-20T10:43:22Z` refreshed the
official PartnerStack report at `10:43:19Z`: `commission_row_count=0`,
`payout_row_state=EMPTY`, `normalizer_state=NO_LIVE_ROWS`, artifact SHA-256
`a0cf2e5d2924069a1e4d0fd534506fa9b3b9f680debb6b763ca180d7c59495ca`.
Reconciliation remained `NO_TRANSACTIONS` with source rows `0`, appended
transitions `0`, and replayed transitions `0`. The canonical ledger now has 32
provider-link clicks and zero transaction rows; aggregate metrics remain 41 with
`+40` unattributed. The owner appended one new durable `CLICK_DELTA` event for
the music/voice-cloning deltas, then its Telegram send returned
`SEND_TIMEOUT_UNKNOWN` without a provider message ID; outbox is 98, sent is 97,
and the event remains pending for the next existing-owner retry. Approved-or-paid
net is USD `0`; real billed cost is `UNKNOWN`; B01 remains open.

The existing owner retry at `2026-08-20T10:54:48Z` recovered the exact pending
`CLICK_DELTA` event without changing any publication, link, provider, or ledger
receipt. Event UUID `4d674b7e14538be7e70cb00c236a8e1bc5153e68a29bf5b4cde0e4452a6a9bf8`
was recorded once with Telegram provider message `26019`; outbox and sent ledger
are both 98 rows with zero pending rows. Revenue remained in cooldown against
the 10:43 empty capture; approved-or-paid net remains USD `0` and billed cost is
`UNKNOWN`. Independent DNS-resolved readback after this retry still returned
HTTP 200 for owned and X pages with the expected markers; tiktok receipt hashes,
landing HEAD `2250d31a6`, and the 13-placement ledger were unchanged. This closes
the observed Telegram timeout self-heal, not B01.

The installed revenue normalizer was audited read-only and its existing focused
suite passed 8/8. It maps provider `pending|hold`, `approved|scheduled`, `paid`,
and `declined` to canonical statuses, retains USD minor/reversal units, and
derives a stable transition identity for replay. This is harness readiness only;
the official report has no live rows, so no fixture or test value advances B02,
B03, or the USD 10,000 gate.

At `2026-08-20T11:17:12Z`, release `260e57098209eaef8f412532af5284ed6a000d65`
was installed as the immutable Affiliate runtime. The new `AFFILIATE_ROLLING_NET`
receipt runs inside the existing owner wake and is fail-closed: it deduplicates
by provider plus transaction ID, binds the commission-ledger SHA-256, lists
in-window transaction-to-placement joins, preserves pending/approved/paid/
reversed and reversal units, and refuses a qualifying USD net when an economic
row is unjoined, FX is missing, real billed costs are missing/invalid, or the
cost window is not explicitly complete. Direct installed readback found no
`commission-ledger.jsonl` and returned `money_state=NO_TRANSACTIONS`, zero rows
in every status, `net_state=NO_APPROVED_OR_PAID_ROWS`,
`threshold_state=NOT_REACHED`, `approved_or_paid_net_usd=null`,
`cost_state=UNKNOWN`, `cost_coverage_state=UNKNOWN`, and receipt SHA-256
`3e77dc1a027bb1e436f14170945c4a84a9ebdaf6eeb3fa20641f42c1035df074`.

The existing `ai.anicca.affiliate-loop` owner was the only runtime executor.
`launchctl start`, `kickstart`, `asuser kickstart`, `bootstrap`, and a target-only
bootout/bootstrap resync each returned macOS `141: Reentrancy avoided`, but the
owner later produced one real wake from the new release. `last-run.json` records
`rolling_net_state=ROLLING_NET_READY` and the same empty/unknown states above.
The owner emitted one natural-language `AFFILIATE_ROLLING_NET` Telegram receipt
as provider message `26044`, event UUID
`72557ed6beb878b70a844c3e1fda8862e284af9a20b2287752e56b1e0b3fb8e6`; Telegram
outbox and sent ledgers are both 100 rows with zero pending. No publication,
provider-link, transaction, settlement, or ledger money effect was created.

C05 is now executable wiring but remains open for the first real transaction,
exact placement join, complete real-billed-cost coverage, and replay proof. B01
remains the next external gate; current approved-or-paid net is USD 0 and the
USD 10,000 rolling window is not reached.

Codex sent milestone Telegram message `26047` with the same release, owner
readback, zero-money result, and B01 next gate. The message contains no secret or
raw tracking link.

The canonical placement ledger repair is release
`f15ca3ceb48fb0312f5041002b139cef98c0768c`, installed after the rolling-net
owner proof. It reuses provider-scoped latest transitions and requires
`placement.state=MATCHED` before per-placement commission counts or net totals
are included. An isolated two-provider/same-transaction-ID fixture counted the
one exact matched row and excluded the unmatched row; the existing revenue
focused suite remains 8/8. The post-install owner trigger returned `141` and no
new `last-run` receipt had appeared by `2026-08-20T11:23:30Z`; the previous
`260e57098` owner proof remains valid for rolling-net wiring, while the new
placement-ledger repair awaits its own existing-owner readback. B01 remains the
next external gate and no money is counted.

Release `0f29dc81fabbe6d9271dddfe130463a56f879bbb` then bound
`AFFILIATE_ROLLING_NET` to the exact `placement-ledger.json` SHA-256 in addition
to the commission-ledger SHA-256. It is installed as current; the post-install
owner start at approximately `2026-08-20T11:25Z` again returned `141` and no
new wake was visible yet. This is evidence-chain hardening only, not a money
event. The next owner readback must show the new placement-ledger hash before
this slice is considered live-verified.

The placement-ledger hash was initially included in the Telegram event identity,
which made the `11:28` owner wake create same-content event UUID
`0a79a537d618f563d5b604d7e003165ef8cb2e5116a754f70cd360fed30e806c`; its
OpenClaw send ended `SEND_TIMEOUT_UNKNOWN` with no provider message ID. This
was a duplicate-event risk, not a money event. Release
`cd7372f45a7ae57a26489679d004d5e77708321d` removes only that volatile hash from
the Telegram identity while retaining the hash in the local rolling receipt.
An isolated replay with two different placement-ledger hashes now returns the
same event UUID, and an already-sent UUID returns no new event. The pending row
must be retried by the existing owner under its original UUID; no duplicate or
Telegram receipt is claimed until message ID readback exists.

The existing owner wake at `2026-08-20T11:40:09Z` ran release `cd7372f45` and
verified the stable-identity repair. The rolling receipt bound placement-ledger
SHA `98573449c5812b6117c89d86acafe7cdb83d8c01a4f92d2bd57861bc40b2b1d8`, kept
`NO_TRANSACTIONS / NO_APPROVED_OR_PAID_ROWS`, and retried pending event UUID
`0a79a537d618f563d5b604d7e003165ef8cb2e5116a754f70cd360fed30e806c` exactly
once as Telegram message `26077`. Outbox and sent are both 101 rows with zero
pending; no new rolling event was generated. The duplicate-identity
self-heal is now live-proven. B01 remains the first non-empty official provider
transaction gate and no money is counted.

The next revenue-eligible owner wake completed at `2026-08-20T11:51:48Z`.
Official PartnerStack capture observed at `11:51:46.626744Z` remained empty:
`commission_row_count=0`, `commission_row_state=EMPTY`,
`payout_row_state=EMPTY`, `normalizer_state=NO_LIVE_ROWS`, artifact SHA
`6567be531f2e6fae780ce6693c8002ee099d4e11231558695ed120dd2261251f`.
Reconciliation at `11:51:47.894387Z` recorded
`NO_TRANSACTIONS / source_rows=0 / appended=0 / replayed=0`. The owner then
wrote rolling receipt SHA `9d9aa493ebf81b7c0a24e78e467d31af0b21568d6f6ab29b9318b414c7d1ff91`
with zero status rows, null USD net, `threshold_state=NOT_REACHED`, and
placement-ledger SHA
`631ff2733181ff178069e068dbff37209682cabf4ff4b5567d1a1d9c0f6a671c`.
The canonical ledger is still 13 placements, 32 provider-link clicks, and zero
transactions. Telegram remained 101/101 with no pending event. B01's required
first non-empty transaction is still open; this empty capture is not money.

Codex sent the empty-capture milestone as Telegram message `26099`, including
the official artifact hash, zero reconciliation counts, zero rolling net, and
the next B01 gate. It contains no secret or raw tracking link.

At `2026-08-20T12:46:27Z`, the fourth DEV.to baseline decision exposed a stale
private machine receipt: it pinned removed Codex `0.147.0`, while the requested
`/Users/anicca/.local/bin/codex` resolved to the current `0.148.0` release. The
new binary's `--version` also wrote a benign no-HOME warning, which the strict
inventory treated as rejection. Commit `649f474cf175f19d21e363856c42bdf1d9bedd43`
changes only the verifier: it probes the fixed binary inside a temporary
mode-0700 HOME and still rejects non-zero exit, stderr, version mismatch, or
file mutation. Capability focused checks passed `6/6`; the existing revenue
focused checks passed `8/8`. The private receipt now records Codex `0.148.0`
at the canonical 0.148.0 release with SHA `b0308517…1e50`.

The canonical `skills/affiliate/scripts/install-release.sh` then atomically
created release `649f474cf175f19d21e363856c42bdf1d9bedd43`, switched `current`,
and wrote its ownership receipt. Its first browser bootstrap retry stopped with
`141: Reentrancy avoided`; no browser, provider, public, Telegram, or ledger
effect was manually substituted. The existing loop owner nevertheless ran the
new release at `2026-08-20T12:46:56Z`. Baseline SHA
`c4012766…0072` now has acquisition decision `READY`, decision ID
`99721872…89ad`, selected variable `title`, runner exit `0`, a sealed private
evidence tree, and a verified Codex binary pin. `last-run.json` no longer says
`RUNNER_REJECTED`; owner Telegram message `26171` is read back, and Telegram
outbox/sent are both `102/102` with no pending row. This closes the capability
and acquisition repair only.

The same owner readback still finds the official PartnerStack report empty
(`commission_row_count=0`, `NO_LIVE_ROWS`, no payout rows). The rolling receipt
remains `NO_TRANSACTIONS / NO_APPROVED_OR_PAID_ROWS`,
`approved_or_paid_net_usd=null`, `cost_state=UNKNOWN`, and
`threshold_state=NOT_REACHED`; no click, model token, estimate, pending reward,
or Telegram receipt is money. B01 remains the next gate: capture the first
official transaction/settlement artifact and join it exactly to one placement.

After the revenue cooldown elapsed at `2026-08-20T12:52Z`, one existing-owner
kickstart and read-only `launchctl` variants with and without XPC metadata all
returned `141: Reentrancy avoided`; `last-run.ts` and the official report did
not advance. No fourth launcher, manual provider capture, OS-service restart,
or public effect was created. This is the current external launchd observation
gate; B01 and the USD 10,000 threshold remain open.

Commit `b348a933fcb406216923add8945c2b6b89af4022` adds typed, retryable
`ACQUISITION_DECISION_FAILURE` receipts for pin rejection, budget block (exit
`75`), invalid config (exit `2`), timeout, and runner start failure, plus a
stable `ACQUISITION_DECISION_FAILED` Telegram event with no public or money
claim. Isolated temporary-state fixtures passed all classifications and
same-failure dedupe. The canonical installer switched current to this release,
but its browser bootstrap again stopped at `141: Reentrancy avoided`; the
existing READY baseline receipt remains unchanged and no artificial failure
receipt or manual owner run was created.

Read-only placement readback confirms the earlier durable campaign-seven run is
complete and no replacement is needed: the canonical ledger has 13 English
placements, 13 dedicated provider-link keys, 13 owned `LIVE` receipts, and 13
X `LIVE` receipts. D01 and D03 are therefore closed in the SSOT. This is
publication and denominator readiness only; every placement still has zero
official transaction rows and no amount is money.

The existing owner then woke naturally at `2026-08-20T12:58:36Z` despite the
earlier launcher `141` responses. Official PartnerStack readback at
`12:58:35.798870Z` remained empty (`commission_row_count=0`, `NO_LIVE_ROWS`, no
payout rows; artifact SHA `8418d228…af0c4`). The owner rolling receipt stayed
`NO_TRANSACTIONS / NO_APPROVED_OR_PAID_ROWS / NOT_REACHED`; the canonical ledger
is 13 placements, 32 provider-link clicks, and zero transaction rows. Telegram
outbox/sent are `102/102` with no pending row. Codex milestone message `26199`
confirms this state without secrets or raw tracking links. B01 remains open.

Follow-up source commit `792f483eb028cb1c7886f75571515e3616337297` changes only
owner-event precedence: a durable `ACQUISITION_DECISION_FAILED` receipt now
prevents the same wake from emitting an unrelated generic `BLOCKED` event, while
keeping stable failure identity and no-public-effect wording. Isolated pin,
budget, invalid-config, timeout, start-failure, and failure-priority/dedupe
fixtures plus focused inventory/revenue/acquisition checks passed `15/15`. The
installer switched `current` to this release but again stopped at browser
bootstrap `141: Reentrancy avoided`; the existing owner nevertheless woke
naturally at `2026-08-20T13:09:27Z` and read back `ALREADY_LIVE`, 13 placements,
rolling net `NO_TRANSACTIONS / NO_APPROVED_OR_PAID_ROWS / NOT_REACHED`, and no
Telegram pending row. No manual executor, provider capture, public effect, or
money claim was created. Codex sent the readback milestone as Telegram message
`26211`.

Follow-up source commit `cc775c3744094edf99087023ae36f3deb0936640` repairs the
Impact playbook drift: the authenticated page title `Impact - Welcome` is now a
valid provider tab, and `HubSpot, Inc. application` plus `Declined` classifies as
`REJECTED / DO_NOT_RESUBMIT`. A live CDP readback at
`2026-08-20T13:20:15Z` and a temporary poll produced the expected state and a
deterministic transition ID without touching production state. The installer
switched `current` to cc775c374 but stopped at browser bootstrap
`141: Reentrancy avoided`; the existing owner still needs to persist this
rejection and emit its deduplicated program receipt. No HubSpot link, public
effect, or money was created.

The existing owner then woke at `2026-08-20T13:19:58Z` and completed E01. The
production Impact receipt is `REJECTED / DO_NOT_RESUBMIT`, `changed=true`, with
transition `14d9b1aa896bd493ad698b795248150f594cc67105276d025e5fb9051c765cb6`
and marker hash `c335ed63…9274`; owner Telegram message `26218` reports the
negative program transition. Rolling net remains
`NO_TRANSACTIONS / NO_APPROVED_OR_PAID_ROWS / NOT_REACHED`; the canonical ledger
is still 13 placements, 32 provider-link clicks, and zero transaction rows.
No HubSpot link, public effect, or money was created. B01 remains the first
official transaction gate.

The current Semrush official page was read-only reviewed at
`2026-08-20T13:28Z`: it states a 120-day last-click cookie, $10 per eligible
trial, $50-$300 basic-tier sales with up to $450 loyalty tiers, a 1,000-monthly-
unique-visitor or significant-organic-social threshold, Impact dashboard
tracking, EFT/PayPal payout, FTC disclosure, and self-referral prohibition.
The Impact-hosted terms/report artifact and TTL-bound local capture are still
missing, so E02 remains open and no application/link was submitted. The target
table now labels HubSpot rejected and the former USD 12,501.86 three-provider
mix as a scenario rather than current money; current executable provider count
is one.

A second read-only fetch at `2026-08-20T13:47:12Z` returned the same official
Semrush page. The page's sign-up/terms link redirected through Impact and failed
with a redirect-loop response, so the Impact-hosted terms/report artifact and a
TTL-bound local capture remain unavailable without an admitted authenticated
program; no application or executable link was attempted.

Read-only official-source refresh at `2026-08-20T13:52:19Z` clarified the two
commerce exploration gates. Amazon Japan's current fee table is 0%--10% by
category (PC/camera/home-electronics/musical instruments 2%; books/stationery
3%); review requires three qualifying sales within 180 days, excludes self
orders, checks all submitted public surfaces, requires at least ten original
public posts, and states that SNS usually needs about 500 organic followers or
likes. Shipment is required before an eligible sale, payment is about 60 days
after month end, and bank transfer requires JPY 5,000. Rakuten's public guide
shows category-dependent rates, a JPY 1,000 per-item cap, `発生`/`確定`/`未確定`/
`破棄` report states, confirmation at the following month end, and Rakuten Cash
payment on the following month's 10th; one yen is usable, while bank transfer
requires screening and three consecutive months at JPY 3,001 or more. These
facts update the SSOT only; no login, application, link, public effect, order,
or money was created. Both providers remain USD 0 until their own official
approval, exact placement join, confirmed/paid receipt, reversal, and cost
coverage are present.

The Semrush admission-gate refresh was committed and pushed as
`206b1145cc81d72137ff8fda53e08e94bd2d2b0e`. The immutable installer switched
`current` to that release, then stopped at the known launchd browser bootstrap
`141: Reentrancy avoided`; no parallel executor was started. The existing owner
naturally woke at `2026-08-20T13:30:33Z` and read back the same durable Impact
`REJECTED / DO_NOT_RESUBMIT` transition, `ALREADY_LIVE` publication, 13
placements, `NO_TRANSACTIONS / NO_APPROVED_OR_PAID_ROWS / NOT_REACHED`, and no
new Telegram event because the state was deduplicated. E02 remains open; B01 is
still the next money gate.

Source repair `eb771cf61006276bac06ab0d044b9edf1043bb41` changes only
composition retry semantics: a stale preflight-only `RUNNER_REJECTED` with no
evidence tree can retry the same durable job once after the capability receipt
changes; budget-blocked and evidence-bearing failures remain terminal. Compile,
the existing composition focused checks `4/4`, and private state verification
passed. The immutable installer switched `current`; the main money owner then
naturally woke at `2026-08-20T13:40:53Z` and retained `ALREADY_LIVE`, 13
placements, and rolling zero. Despite the direct label commands returning
`141: Reentrancy avoided`, the existing composition owner naturally retried the
same Instagram job at `2026-08-20T13:43:25Z`, sealed evidence with Codex
`0.148.0`, exit `0`, and wrote `READY_FOR_POLICY`. No public effect, provider
transaction, or money was created; publication remains the next owner gate.

The next natural money-owner wake at `2026-08-20T13:51:10Z` was a duplicate-safe
readback: `READY_FOR_PUBLICATION`, `ALREADY_LIVE` on the existing X status, a
verified/deduplicated ElevenLabs placement link, and revenue cooldown. Private
ledger readback shows 13 placements, 13 owned public URLs, 32 provider-link
clicks, zero transaction rows, and zero approved/paid/pending/reversed statuses.
Rolling net remains `NO_TRANSACTIONS / NO_APPROVED_OR_PAID_ROWS / NOT_REACHED`,
approved-or-paid net is null, actual cost/coverage remain `UNKNOWN`, and
Telegram has no pending event. This closes no money gate and creates no new
external effect.

B01 was checked without a new executor at `2026-08-20T13:57:45Z`: the existing
revenue checks passed (`test_revenue_cli` 8/8, `test_local_loop` 16/16, and
Python compilation). The latest official PartnerStack artifact remains
`commission_row_count=0 / NO_LIVE_ROWS / payout_row_state=EMPTY` with USD
display; reconciliation appended zero transitions and rolling net remains
`NO_TRANSACTIONS / NO_APPROVED_OR_PAID_ROWS / NOT_REACHED`. This is the absence
of an external conversion/report row, not money and not a parser pass-through.
The first row still must carry the official reward key, lifecycle status,
amount/currency, attribution key, exact placement join, and replay-safe
transition before B01 can close.

The provider-namespace replay repair is installed as immutable release
`e842fb8759a7f3ed315e5f2dce0817072d4afc9f`; source byte equality and all three
CDP version endpoints passed. The installer again stopped at launchd bootstrap
`141: Reentrancy avoided`, but the existing owner naturally ran that release at
`2026-08-20T14:02:15Z`: PartnerStack capture/reconcile executed with zero
commission rows and zero appended transitions, and rolling net stayed
`NO_TRANSACTIONS / NO_APPROVED_OR_PAID_ROWS / NOT_REACHED`. The same durable
Instagram transcript job acquired one verified private provider link and
stopped before publication, leaving 14 placements, 13 owned public URLs, 32
provider clicks, and one link-only row. No public effect, transaction, or money
was created; the next wake owns the policy/publication handoff.

The X rendered-DOM readback repair is commit `97d143d7908b05ee4261e83c85d41818c3478c04`.
It adds the browser-rendered exact owned URL as a fallback when a `t.co` anchor
cannot be resolved by Python HTTP/DNS; it does not weaken the disclosure,
status-URL, or content-prefix checks. Existing X contract checks and Python
compilation passed. A direct read-only replay through the existing authenticated
X tab verified all five historical `XPostError` liveness rows as exact `LIVE`
readbacks; no compose, click, or post call was made. The immutable installer
switched `current` to that release, source byte equality passed, all three CDP
version endpoints remained `Chrome/145.0.7632.109`, and only the known launchd
bootstrap `141: Reentrancy avoided` was returned.

The existing money owner then naturally woke at `2026-08-20T14:12:51Z` on the
new release. It preserved the 14-row canonical ledger, 32 provider clicks, zero
official commission rows, `NO_TRANSACTIONS / NO_APPROVED_OR_PAID_ROWS / NOT_REACHED`,
unknown costs, and no Telegram pending event. It advanced the same Instagram
campaign to an owned Git `DELIVERED` receipt with commit `b1452826b`; the receipt
has no public URL yet, and no X effect was attempted. A separate read-only
`owned_publish.fetch_readback` call returned `LIVE_READBACK` using the
`curl-resolved` transport with a rendered-body hash, proving the public article
is live while leaving the owner receipt untouched. The next natural owner wake
must promote that existing receipt and only then perform the single X step.

The liveness receipt still lists the five historical X failures because its day
is already `2026-08-20` and the owner correctly remains in same-day cooldown;
Codex did not rewrite that mutable receipt. The next JST-day sweep should use
the installed DOM fallback and clear the stale false negatives. B01 remains
open: the official PartnerStack report still has zero commission rows and no
transaction/settlement ID that can be joined to a placement.

The following existing-owner wake completed that handoff at
`2026-08-20T14:23:46Z`. The same Instagram job promoted the owned receipt to
`LIVE`, published one X post with an exact readback, and sent Telegram message
`26282`; no replacement placement, link, or post was created. The canonical
ledger is now 14 placements, 14 owned public URLs, 32 provider-link clicks, and
zero approved/paid/pending/reversed commission rows. Revenue remains
`NO_TRANSACTIONS / NO_APPROVED_OR_PAID_ROWS / NOT_REACHED`, actual cost and
coverage remain `UNKNOWN`, and no Telegram event is pending. P0 publication
handoff is closed; B01 is the next atomic task: wait for a non-empty official
PartnerStack transaction/settlement row and exact-join it replay-safely to one
of these placements.
The next B01 repair is commit `9e8f7b90f4392966080edad9b29ff313d81318ae`.
The commission transition identity now includes the attribution and placement
join receipt in addition to provider, provider transaction key, lifecycle
status, currency, gross, reversal, and net units. This prevents a real provider
reward first observed as `UNMATCHED` from being permanently replay-deduped when
a later poll supplies the exact sub-ID/link placement; replaying that matched
state still appends zero duplicates. Existing revenue checks `8/8`, local-loop
checks `16/16`, Python compilation, and the inline unmatched→matched→replay
fixture passed. The immutable installer switched `current` to this release and
source byte equality passed; browser bootstrap still returned only the known
`141: Reentrancy avoided`, so the next natural owner wake is required for
installed proof. The official provider report remains empty and no money was
created.
The follow-up B01 repair is commit `c8f6e4a1b9c4a83b8789b5eaa5da4e8589b7b0f0`.
It preserves row-provided ISO currency and optional provider settlement/payout
identifiers, and includes those identifiers in replay identity so a later payout
readback cannot be silently deduped. Existing revenue checks `8/8`, local-loop
checks `16/16`, Python compilation, and a non-persistent currency/settlement
identity fixture passed. The immutable installer switched `current`; source byte
equality and all three CDP version endpoints passed, browser bootstrap again
returned only `141: Reentrancy avoided`, and the existing owner naturally ran at
`2026-08-20T14:45:03Z` with `ALREADY_LIVE`, revenue `COOLDOWN`, no fresh capture,
zero observed rows, and no duplicate effect. The first official transaction and
exact placement join remain open.
The follow-up B01 receipt repair is commit `be76c390d15b664326d2329d6af669b4696ad8db`.
Commission Telegram events now state provider, official transaction key,
exact placement ID or `UNKNOWN`, status, gross, reversal, net, currency, and
optional settlement/payout IDs without exposing tracking links. Existing
revenue checks `8/8`, local-loop checks `16/16`, Python compilation, and a
non-persistent receipt-field fixture passed. The immutable installer switched
`current`; source byte equality passed, browser bootstrap again returned only
`141: Reentrancy avoided`, and the existing owner naturally ran at
`2026-08-20T14:55:19Z` with `ALREADY_LIVE`, revenue `COOLDOWN`, no fresh capture,
zero observed rows, no duplicate effect, and no pending Telegram event. The
first official transaction and exact placement join remain open.

E02 was revalidated read-only on `2026-08-21` against the official Semrush
English program page and Japanese KB. They currently state 120-day last-click
attribution, $10 eligible trials, product/tier sale commissions up to $450,
first-purchase/new-user attribution, a 2+ hour report delay, Impact tracking,
EFT/PayPal withdrawal, transaction locking 27 days after month end and payment
21 days after locking, FTC disclosure, and self-referral/cookie-stuffing
prohibition. The public admission gate still requires a relevant public
property and generally at least 1,000 monthly unique visitors or significant
organic social audience. The Impact terms/report route remains a redirect loop
outside an authenticated program; CRWL independently failed with Chromium
`bootstrap_check_in` 141 and scrapy failed DNS resolution for the English,
Japanese, and official URLs. Therefore E02 stays `PARTIAL /
WAITING_FOR_LOCAL_TERMS_CAPTURE`; no application, Semrush link, click, or money
was created. Sources: <https://www.semrush.com/lp/affiliate-program/en/> and
<https://ja.semrush.com/kb/97-affiliate-program>.

The existing owner then completed one new PartnerStack placement-link effect at
`2026-08-21T03:56:04Z` for the voice-isolator experiment. Its journal is
`EFFECT_STARTED → VERIFIED`, while the same campaign handoff/policy receipts
remain `READY_FOR_POLICY`/`PASS`; the one-effect-per-wake fence therefore did not
attempt publication in that wake. The canonical ledger is now 18 dedicated links,
17 public placements, 32 provider clicks, and 15 `INSUFFICIENT_DENOMINATOR` rows.
The next owner wake must resume this same job for owned/X readback. B01 is still
cooldown/empty: no official transaction, settlement, payout, commission, or net
was created.

The next owner wake at `2026-08-21T04:06:43Z` resumed that same campaign and
verified the owned Git push (`4c42cb1…`, state `DELIVERED`). The independent public
readback remained unavailable, so the publication receipt stayed `OWNED_NOT_LIVE`
and no X effect was attempted. At `2026-08-21T04:17:31Z`, the owner attempted the
same X handoff after the public deploy receipt was promoted; its authenticated
timeline readback returned `NOT_FOUND` and the durable job
`e5399f85…` remained `EFFECT_STARTED`, producing the truthful
`PUBLICATION_FAILED / XPostError` detail “X effect is ambiguous; retry will
reconcile timeline.” The canonical ledger readback is 19 rows: 18 provider-link
keys, 18 owned public URLs, 32 provider clicks, 16 insufficient plus 3 observed
Dev.to denominators, and zero official commission rows. The experiment currently
has a provider-link row with placement suffix `-1` and a separate owned-only row;
it is not an exact placement join and no money is credited.

Codex repaired the observed retry dead-end in `4dc7c6be2` and pushed it to both
`origin/docs/affiliate-life-manager-spec` and `canonical/docs/affiliate-life-manager-spec`.
The installed immutable release is the full SHA
`4dc7c6be2d0fe9f9ad15ca4f56ff461b049474a6`, with `LOCAL_READY` ownership receipt
and byte-equal `current` symlink. The repair reads the X timeline before any
retry, reconciles an exact post by placement, resumes only the same unresolved
job after its 3,600-second cooldown, and refuses a new compose effect while the
fence is cooling down. Existing checks and the temporary journal fixture passed;
the install stopped only at the known launchd `141: Reentrancy avoided` bootstrap
warning, while CDP ports 9324/9326/9327 stayed ready. The next natural owner wake
must verify cooldown readback without a duplicate post; once eligible around
`05:17 JST`, it may resume that same job identity. B01 remains empty:
`NO_TRANSACTIONS`, approved/paid net null, and actual cash cost unknown.

The Codex owner receipt for this repair was sent as Telegram `messageId=26583`.
After the install, read-only `launchctl print` failed for the Affiliate label,
the whole `gui/$(id -u)` domain, and the `system` domain with
`141: Reentrancy avoided`; `managerpid` also failed. A declared
`kickstart` of the existing `ai.anicca.affiliate-loop` and a direct bootstrap of
its existing plist both returned the same 141, while CDP ports 9324/9326/9327
remained ready. No direct loop executor was started and no external post or
provider action was fabricated. This is an indispensable local launchd-session
capability blocker for the next real X timeline readback and B01 capture; the
smallest truthful recovery action is to recreate the user launchd session (log
out/in) and then let the existing owner run. The authenticated job journal now
records `VERIFIED/LIVE`, but the terminal `x-posts` public-readback receipt is
still absent until the new release gets one successful final status-page readback;
the placement is therefore not terminal `X_LIVE`, the split placement is not
joined, and money stays `NO_TRANSACTIONS` / USD 0 with unknown costs.

Before the second repair was installed, the existing owner resumed the same X job
at approximately `2026-08-21T04:28Z` as attempt `2`; its authenticated timeline
readback found the exact status URL and the job journal became `VERIFIED/LIVE`
without creating another job. The subsequent `04:29:25 JST` final status-page
readback was transiently not exact, so `last-run` truthfully stayed
`PUBLICATION_FAILED / XPostError` and the `x-posts` file remained an effect fence
without terminal `state`. Codex found the ordering defect: the publisher had
verified the journal before `live_readback`, so a transient final failure could
overstate X liveness. Release `ba2721b50a1439d3ae3f38ab39b3895bfce32c2c` now
writes `X_POST_PUBLIC_READBACK / LIVE` and verifies or reconciles the journal only
after that final readback. The guard fixture proves a failed final readback leaves
`EFFECT_STARTED` and calls no reconcile; existing checks remain `25/25`. The
release is installed with byte-equal `current`; the next existing owner wake must
promote the current fence receipt without a new post. B01 remains
`NO_TRANSACTIONS`, approved/paid net null, and costs unknown.

The existing owner then naturally ran the installed repair at
`2026-08-21T04:40:03Z`. It reconciled the same X status URL under the same job
`e5399f85…`, promoted `x-posts/...-1.json` to terminal `LIVE`, advanced the
campaign to `X_LIVE`, and sent owner Telegram `messageId=26594`. No second X post,
job, or provider-link effect was created. The canonical ledger collapsed back to
18 exact rows: 18 provider-link keys, 18 owned public URLs, 32 provider clicks,
15 insufficient plus 3 observed Dev.to denominators, all four commission status
counts zero, and all 18 real cash costs unknown. `launchctl` still reports 141 for
introspection, but this natural owner wake is the installed runtime proof. The
revenue cycle remains in its one-hour cooldown from `04:29:23 JST`; the next
official PartnerStack capture is due around `05:29 JST`. B01 remains open with
`commission_row_count=0`, `NO_TRANSACTIONS`, approved/paid net null, and unknown
cost coverage.

At `2026-08-21T05:13:04Z`, the existing owner resumed the same voice-design job,
read back the owned page and one exact X status, and advanced it to `X_LIVE`.
Telegram owner receipt `26625` confirms the natural-language state. The
canonical ledger is now 19 exact rows with 19 provider-link keys and 19 owned
public URLs; provider clicks remain 32, commission statuses remain all zero, and
all real cash costs remain unknown. This campaign is now a comparable English
placement, but it has no official transaction and cannot influence allocation.

At `2026-08-21T05:34:22Z`, the next existing owner wake reached the due revenue
cycle but the official PartnerStack `capture` subprocess returned
`NONZERO_EXIT` with return code `1`. The durable receipt is
`REVENUE_CYCLE_FAILED` at `stage=capture`; the latest hash-bound provider
artifact is still the prior empty report, so this wake created no transaction,
settlement, payout, commission transition, or money. `revenue-cycle.json` still
records the last successful `NO_TRANSACTIONS` cycle and Telegram `26645` records
the failure. The next atomic action is the existing owner's retry/readback of
the same capture path; do not run a manual provider capture or treat the failure
as proof of zero revenue.

At `2026-08-21T05:45:32Z`, that existing owner retry recovered the capture path.
The new hash-valid PartnerStack artifact is `7f330211…d097a89`, with zero
commission rows, empty payout rows, and `NO_LIVE_ROWS`. Reconciliation read
`source_rows=0`, appended/replayed `0/0`, and `money_state=NO_TRANSACTIONS`.
The owner event is `NO_TRANSACTIONS`, not `REVENUE_CYCLE_FAILED`; the retained
failure file is historical evidence only. Canonical state remains 19 placements,
19 provider-link keys, 19 public URLs, 32 provider clicks, 16 insufficient plus
3 observed denominators, zero pending/approved/paid/reversed statuses, and
unknown real costs. Rolling net remains `NO_APPROVED_OR_PAID_ROWS` with null
approved/paid USD net and `NOT_REACHED` for the $10,000 threshold. The next
official capture is due around `06:45 JST`; the owner emitted the
natural-language recovery receipt as Telegram `26654`; B01 still waits for the
first non-empty official transaction.
The existing Affiliate suite was rerun after recovery (`69` tests, `OK`); no
runtime code changed and installed `current` remains the byte-equal
`ba2721b50…ce32c2c` release.

At `2026-08-21T04:51:05Z`, the same existing owner selected the next bounded
English opportunity and created one verified PartnerStack link for
`elevenlabs-discovered-voice-design-en-1` (provider key is retained only in the
private receipt). The wake stopped at `WAITING_FOR_PLACEMENT_LINK` after that one
effect; no owned article, X post, or provider transaction was created. Telegram
owner receipt `26604` reports the state. The canonical ledger is now 19 rows,
19 provider-link keys, 18 owned public URLs, 32 clicks, 16 insufficient plus 3
observed Dev.to denominators, and zero commission statuses; all real cash costs
remain unknown. The new row is not mature and cannot receive allocation credit.

At `2026-08-21T05:56:18+0900`, the existing Affiliate owner naturally selected
`elevenlabs-discovered-realtime-speech-to-text-en-1` from the bounded English
opportunity path and created one verified PartnerStack link. The durable program
link receipt is `VERIFIED` and the placement ledger grew to 20 rows: 20 private
provider-link keys, 19 owned public URLs, 32 provider clicks, 17 insufficient plus
3 observed Dev.to denominators, and zero pending/approved/paid/reversed rows. The
wake event stopped at `WAITING_FOR_PLACEMENT_LINK`; its generic placement identity
was missing from the owner event, so Telegram `26662` contained only the separate
Repost observation. No public URL, transaction, commission, or money was created.

Codex repaired that observability gap in release
`1c5faf4ff7d9d70cf3f2a4e607ae11b81e1aca28`: generic publication now returns
`publication_link_*` receipt fields to the existing owner event, and the owner
emits one redacted `PLACEMENT_LINK_VERIFIED` Telegram receipt without printing a
raw tracking link or provider key. The existing Affiliate suite remained `69`
tests `OK`; Python compilation, source byte equality, the immutable `current`
symlink, ownership receipt, and CDP `9324/9326/9327` version readback passed. The
installer still reports only the known launchd bootstrap `141: Reentrancy avoided`;
no parallel executor or direct public/provider effect was started.

The next natural owner wake at `2026-08-21T06:07:09+0900` read back the same durable
link as `VERIFIED` with `deduplicated=true`, kept the campaign at
`publication_state=OWNED_NOT_LIVE`, and sent Telegram `26680` with
`PLACEMENT_LINK_VERIFIED`. No second link effect, owned page, X post, provider
transaction, commission, payout, or money was created. Rolling net remains
`NO_TRANSACTIONS / NO_APPROVED_OR_PAID_ROWS / NOT_REACHED`, approved/paid net is
null, status counts are all zero, and real costs remain `UNKNOWN`; B01 still waits
for the first non-empty official provider transaction and exact placement join.

B01 money-boundary repair `403b98448fc7caeeb98086c4e6ba00ca5d88ff12` adds the
literal provider status `reversed`, uses the observation time for a late reversal
in the rolling window, and marks a non-USD reversal as FX-unknown instead of
claiming a USD net. The existing Affiliate suite remained `69/69` and a
non-persistent reversal/currency/timing fixture passed. The immutable release was
installed with `LOCAL_READY` ownership and byte-equal `revenue_cli.py`; launchd
bootstrap still returned only the known `141: Reentrancy avoided`. No provider row,
transaction, or money was created.

At `2026-08-21T06:18:18+0900`, the existing owner advanced the same realtime
speech-to-text campaign through owned publication, then the existing X publisher
left its one effect fence at `PUBLICATION_FAILED / XPostError` with timeline
`NOT_FOUND`, attempt `1`, and a 3,600-second retry cooldown. No second X job or
post was created. Because the in-flight campaign was `OWNED_LIVE` but the
placement mapper only considered `X_LIVE`, the readback temporarily exposed a
21-row ledger split: 20 provider-link keys, 20 public URLs, and one slug alias.

Candidate repair `5d14460d5f4262d2029ea5bf903e45109c6b888f` treats in-flight
`MATERIALIZED/OWNED_NOT_LIVE/OWNED_LIVE` campaign receipts as canonical placement
identity. The read-only actual-state proof returned 20 candidates with the
discovered placement carrying both the private link and owned URL and no slug
alias; the existing suite remained `69/69`. The immutable release was installed
with `LOCAL_READY` ownership and byte-equal source, and the browser bootstrap
warning remained only `141`.

The next natural owner wake at `2026-08-21T06:29:23+0900` read back the same X
status URL under the same fence, promoted the campaign to `X_LIVE`, collapsed the
canonical ledger to exactly 20 rows (20 provider-link keys and 20 owned public
URLs), and removed the slug alias. Telegram `26700` is the natural-language
`SELF_HEALED` receipt stating same-publication recovery with no duplicate effect.
The wake remained in revenue cooldown; official source rows are still zero,
approved/paid net is null, all pending/approved/paid/reversed counts are zero, and
real billed costs remain `UNKNOWN`.
