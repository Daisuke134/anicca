---
name: social-media-commander-on-idea-capture
description: Fires when owner mentions a content idea. Creates draft entry immediately.
---

# On-Idea-Capture Hook

## Trigger
Owner mentions: "post about", "make a reel", "write a thread",
"tweet about", "share this", "content idea" or similar.

## Step 1 — Extract Intent
- Core topic/subject
- Platform (if mentioned, else suggest best fit)
- Content type (if mentioned, else suggest)
- Funnel {{profile.lateness.stakeholders.senderType}} (infer from context)
- Urgency (asap / this week / whenever)

## Step 2 — Suggest Platform + Type (if not specified)
Based on topic:
- Breaking news / hot take → Twitter/X
- Visual transformation / lifestyle → Instagram Reel
- Professional insight → LinkedIn post
- Long tutorial → YouTube
- Casual thought → Threads

## Step 3 — Create Draft Entry
```markdown
# <YYYY-MM-DD-platform-type-slug>
## Meta
- Platform:     <platform>
- Type:         <content-type>
- Format:       [Reel/Post/Thread/etc]
- State:        idea
- Pillar:       [pillar or TBD]
- Funnel {{profile.lateness.stakeholders.senderType}}: [{{profile.lateness.stakeholders.senderType}} or TBD]
- Priority:     normal
- Created:      YYYY-MM-DD HH:MM IST

## Core Idea
[Raw idea as captured]

## Suggested Angle
[Agent's suggestion for how to develop this]

## Hook Draft
[First attempt at hook]

## CTA Suggestion
[What action should audience take]
```

## Step 4 — Update Pipeline
Update soul [CONTENT PIPELINE].

## Step 5 — Confirm
"Idea captured: <slug> for <platform>. Want me to develop the full draft now?"
