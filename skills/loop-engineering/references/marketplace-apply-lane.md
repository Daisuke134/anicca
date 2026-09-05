# Building an Apply lane on a marketplace

Measured on CrowdWorks, 2026-09-05, recovering a lane that had submitted nothing
since 2026-08-11. Every fault below was silent: the lane ran, exited, and
reported a status while earning nothing. Read this before writing a new
marketplace adapter — each one costs a day to rediscover.

## Reuse before writing

| Need | Already exists |
|---|---|
| Idempotent submission, replay prevention, pending reconciliation | `skills/_shared/marketplace-core/scripts/application_transaction.py` |
| Receipt ledger | `.../ledger.py` |
| Telegram delivery with exactly-once accounting | `.../telegram_outbox.py` |
| The `[Platform][応募判断]` / `[Platform][応募完了]` message | `skills/earn/gig/scripts/report_envelope.py` (platform-neutral; takes the display name as an argument) |
| The per-wake lane summary | `skills/_shared/marketplace-core/scripts/lane_summary.py` (Lancers and CrowdWorks both render through it) |
| Sending, and draining the outbox | `.../telegram_delivery.py` (never a CLI: launchd gives a job no PATH) |
| What to sell, at what price, per platform | `skills/gig-work/profile/listings/catalog.json` |

An adapter that adds its own ledger, its own outbox or its own wording is the
defect this file exists to prevent.

## Where the three lanes stand (2026-09-06)

| Piece | Coconala | Lancers | CrowdWorks |
|---|---|---|---|
| transaction, ledger | own | shared | shared |
| outbox | own diverged copy | shared | shared |
| delivery loop + sender | own | own | shared |
| wake summary | own | shared | shared |
| per-decision message | hand-written | — | shared renderer |

Coconala owns `report_envelope.py` and does not call it: its own
`[ココナラ][応募判断]` is hand-written in `application_direct.py`. So the one
sentence exists three times. Wiring Coconala to its own renderer is the next
extraction, and it belongs to whoever owns that lane — not to a second session
editing the same files.

`report_envelope.py` still sits in the Coconala adapter rather than in
`_shared/marketplace-core/`. Four Coconala scripts import it and that lane is
being worked on concurrently, so moving it is the extraction step to take when
that work settles — not while two sessions would both be editing it. Load it by
path in the meantime; do not copy it.

## The eight silent faults

**1. A wedged browser still looks healthy.** A crashed Chromium keeps its
debugging port in `LISTEN` while DevTools no longer answers, and the ownership
check believed the port. Decide liveness by an actual CDP request, not by a
bound socket or a live PID.

**2. A crash leaves a lock that kills every relaunch.** The dead process leaves
`SingletonLock` in the profile directory naming itself, so each new instance
exits instantly and the supervisor reports a clean restart. Clear the stale
lock when the process it names is gone.

**3. A gate can be impossible to pass.** Readback demanded fields the public
profile never renders and an exact string match the page's whitespace
collapsing makes unachievable. Assert only what the surface you are reading can
actually prove; verify the rest where it is editable.

**4. A supplied page already carries a browser.** Acquiring another one starts a
second Playwright runtime in the same process and throws — visible only as a
generic failure, and only on the path that passes a page.

**5. The form is only reachable if you navigate to it.** Navigating "only from
`about:blank`" fails every real handover, because the caller arrives holding the
job detail page.

**6. Success does not always look like success.** The provider landed the
accepted proposal on `/proposals/<id>#scroll_to_message`; a strict URL check
rejected the fragment and reported `submission_uncertain` for applications that
had posted. Also allow the page a moment to settle before reading it back.

**7. Money is displayed in a different unit than it is submitted.** Proposals go
out tax-exclusive and read back tax-inclusive, so 300,000 never matched 330,000
and verification could never pass. Normalise before comparing.

**8. An uncertain submission must still reach the ledger.** Otherwise the
application exists on the provider and nowhere in your state. Resolve its id
from the provider's own list and reconcile it. A pending entry is unverified
whether or not it already carries an id — reconcile it either way.

## Qualifying a posting

Search terms come from the catalogue's own titles, cut to noun phrases:
`業務自動化システムを開発` finds nothing while `業務自動化` returns a live board.

Reject, in this order, and count each rejection so an empty day is explainable:

1. closed postings, and clients that are both unverified and unreviewed — the
   2026-09-02 scout with 9 applicants and 0 contracts was exactly this shape;
2. postings whose text does not match the listing, read from the posting body
   rather than the whole page (navigation and sidebars matched a medical
   clerical job on the word "AI");
3. postings outside build categories, read from the provider's own category
   label rather than a breadcrumb guess;
4. postings whose stated budget cannot pay the cheapest tier.

Take search results only from the result list — a bare link selector returned
227 links for a 20-result search.

Skip anything already in the ledger, or the lane re-picks its own best match
forever and every tick ends `duplicate_project`.

## Cadence and rollout

Rotation decides where to start, not where to stop: capping the scan at a few
listings makes a quiet slice look like an empty market. Bound the scan by time
instead.

Reporting is its own owner. Merging it into the apply tick means a failed apply
silences the report and a slow report delays an application.

Shipping is not merging. A merged fix stays dormant until a release is cut from
a main SHA and each label is repointed at it; `cut-loop-release.sh` with no
argument cuts from whatever branch the checkout happens to be on, which can
produce a release missing the very code you shipped.

## Faults found while wiring the reports (2026-09-05, same day)

**9. A receipt is validated twice.** Adding a field to the JSON schema is not
enough — the same receipt is also built into a frozen dataclass, and the
mismatch surfaces as a generic uncertain result, never as a schema error. Add
the field to both, and make it optional so every other lane's rows stay valid.

**10. The state writer keeps a fixed field list.** Anything a lane attaches to a
claim that is not on that list is dropped on the next write, silently. That is
why the job's name never reached the receipt even after the receipt could carry
it.

**11. Not every helper receives what its caller has.** `_reconcile_pending` is
handed the pending entry, not the opportunity, so reading the opportunity there
raises inside a broad `except` and turns every reconciliation into
`submission_uncertain`. When a change makes everything uncertain at once,
suspect an exception inside the settle path before suspecting the provider.

**12. Silence is ambiguous.** A lane that reports only its successes cannot be
distinguished from a lane that has stopped. Send one line per wake — what was
inspected, what was declined and why, what was applied — and the reader can
tell "nothing was eligible" from "broken" without opening a terminal.

**14. A category allow-list must be measured, not guessed.** The first list
rejected `AI・チャットボット開発`, `ChatGPT開発` and `Webサイト更新・保守` — all sold
by the catalogue — and was the largest rejection bucket. Sample the categories
the provider actually prints before deciding what is out of scope, then keep a
case for each accepted and each rejected name so widening it later is safe.

**15. Optional state fields are rejected in three places.** A field added to a
claim has to survive the writer's field list, the reader's field-set check and
the reader's field-by-field rebuild. Miss the middle one and the whole state
file is invalid, which surfaces as every reconcile failing at once.

**13. An abandoned claim stops the whole queue.** A sender killed between
claiming a message and resolving it leaves the claim in `sending`, and because
the claimer only reads `pending`, delivery stops entirely and silently. Both
CrowdWorks and Lancers had accumulated stuck claims — reclaim them, past a
window and only when no provider id was recorded.
