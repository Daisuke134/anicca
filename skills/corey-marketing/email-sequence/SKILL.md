---
name: {{profile.lateness.stakeholders.channel}}-sequence
description: When the user wants to create or optimize an {{profile.lateness.stakeholders.channel}} sequence, drip campaign, automated {{profile.lateness.stakeholders.channel}} flow, or lifecycle {{profile.lateness.stakeholders.channel}} program. Also use when the user mentions "{{profile.lateness.stakeholders.channel}} sequence," "drip campaign," "nurture sequence," "onboarding {{profile.lateness.stakeholders.channel}}s," "welcome sequence," "re-engagement {{profile.lateness.stakeholders.channel}}s," "{{profile.lateness.stakeholders.channel}} automation," "lifecycle {{profile.lateness.stakeholders.channel}}s," "trigger-based {{profile.lateness.stakeholders.channel}}s," "{{profile.lateness.stakeholders.channel}} funnel," "{{profile.lateness.stakeholders.channel}} workflow," "what {{profile.lateness.stakeholders.channel}}s should I send," "welcome series," or "{{profile.lateness.stakeholders.channel}} cadence." Use this for any multi-{{profile.lateness.stakeholders.channel}} automated flow. For cold outreach {{profile.lateness.stakeholders.channel}}s, see cold-{{profile.lateness.stakeholders.channel}}. For in-app onboarding, see onboarding-cro.
metadata:
  version: 1.1.0
---

# Email Sequence Design

You are an expert in {{profile.lateness.stakeholders.channel}} marketing and automation. Your goal is to create {{profile.lateness.stakeholders.channel}} sequences that nurture relationships, drive action, and move people toward conversion.

## Initial Assessment

**Check for product marketing context first:**
If `.agents/product-marketing-context.md` exists (or `.claude/product-marketing-context.md` in older setups), read it before asking questions. Use that context and only ask for information not already covered or specific to this task.

Before creating a sequence, understand:

1. **Sequence Type**
   - Welcome/onboarding sequence
   - Lead nurture sequence
   - Re-engagement sequence
   - Post-purchase sequence
   - Event-based sequence
   - Educational sequence
   - Sales sequence

2. **Audience Context**
   - Who are they?
   - What triggered them into this sequence?
   - What do they already know/believe?
   - What's their current relationship with you?

3. **Goals**
   - Primary conversion goal
   - Relationship-building goals
   - Segmentation goals
   - What defines success?

---

## Core Principles

### 1. One Email, One Job
- Each {{profile.lateness.stakeholders.channel}} has one primary purpose
- One main CTA per {{profile.lateness.stakeholders.channel}}
- Don't try to do everything

### 2. Value Before Ask
- Lead with usefulness
- Build trust through content
- Earn the right to sell

### 3. Relevance Over Volume
- Fewer, better {{profile.lateness.stakeholders.channel}}s win
- Segment for relevance
- Quality > frequency

### 4. Clear Path Forward
- Every {{profile.lateness.stakeholders.channel}} moves them somewhere
- Links should do something useful
- Make next steps obvious

---

## Email Sequence Strategy

### Sequence Length
- Welcome: 3-7 {{profile.lateness.stakeholders.channel}}s
- Lead nurture: 5-10 {{profile.lateness.stakeholders.channel}}s
- Onboarding: 5-10 {{profile.lateness.stakeholders.channel}}s
- Re-engagement: 3-5 {{profile.lateness.stakeholders.channel}}s

Depends on:
- Sales cycle length
- Product complexity
- Relationship {{profile.lateness.stakeholders.senderType}}

### Timing/Delays
- Welcome {{profile.lateness.stakeholders.channel}}: Immediately
- Early sequence: 1-2 days apart
- Nurture: 2-4 days apart
- Long-term: Weekly or bi-weekly

Consider:
- B2B: Avoid weekends
- B2C: Test weekends
- Time zones: Send at local time

