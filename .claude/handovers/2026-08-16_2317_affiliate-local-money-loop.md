# Affiliate local money loop handover

- SSOT: `docs/affiliate-agent/AFFILIATE-AGENT-SSOT.md`; resume from `Measured planning checkpoint and next TODOs`, then `Remaining autonomous money-loop work — canonical order`.
- Development route: `/Users/anicca/anicca-project/.worktrees/affiliate-life-manager-spec`, branch `docs/affiliate-life-manager-spec`. Current clean/pushed spec HEAD is `361866f51`, descended from required base `0a7debb58`.
- Installed runtime: `/Users/anicca/.local/share/life-manager/affiliate/current` → release `088858bce2965f05783448b4b5f829fa053717ee`; `current` is byte-backed by that immutable release. Any future `skills/affiliate` change requires immutable install and real owner replay.
- Repository decision: one Life Manager implementation at `skills/affiliate/`; no Affiliate-only repo, executor, ledger, `apps/api`, or Railway runtime. Private mutable state stays under `~/.local/state/life-manager/affiliate/`. OSS is the same proven Skill packaged for a clean Mac, never a rewrite.

## Current measured truth

- Six Affiliate launchd plists exist: three keep-alive browser owners and source/composition/money jobs at 600-second intervals. CDP `9324`, `9326`, and `9327` each returned HTTP `200`; authenticated tabs showed ElevenLabs home, one exact Affiliate X status, and Impact home.
- The canonical ledger contains **13 dedicated-link placements**, **13 owned public URLs**, and **30 provider-link clicks**. The latest per-link transition is `+1` on the subtitle-translator placement; the aggregate provider metric is 41 clicks with `+40` explicitly unattributed. Neither is money.
- PartnerStack/ElevenLabs is `AUTHENTICATED`; the latest official capture has `commission_row_count=0`, `NO_LIVE_ROWS`, currency display `USD`, tax registration required, and payment-provider selection required. Pending/approved/paid/reversed are therefore zero observed rows. Approved-or-paid net is **USD 0**. Unknown real costs remain unknown.
- Telegram outbox and sent ledger are both 97 rows after the owner retry; the tiktok `PLACEMENT_LIVE` event was sent by the existing owner as provider message `26004`, and no pending event is currently visible.
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

The publication slice A04/A05 is now complete. The existing owner reached the
tiktok owned/X terminal receipts and an unchanged replay without a new commit,
X object, link, or placement. The next execution slice is B01: capture the first
non-empty official provider transaction artifact, retaining the exact provider
transaction/settlement identifiers and truthful empty/unknown states. Do not
create a parallel executor or manually publish.

## Ordered route to completion

1. P0: restore the real publication trajectory and close the two non-public rows.
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

The latest official PartnerStack artifact remains empty (`commission_row_count=0`,
`NO_LIVE_ROWS`, `payout_row_state=EMPTY`, `generic_transaction_id_available=false`,
artifact SHA-256 `6bb1c9…`). The canonical placement ledger records 30
provider-link clicks, while aggregate provider metrics show 41 clicks with `+40`
unattributed; no click is money. There are zero official pending/approved/paid/
reversed transaction rows, approved-or-paid net is USD `0`, and real billed cost
is `UNKNOWN`. The next atomic item is B01: let the existing owner capture a
non-empty official transaction/settlement artifact and join it replay-safely to
one exact placement; no estimate or pending value can advance the $10,000 gate.
