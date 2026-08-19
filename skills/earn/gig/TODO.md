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

The public product principle is **fast, cheap, accurate, and minimal-human-loop**. A user
creates and owns the marketplace account, connects their own authenticated browser and
notification address, and the four independent lanes run in parallel. Apply finds and
submits only work the configured capability policy permits; Negotiate answers buyers and
returns estimates; Paid builds, verifies and delivers paid work; Storefront measures and
improves listings. Revenue claims come only from official marketplace/payment readback.
The public package must not promise guaranteed income or describe unverified activity as
revenue. Owner notifications use a provider adapter; the distributable default is email,
not this operator's Telegram identity.

## Execution order to end

Only the first unfinished item is active: **0b reply speed** → the four clean-public-package
steps below → **4 listing contract/product truth** → **2 stable paid-feedback identity and
credential handling** → **5 storefront attribution** → **1 browser-major qualification** →
**6 merge the already-pushed legacy-removal branch when its unrelated merge clears**. Closed
items do not reopen without new contradictory evidence.

After 0b closes, execute the public-package items in order:

1. Audit the tracked `skills/earn/gig/` tree and its reachable Git history for credentials,
   customer content, account identifiers, absolute owner paths, and committed runtime evidence.
   Remove or redact any public-data violation before continuing.
   **IN PROGRESS:** allowlist-free current-tree gitleaks and PII-shape scans are clean, but the
   semantic audit found tracked seller storefront ids/profile/contracts/assets. Reachable history
   also contains the real customer messages, delivery files, attachment/account paths and operator
   address introduced by `944ca1fc1` and only deleted—not purged—by `478b8a1b2`. Slice A adds the
   reviewed `GIG_STOREFRONT_ROOT` boundary: strict pre-browser validation, private-family binding,
   symlink containment and runtime-state asset snapshots. Focused tests are 17 + 4 + 21 passing;
   fresh Sol/High review verdict is `ship`. Next, atomically move the seller bundle to the private
   root and remove the tracked fallback before rewriting the affected public history.
2. From a fresh clone of public `main`, run the package's non-mutating tests and configuration /
   plist generation using only documented local configuration. Do not reuse this machine's
   private state as proof of portability.
3. Make `README.md` match that clean-clone evidence: exact dependencies, local secret/state
   boundaries, install, status, upgrade and uninstall steps. Every documented command must be
   exercised from the fresh clone.
4. Re-run the public-tree audit and clean-clone acceptance, then record the exact commit and
   evidence here. That closes this milestone. Items 0b, 1, 2, 4, 5 and 6 remain product/runtime
   work and do not block publishing the package unless the audit finds private data in them.

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
judgement uses one tool-disabled Luna-medium candidate with a 60-second runner deadline and no
slow fallback or same-call retry. The existing real-model authorization eval passed 6/6 cases,
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
60-second-bounded semantic judgement, rechecks the exact head identity, refreshes the official
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
passes, the system may describe the 30-second wake request and 60-second semantic bound, but must
not publish an "after" reply speed or a five-minute guarantee. Tests must prove that a deliberately
slow semantic task does not block claiming a second message, two changed threads can progress
concurrently, restart resumes the durable claim, and replay produces zero duplicate sends. Final
acceptance is a natural buyer-origin → detection → judgement → click → official-readback receipt
within five minutes, with two minutes or less as the operating target.

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

## 4. `negotiate_context` can never become "ready"

**Blocks:** the negotiate lane answering a storefront inquiry with the offer it was made
against. Two independent causes, both proven from the live receipt.

**4a. The lane retires its own contracts by doing its job.**
`_load_listing_contracts()` (`scripts/storefront_direct.py:1691`) reads the hand-authored
contracts under `contracts/storefront/`, and each one is bound to one exact listing version:
if `service_version_sha256` no longer equals the live listing's, the contract is dropped as
stale. Editing listings is this lane's entire purpose, so **the lane invalidates its own
contracts**, and with them that listing's inquiry playbook, until a human re-authors the file.

There is exactly one hand-authored contract, `contracts/storefront/91000002.json`, and the live
receipt shows it stale right now. The single storefront-origin inquiry on record is on that
same service, so its identity lookup finds nothing and no envelope is written.

That was recorded in the wake row as `stale_listing_contracts` and never said out loud — the
report kept printing a healthy-looking active count beside it. It now prints the binding
breakage too.

**This is not a rebind, and rebinding it would be worse than leaving it stale.** Comparing the
hand-authored contract with the listing as last observed: five of six `offer` fields differ in
substance — `outcome`, `inclusions`, `deliverables` and `required_inputs` are all rewritten, and
`options` holds two paid add-ons (¥3,000 for an extra macro, ¥5,000 for monthly maintenance)
that **the published listing no longer offers at all**. The contract describes a product that is
not on sale. Moving the version hash to make the binding pass would hand the negotiate lane
add-ons a buyer cannot buy.

So the decision is which one is wrong: bring the contract down to what is published, or put the
add-ons back on the listing. That is seller copy and a pricing choice, not a code change. Worth
noting the second reading is a revenue one — an upsell that used to exist is gone from the
listing, and only this file still remembers it.

**4b. Nothing consumes an envelope.**
`negotiate_context` reports `ready` only when every context key is also present in
`negotiate-context-acks.jsonl` with `status: consumed`. That file has never been created, and
`storefront_direct.py` is the only file in the repository that names either it or
`inquiry-context-envelopes.jsonl` — which does exist on disk, written and then read by nobody.
The negotiate lane does not know this protocol exists, so even with 4a fixed the state stays
`missing` forever, and `missing` reads as a transient failure when it means "no consumer".

Decide whether to build the consumer or to delete the protocol. Do not "fix" this by relaxing
the readiness test — that would only make an unbuilt half look finished.

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
