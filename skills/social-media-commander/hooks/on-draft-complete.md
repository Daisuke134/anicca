---
name: social-media-commander-on-draft-complete
description: Fires when content draft is complete. Runs quality checklist before moving to review.
---

# On-Draft-Complete Hook

## Pre-Review Checklist (hard requirements)

Run all checks. Block move to review if any fail.

- [ ] Hook written and follows formula from brand/hooks/master.md
- [ ] Caption complete for this platform's character limit
- [ ] Funnel {{profile.lateness.stakeholders.senderType}} tagged
- [ ] Content pillar tagged
- [ ] CTA present and clear
- [ ] Hashtag set assigned from brand/hashtags/master.md
- [ ] Visual described or asset referenced
- [ ] Brand voice check passed (tone/language per guidelines)
- [ ] No prohibited phrases from brand/guidelines/dos-donts.md
- [ ] For promotional content: offer/value clearly stated
- [ ] For educational content: one clear takeaway exists

## Advisory Checks (non-blocking)

- Is hook in top 3 formula types from performance data?
- Is posting time within optimal window for this platform?
- Is there a better platform for this content?
- Is this content similar to something posted in last 30 days?

## If All Hard Checks Pass
Move state: draft → review
Write to reviews/pending/<slug>/
Notify: "Draft ready for review: <slug>"

## If Any Hard Check Fails
Stay in draft state.
Return checklist with specific failures:
"Draft incomplete — missing: [list]"
