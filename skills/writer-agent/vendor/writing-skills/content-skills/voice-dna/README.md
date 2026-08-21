# Voice-DNA — teach Claude to write like *you*

The other four skills make good content. This one makes it **yours**.

Voice-DNA is the one skill you can't just download — you build it from your own content in about 2 minutes. You feed Claude ~20 of your real posts or video transcripts, it extracts how you actually sound (your sentence shapes, signature phrases, hooks, tics, and the things you'd *never* say), and saves it as a profile every other skill can read.

---

## How to build it (≈2 minutes)

1. **Gather your last ~20 posts.** Best input = **spoken transcripts of your own short-form videos** (how you actually talk), not just captions. Even 10 is enough to start; more = sharper.
2. **Paste them into Claude** with the prompt below.
3. **Claude returns a `voice-dna.md`** — a profile of how you sound: your sentence shapes, signature phrases, your hooks, your tics, and your anti-voice (what you'd never say).
4. **Save it as a skill** at `~/.claude/skills/voice-dna/SKILL.md` (wrap it with the template below). Now every piece Claude writes for you can read it and match your voice.

---

## The prompt (copy-paste — this is the magic)

```
You are building my VOICE-DNA — a reusable profile of how I actually write and talk, so you can
write in my voice later.

Below are 20 of my real posts / video transcripts. Read ALL of them first. Then build a profile.
Do NOT summarize what they're about — analyze HOW I express myself.

Output a single markdown file with these sections:

## How I sound
3–5 sentences on my overall register, energy, and pacing. Be specific and quote me.

## Sentence shapes
How I build sentences. Length patterns. Do I run thoughts together with "and/but/so," or write
short and clipped? Punctuation habits. Quote 3–4 real examples.

## Signature phrases & tics
The exact words, openers, transitions, and verbal habits that recur across my posts. List them
verbatim with the post they came from. Include filler/slang I actually use.

## How I open (hooks)
The patterns in my first lines. What kind of hook do I reach for? Quote my 5 strongest openers.

## How I close (CTAs / last lines)
How I end things. My real CTA style, word for word.

## Anti-voice (never do this)
Words, phrases, and moves that would instantly sound NOT like me. Be strict.

Rules:
- Ground every claim in a real quote from my posts. No generic adjectives.
- If I write differently when spoken vs. written, note the difference.
- Keep it tight enough to drop into a system prompt.

Here are my posts:
[PASTE 20 POSTS / TRANSCRIPTS HERE]
```

---

## Save it as a skill

Take the markdown Claude returns and save it at `~/.claude/skills/voice-dna/SKILL.md` with this frontmatter on top, so it installs and fires like the other four:

```
---
name: voice-dna
description: Use when writing ANY content in my voice — captions, scripts, posts, emails. Read this
  profile first and match my sentence shapes, signature phrases, hooks, and CTAs. Never write in a
  generic voice when this exists.
---

[paste the voice-dna.md the prompt produced here]
```

Now `storytelling`, `viral-hooks`, and `anti-ai-writing` all have a real voice to check against instead of falling back to mechanics alone.

---

## Pro tip

Re-run the prompt every few months as your content evolves — your voice drifts, and a fresh 20-post sample keeps the DNA current.
