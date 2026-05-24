---
name: content-repurposing-engine
description: Transform one long-form piece of content into platform-native posts for LinkedIn, Twitter/X, Email, Instagram, and Blog/DEV.to. Use when: (1) repurposing blog posts into social content, (2) turning newsletters into multi-platform threads, (3) turning videos/podcasts into written content, (4) building a week of social content from one anchor piece, (5) creating LinkedIn posts, Twitter threads, or {{profile.lateness.stakeholders.channel}} sequences. Triggers on: "repurpose", "content repurposing", "one article many platforms", "turn blog to social", "LinkedIn post from newsletter", "Twitter thread from article", "content calendar", "multi-platform content", "social media content machine", "content recycling"
---

# Content Repurposing Engine

Transform one source content into perfectly-formatted content for every platform — in under 5 minutes.

## Core System: The 3-Layer Approach

### Layer 1 — The Source Audit
Before repurposing, assess the content's strongest extractable elements:

Ask: What is the ONE insight, fact, or idea that could stand alone?
Ask: What emotional reaction does this content produce?
Ask: What would someone save or share?

Only repurpose content with at least ONE of these qualities. Generic "5 tips" posts rarely perform well as threads.

---

### Layer 2 — Platform Selection Matrix

Choose platforms based on content type and audience:

| Source Format | Best Outputs | Skip |
|---|---|---|
| How-to article | LinkedIn post + Twitter thread | Instagram |
| Opinion/Hot take | Twitter thread + LinkedIn | Email |
| Case study | LinkedIn post + Email + Blog | Twitter |
| News/Announcement | Twitter thread + LinkedIn | Blog |
| Podcast/Video transcript | All platforms + Blog | — |
| Data/Research | Twitter thread + LinkedIn + Blog | Email |

---

### Layer 3 — The Transformation Prompts

Use these exact prompts for each platform. Copy the template, fill in the `[BRACKETS]`, and run through your AI.

---

## Platform Formats & Prompts

### LinkedIn Post

**Format structure:**
```
[HOOK LINE — bold claim or surprising number, max 150 chars]
[CONTEXT — 2-3 sentences expanding the hook]
[核心内容 — 2-4 paragraphs, each max 2 sentences]
[CTA — question that drives comments, or "save this"]
[2-3 hashtags — specific, not generic]
```

**LinkedIn Prompt:**
```
Transform this content into a LinkedIn post.

Rules:
- First line MUST stop the scroll — use a bold claim, surprising statistic, or provocative question
- First line max 150 characters (visible before "see more")
- Body: 3-5 short paragraphs, each max 2 sentences
- Conversational but authoritative tone
- End with a genuine question OR "Save this post for later"
- Add exactly 3 specific hashtags at the end
- Do NOT use emoji in the first line
- Total word count: 150-250 words

Source content:
[Paste content here]
```

---

### Twitter/X Thread

**Format structure:**
```
(1/N) [HOOK — the entire premise in one tweet. Bold claim or counter-intuitive statement]
(2/N) [Why this matters — 1-2 sentences]
(3/N) [Point 1 — with concrete example or data]
(4/N) [Point 2 — or deeper insight]
(5/N) [The key takeaway + "do this differently" CTA]
```

**Thread Prompt:**
```
Turn this content into a Twitter/X thread with 4-5 tweets.

Rules:
- Tweet 1: The hook — one bold claim that stops the scroll. Make it count.
- Tweets 2-4: Build a logical argument in sequence. Each tweet adds one new point.
- Tweet 5: The closer — what to do with this information. Be specific.
- Each tweet: under 250 characters (X/Twitter limit)
- Number tweets: (1/5), (2/5), etc.
- Do NOT use emoji in the hook tweet — they dilute impact
- Add a soft CTA in the final tweet
- Keep the thread engaging WITHOUT cliffhangers — deliver value in each tweet

Source content:
[Paste content here]
```

---

### Email Newsletter

**Format structure:**
```
Subject: [Punchy — number, question, or curiosity gap, max 50 chars]
Opener: [First sentence — immediate hook, no preamble]
Body: [Core insight in warm, conversational tone]
Closer: [One clear takeaway OR "hit reply"]
```

