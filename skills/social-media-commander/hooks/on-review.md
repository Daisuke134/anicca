---
name: social-media-commander-on-review
description: Owner reviews content. Approve or reject with specific feedback.
---

# On-Review Hook

## Present Content for Review

Format:
```
REVIEW REQUEST: <slug>
Platform: <platform> | Type: <type> | Stage: <funnel-{{profile.lateness.stakeholders.senderType}}>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOOK:
[hook text]

CAPTION:
[full caption]

HASHTAGS:
[hashtag set]

VISUAL:
[description or asset ref]

CTA: [cta]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Say: APPROVE / REJECT <reason> / EDIT <what to change>
```

## On APPROVE
- Move state → approved
- Move file to reviews/approved/
- Ask: "Schedule for when? [suggest optimal time for this platform]"

## On REJECT <reason>
- Move state → rejected (or back to draft if editable)
- Log rejection reason in entry
- Move to reviews/rejected/
- If "edit" intent → keep as draft, apply feedback

## On EDIT <instruction>
- Apply changes immediately
- Re-run pre-review checklist
- Represent for review
