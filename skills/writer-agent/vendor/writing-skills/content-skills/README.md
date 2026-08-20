# 5 Skills That Fix Claude's Writing

Claude is a great writer in the abstract and a generic one by default — it hedges, it over-explains, it reaches for "it's not just X, it's Y," and it never sounds like *you*. These five Claude Code skills fix that, one failure mode at a time.

They chain like a story: **simple → boring → no hook → sounds like AI → not you.**

| # | Skill | What it fixes |
|---|---|---|
| 1 | **dumbify** | Rewrites anything at an 8th-grade reading level — lower mental load, higher retention — without dumbing down the idea. |
| 2 | **storytelling** | Structures content like a story that holds attention after the hook. Tension, turn, payoff — not tips in a list. |
| 3 | **viral-hooks** | Audits your hook (and your aha) against the four things that kill every opener, then rewrites it to hit. |
| 4 | **anti-ai-writing** | Strips the tells that make writing smell like AI — the negative parallelism, the recycled words, the em-dash pile-ups. |
| 5 | **voice-dna** | Teaches Claude to write in *your* voice from your last ~20 transcripts. The one you build yourself — see [`voice-dna/`](voice-dna/). |

Skills 1–4 are downloadable folders. Skill 5 is a 2-minute build from your own content (the guide is in [`voice-dna/README.md`](voice-dna/README.md)).

---

## What a skill is

A skill is just a folder with a `SKILL.md` inside — a set of writing instructions. Claude reads the `description:` line and applies the skill automatically when it's relevant; you don't call it by name. **You don't need to be technical, and you don't need Claude Code.** Pick whichever way below fits you — easiest first.

## How to use them

### 1. Paste it in — works on any plan, even free (10 seconds)

The no-setup way. Open a skill's `SKILL.md` (unzip a download, or view it here on GitHub), copy everything, and paste it into a normal Claude chat with your draft:

```
Use the writing rules below to rewrite my draft. Then list what you changed and why.

[PASTE THE SKILL HERE]

My draft:
[PASTE YOUR CAPTION / SCRIPT / POST HERE]
```

Want to stack a few? Paste dumbify, then storytelling, then anti-ai-writing one after another in the same chat.

### 2. Install once in the Claude app — then it's automatic (Pro / Max)

Upload a skill once and Claude uses it on its own whenever you ask it to write, in any chat:

1. In Claude, go to **Settings → Capabilities** and turn on **Code execution and file creation**.
2. Go to **Settings → Customize → Skills → Upload** and drop in a skill folder, zipped (upload one at a time — zip `dumbify/` so the folder is at the root of the zip, then `storytelling/`, and so on).
3. Ask Claude to write or fix something. It reads the skill's description and applies it automatically.

Custom-skill upload needs a Pro or Max plan with code execution enabled.

### 3. Claude Code (for the technical crowd)

In Claude Code, paste:

```
Install the writing skills from this repo into my Claude Code skills directory
(~/.claude/skills/): https://github.com/artemnovitckii/content-skills
Then tell me how to restart so they're picked up.
```

Or copy `dumbify/`, `storytelling/`, `viral-hooks/`, and `anti-ai-writing/` into `~/.claude/skills/` manually and start a fresh session.

**Then build voice-dna:** follow [`voice-dna/README.md`](voice-dna/README.md) — paste ~20 of your posts, then reuse the result by pasting it in a chat (method 1) or uploading it as a skill (method 2).

---

## How they work together

Each skill has a **writing mode** (drafting) and an **audit mode** (scoring an existing draft), so you can run them on something Claude already wrote. They're designed not to fight each other:

- **dumbify** keeps words plain but never flattens the rhythm **storytelling** builds.
- **storytelling** hands the opening line off to **viral-hooks**.
- **viral-hooks** uses A-vs-B contrast on purpose; **anti-ai-writing** allows it *only when the payoff is concrete* (the "hollow vs earned" test).
- **voice-dna** gives the other three a real voice to match instead of falling back to mechanics.

A natural full pass: draft → **storytelling/viral-hooks** for structure and opener → **dumbify** for load → **anti-ai-writing** as the final filter → all of it in **voice-dna**.

---

## License

MIT — use them, fork them, ship them. See [`LICENSE`](LICENSE).

Built by [Artem Novitckii](https://www.instagram.com/artem.novitckii/). If a skill breaks or you want one added, ping me on Instagram or join the [Skool](https://www.skool.com/artemis-1201/about).