**Email Prompt:**
```
Write an {{profile.lateness.stakeholders.channel}} newsletter based on this content.

Rules:
- Subject line: max 50 characters. Use: number + benefit, question, or curiosity gap
- First sentence: Must create immediate tension or curiosity — no "I'm excited to share"
- Body: 150-200 words. Conversational, like texting a smart friend
- Write as ONE person talking to ONE reader — not broadcasting
- Include one specific actionable takeaway
- End with an open-ended question OR "hit reply" invitation
- No bullet points, no headers — pure prose

Source content:
[Paste content here]
```

---

### Instagram Caption

**Format structure:**
```
[Line 1: Most compelling single line from the content]
[Hook paragraph: 2-3 sentences that draw the reader in]
[Body: Core message, minimal words]
[CTA: Ask a question or "Save this for later"]
[5-7 #hashtags #spaced #out]
```

**Instagram Prompt:**
```
Transform this content into an Instagram caption.

Rules:
- First line is EVERYTHING — write only the most compelling sentence from the content
- Caption body: max 150 words
- Tone: Conversational storyteller — not a sales pitch
- Use line breaks to create white space (4-8 words per line)
- Include exactly one question at the end to drive comments
- Add 5-7 specific hashtags at the bottom (not generic ones)
- Total character count: 150-500 characters (Instagram caption limit)
- Do NOT use hashtags in the main body — only at the end

Source content:
[Paste content here]
```

---

### Blog / DEV.to SEO Article

**Format structure:**
```
Title: [What it is + benefit, max 60 chars]
Meta description: [What the reader will learn, max 155 chars]
Intro: [1 paragraph — the problem or question]
Body: [3-5 sections with headers]
Takeaway: [What to do with this information]
```

**Blog Prompt:**
```
Transform this content into a blog/DEV.to SEO article.

Rules:
- Title: Descriptive + compelling, max 60 characters
- Meta description: What the reader learns, max 155 characters
- Intro: 1 paragraph — lead with the problem or question this solves
- Body: Use H2 headers to break into 3-5 sections
- Include one bulleted list or numbered list (readers scan)
- Closing: "Here's what to do with this" — one specific action
- Tone: Clear, educational, practical
- Add estimated read time at top (words ÷ 200)
- Total: 600-1200 words

Source content:
[Paste content here]
```

---

## Content Threading System

### The 30-Day Content Calendar (1 Source = 52 Outputs)

**Week structure from one anchor piece:**

| Day | Format | Platform | Purpose |
|---|---|---|---|
| Mon | LinkedIn post | LinkedIn | Main audience |
| Tue | Tweet thread | Twitter/X | Catch casual scrollers |
| Wed | Email excerpt | Newsletter | Deepen relationship |
| Thu | LinkedIn poll question | LinkedIn | Boost engagement |
| Fri | Short quote graphic | Instagram | Visual audience |
| Sat | Short tip | Twitter/X | Consistency signal |
| Sun | Blog excerpt | DEV.to | SEO + discovery |

**Per quarter:**
- 13 anchor pieces → 676 content units per year
- 13 anchor pieces × 4 quarters = 52 weeks of content

---

## Quality Standards

Every repurposed piece must pass these 3 tests before publishing:

1. **The Stand-Alone Test:** Would someone understand this without reading the original?
2. **The Value Test:** Does this deliver specific insight, not just summary?
3. **The Action Test:** Does the reader know what to do next?

If any answer is NO, rewrite that section.

---

## Common Mistakes

1. **Cross-posting without adapting** — Copy-paste signals low effort. Always platform-native.
2. **Ignoring character limits** — Platform constraints force creativity. Respect them.
3. **Publishing without CTA** — Content without a next step has zero follow-through value.
4. **Repurposing weak source content** — Garbage in, garbage out. Audit the source first.
5. **Publishing everywhere at once** — Start with 2 platforms, nail them, expand.

---

## Reference Files

For detailed platform-specific templates and examples, see:
- `references/linkedin-format.md` — Full LinkedIn post template + 5 example hooks
- `references/twitter-thread-format.md` — Thread structure + hook library
- `references/{{profile.lateness.stakeholders.channel}}-format.md` — Email subject lines + opener templates
- `references/calendar-template.md` — 30-day content calendar template
