# Open work on the Coconala loop

Ordered. Each item says what was measured, not what is suspected. Anything without
evidence does not belong on this list.

The four lanes run from `~/gig/releases/life-manager/<sha>/`, cut from `main` by
`gig_release.py`. See `README.md` for how the whole thing is installed.

---

## 0a. The apply lane refuses 35% of the board for work it can actually do

**This is the revenue lever.** Measured on `~/gig/b2-ineligible-cache.json`: 249 cached
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

Six of those seven are correct and should stay: you cannot go somewhere and assemble a thing,
appear on camera, hold a licence you do not hold, claim a history you do not have, or take work
from someone who wrote "no AI".

`video_or_animation` is the one that is wrong, and it is the largest by a distance. Reading what
the 88 postings actually ask for: "編集（カット、テロップ、BGM/SE挿入、エフェクト）",
"YouTube動画の編集業務", "30秒ショート動画で333本で10万円", "Instagram縦型広告の冒頭5〜10秒",
"YouTube横動画の編集". Almost all of it is **editing footage the client supplies**. Only a
couple need filming.

Editing supplied footage is not a gap in this machine's capability — it is one of the things it
already does at scale. The class conflates live-action *filming*, which is genuinely impossible,
with *editing*, which is not, and refuses both. The 333-shorts-for-¥100,000 posting is the shape
of job where batch automation beats a human editor outright.

Splitting the class is a policy decision, not a code change, and it needs the seller's word
before anything applies to that work. What the code needs afterwards is a delivery path that
proves the edit before it is offered.

## 0b. The negotiate lane cannot answer in five minutes; a full sweep takes 5.8 hours

`DIRECT_REVALIDATION_BATCH_SIZE=1` at a 180-second interval means one talkroom re-read per wake.
Against ~115 rooms that is about 5.8 hours to come back round, while a room is treated as stale
after 30 minutes — so 114 rooms sit permanently overdue. The fast path exists (revalidate only
rooms whose list entry changed) but reports `thread_changed_count: 0` and nothing treats that
silence as a failure.

Sub-five-minute replies are not reachable by tuning the batch size alone: raising the budget
puts proportionally more DOM reads through the one shared browser, which is what the other three
lanes are also queued behind. Either the change detector becomes trustworthy enough to be the
primary path — which means measuring why it reports zero while messages arrive — or the lanes
stop sharing one browser. Decide which before touching the number.

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

## 3. The estimate lane refuses one thread forever — the counts disagree

**Blocks:** estimate revenue on one thread. Not a race; waiting longer cannot help.

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

Six against three, with three mapped, has the shape of the previous sub-category's options
still sitting in the `<select>` alongside the new ones. Confirm that before fixing it: the
readback records counts, not values, so the next step is to capture the option values and the
mapped ids together and see whether the extra three are the stale set.

The count equality is a proxy for the real invariant, which is that the enabled options *are*
the mapped ones. Comparing values instead of counts would be correct whether or not stale
options linger — but this lane submits priced offers to buyers, so the change wants a fresh
adversary before it ships, not just a green test.

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