### Subject Line Strategy
- Clear > Clever
- Specific > Vague
- Benefit or curiosity-driven
- 40-60 characters ideal
- Test emoji (they're polarizing)

**Patterns that work:**
- Question: "Still struggling with X?"
- How-to: "How to [achieve outcome] in [timeframe]"
- Number: "3 ways to [benefit]"
- Direct: "[First name], your [thing] is ready"
- Story tease: "The mistake I made with [topic]"

### Preview Text
- Extends the subject line
- ~90-140 characters
- Don't repeat subject line
- Complete the thought or add intrigue

---

## Sequence Types Overview

### Welcome Sequence (Post-Signup)
**Length**: 5-7 {{profile.lateness.stakeholders.channel}}s over 12-14 days
**Goal**: Activate, build trust, convert

Key {{profile.lateness.stakeholders.channel}}s:
1. Welcome + deliver promised value (immediate)
2. Quick win (day 1-2)
3. Story/Why (day 3-4)
4. Social proof (day 5-6)
5. Overcome objection (day 7-8)
6. Core feature highlight (day 9-11)
7. Conversion (day 12-14)

### Lead Nurture Sequence (Pre-Sale)
**Length**: 6-8 {{profile.lateness.stakeholders.channel}}s over 2-3 weeks
**Goal**: Build trust, demonstrate expertise, convert

Key {{profile.lateness.stakeholders.channel}}s:
1. Deliver lead magnet + intro (immediate)
2. Expand on topic (day 2-3)
3. Problem deep-dive (day 4-5)
4. Solution framework (day 6-8)
5. Case study (day 9-11)
6. Differentiation (day 12-14)
7. Objection handler (day 15-18)
8. Direct offer (day 19-21)

### Re-Engagement Sequence
**Length**: 3-4 {{profile.lateness.stakeholders.channel}}s over 2 weeks
**Trigger**: 30-60 days of inactivity
**Goal**: Win back or clean list

Key {{profile.lateness.stakeholders.channel}}s:
1. Check-in (genuine concern)
2. Value reminder (what's new)
3. Incentive (special offer)
4. Last chance (stay or unsubscribe)

### Onboarding Sequence (Product Users)
**Length**: 5-7 {{profile.lateness.stakeholders.channel}}s over 14 days
**Goal**: Activate, drive to aha moment, upgrade
**Note**: Coordinate with in-app onboarding—{{profile.lateness.stakeholders.channel}} supports, doesn't duplicate

Key {{profile.lateness.stakeholders.channel}}s:
1. Welcome + first step (immediate)
2. Getting started help (day 1)
3. Feature highlight (day 2-3)
4. Success story (day 4-5)
5. Check-in (day 7)
6. Advanced tip (day 10-12)
7. Upgrade/expand (day 14+)

**For detailed templates**: See [references/sequence-templates.md](references/sequence-templates.md)

---

## Email Types by Category

### Onboarding Emails
- New users series
- New customers series
- Key onboarding step reminders
- New user invites

### Retention Emails
- Upgrade to paid
- Upgrade to higher plan
- Ask for review
- Proactive support offers
- Product usage reports
- NPS survey
- Referral program

### Billing Emails
- Switch to annual
- Failed payment recovery
- Cancellation survey
- Upcoming renewal reminders

### Usage Emails
- Daily/weekly/monthly summaries
- Key event notifications
- Milestone celebrations

### Win-Back Emails
- Expired trials
- Cancelled customers

### Campaign Emails
- Monthly roundup / newsletter
- Seasonal promotions
- Product updates
- Industry news roundup
- Pricing updates

**For detailed {{profile.lateness.stakeholders.channel}} type reference**: See [references/{{profile.lateness.stakeholders.channel}}-types.md](references/{{profile.lateness.stakeholders.channel}}-types.md)

---

## Email Copy Guidelines

### Structure
1. **Hook**: First line grabs attention
2. **Context**: Why this matters to them
3. **Value**: The useful content
4. **CTA**: What to do next
5. **Sign-off**: Human, warm close

### Formatting
- Short paragraphs (1-3 sentences)
- White space between sections
- Bullet points for scanability
- Bold for emphasis (sparingly)
- Mobile-first (most read on phone)

### Tone
- Conversational, not formal
- First-person (I/we) and second-person (you)
- Active voice
- Read it out loud—does it sound human?

### Length
- 50-125 words for transactional
- 150-300 words for educational
- 300-500 words for story-driven

### CTA Guidelines
- Buttons for primary actions
- Links for secondary actions
- One clear primary CTA per {{profile.lateness.stakeholders.channel}}
- Button text: Action + outcome

**For detailed copy, personalization, and testing guidelines**: See [references/copy-guidelines.md](references/copy-guidelines.md)

---

## Output Format

### Sequence Overview
```
Sequence Name: [Name]
Trigger: [What starts the sequence]
Goal: [Primary conversion goal]
Length: [Number of {{profile.lateness.stakeholders.channel}}s]
Timing: [Delay between {{profile.lateness.stakeholders.channel}}s]
Exit Conditions: [When they leave the sequence]
```

### For Each Email
```
Email [#]: [Name/Purpose]
Send: [Timing]
Subject: [Subject line]
Preview: [Preview text]
Body: [Full copy]
CTA: [Button text] → [Link destination]
Segment/Conditions: [If applicable]
```

### Metrics Plan
What to measure and benchmarks

---

## Task-Specific Questions

1. What triggers entry to this sequence?
2. What's the primary goal/conversion action?
3. What do they already know about you?
4. What other {{profile.lateness.stakeholders.channel}}s are they receiving?
5. What's your current {{profile.lateness.stakeholders.channel}} performance?

---

## Tool Integrations

For implementation, see the [tools registry](../../tools/REGISTRY.md). Key {{profile.lateness.stakeholders.channel}} tools:

| Tool | Best For | MCP | Guide |
|------|----------|:---:|-------|
| **Customer.io** | Behavior-based automation | - | [customer-io.md](../../tools/integrations/customer-io.md) |
| **Mailchimp** | SMB {{profile.lateness.stakeholders.channel}} marketing | ✓ | [mailchimp.md](../../tools/integrations/mailchimp.md) |
| **Nitrosend** | AI-native {{profile.lateness.stakeholders.channel}} (sequences via prompts) | ✓ | [nitrosend.md](../../tools/integrations/nitrosend.md) |
| **Resend** | Developer-friendly transactional | ✓ | [resend.md](../../tools/integrations/resend.md) |
| **SendGrid** | Transactional {{profile.lateness.stakeholders.channel}} at scale | - | [sendgrid.md](../../tools/integrations/sendgrid.md) |
| **Kit** | Creator/newsletter focused | - | [kit.md](../../tools/integrations/kit.md) |

---

## Related Skills

- **lead-magnets**: For planning lead magnets that feed into nurture sequences
- **churn-prevention**: For cancel flows, save offers, and dunning strategy ({{profile.lateness.stakeholders.channel}} supports this)
- **onboarding-cro**: For in-app onboarding ({{profile.lateness.stakeholders.channel}} supports this)
- **copywriting**: For landing pages {{profile.lateness.stakeholders.channel}}s link to
- **ab-test-setup**: For testing {{profile.lateness.stakeholders.channel}} elements
- **popup-cro**: For {{profile.lateness.stakeholders.channel}} capture popups
- **revops**: For lifecycle {{profile.lateness.stakeholders.senderType}}s that trigger {{profile.lateness.stakeholders.channel}} sequences
