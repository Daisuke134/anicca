# Open work on the Coconala loop

Ordered. Each item says what was measured, not what is suspected. Anything without
evidence does not belong on this list.

The four lanes run from `~/gig/releases/life-manager/<sha>/`, cut from `main` by
`gig_release.py`. See `README.md` for how the whole thing is installed.

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

**Blocks:** real money on a real order.

The paid lane holds one live order in `pending`. Its `active_feedback_cycle` carries a
`buyer_feedback_sha256` that does not equal the digest of the current buyer message, so
`_remote_revision_required()` returns false and the cycle never advances.

The digest itself is the thing that is broken. The same day's artifacts disagree: the item
snapshot and the remote intent hold one digest, while the live buyer reply and the work
decision written nineteen minutes later hold an older one, whose text includes an exchange
that was already resolved. `persist_latest_paid_buyer_reply`'s accumulation window is
regressing to older history.

Fix the window first. `_feedback_cycle_patch()` in `scripts/delivery_project.py:144` is wired
but guarded at `scripts/paid_direct.py` by `if not (root/"state.json").is_file()`, so it only
ever fires during a project's first bootstrap. **Do not loosen that guard while the digest is
unstable** — a stale digest reaching the remote builder means it edits a customer's live site
against instructions the customer already withdrew.

---

## 3. The estimate lane loses one submission per pass to a form race

**Blocks:** estimate revenue, at a measured rate of one in six.

Every retained pass fails with `dependent_category_types_not_loaded`. The wait lives in the
injected script in `scripts/coconala_estimate_browser.py`: after selecting the sub-category it
polls for five seconds for the dependent category-type control to populate, and gives up.
The same pass confirms five other estimates officially submitted, so this is a race on one
form, not a dead lane.

Measure the real population time before changing the number. A fixed five seconds that is
sometimes too short will also sometimes be too long; the control's own readiness signal is
already computed in `categoryTypeContract()`.

---

## 4. `negotiate_context` can never become "ready"

**Blocks:** the negotiate lane answering a storefront inquiry with the offer it was made
against. Two independent causes, both proven from the live receipt.

**4a. The envelope is matched against the current pass's listings only.**
`_materialize_inquiry_context()` (`scripts/storefront_direct.py:876`) is handed
`listing_contracts` from the pass that is running, and looks up
`(service_id, listing_version)`. The one storefront-origin inquiry on record cites a listing
version that has since been superseded. That version is present in
`~/gig/storefront-direct/listing-contracts.jsonl` — eight versions exist for that service —
but not in the set the function receives, so the inquiry lands in `missing_contracts` and no
envelope is ever written. A buyer inquires about the listing they saw, which by definition
may not be the listing that exists now.

**4b. Nothing acknowledges an envelope.**
`negotiate_context` reports `ready` only when every context key is also present in
`negotiate-context-acks.jsonl` with `status: consumed`. That file has never been created, and
`storefront_direct.py` is the only file in the repository that names it. The negotiate lane
does not know this protocol exists. Even with 4a fixed, the state stays `missing` forever.

Decide whether the protocol is worth completing or whether the context should be passed the
way the lanes already pass everything else. Do not "fix" this by relaxing the readiness test.

---

## 5. The funnel attributes most payments to nobody

**Blocks:** knowing which lane earns.

The storefront receipt reports its own source as
`source_status: "latest_completed_log_noncanonical"` — the funnel is reconstructed by parsing
the negotiate lane's launchd stdout log, because no canonical inventory is provided. The
result, honestly labelled: 110 of 116 inquiries and 5 of 8 payments have origin `unknown`.

A log is a rendering, not a ledger. Give the funnel the negotiate lane's own state as its
source, and keep the log path only as the fallback it already declares itself to be.

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
