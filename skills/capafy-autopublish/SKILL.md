---
name: capafy-autopublish
description: >
  THE single skill to publish profitable, rejection-proof skills to the Capafy
  marketplace end-to-end, verification-baked. Load this one skill and you can:
  pick a proven-profitable niche, generate the skill, write a best-practice listing,
  publish it (CP1 card + CP2 LLM-key host + CP3 submit) via the CloakBrowser
  daily-driver, and verify it (linter + browser + remote-status). Use for ANY
  Capafy publishing. This skill VENDORS the Capafy CLIs internally — never invoke
  capafy-publisher / capafy-user directly; everything routes through here.
---

# capafy-autopublish — one skill, full Capafy publishing + verification

★ This is the ONLY Capafy skill to invoke. ★ It vendors the Capafy seller CLI
(`vendor/capafy-publisher`) and the market-search CLI (`vendor/capafy-user`).
Other Claude instances: do NOT use those two directly — use this skill.

## What sells on Capafy vs what does not (read first)
Capafy has two agent types:
- **run_online** (cloud_hosted, subscription): the buyer CHATS with the skill in a
  **sandbox** — only the model + what the buyer pastes. NO web, tools, accounts,
  browser, files, or cron. **Sellable test:** "Does the buyer get full value by
  chatting, from model + pasted input alone?" YES → sellable.
  - ✅ humanizer, copywriter, slide-maker (HTML), data-analyst (pasted data), strategist
  - ❌ photo-publisher, auto-poster, scheduler, "researches the web/competitors"
    (sandbox can't act on the world or browse → useless / gets REJECTED, see C4).
- **download** (buyout, one-time): the buyer runs the package in THEIR own env — can
  include tools/browser. (The auto-publisher itself could be sold this way, not run_online.)

We publish **run_online subscription** skills that are sandbox-complete and copy a
proven winner's pricing/structure verbatim.

## The one command (verification-baked)
```
scripts/publish_one.sh <skill-dir> <LISTING.md> <icon.png>
```
Runs: **[0] lint → [1] init → [2] CP1 → [3] configure → [4] CP2 → [5] ship →
[6] CP3 → [7] remote verify → [8] ledger**. Fail-closed at every step (dies unless
skills=1, CP2=VERIFIED, and final status=1 ∧ isConfirmedConfigKeys=1).
After it prints ✅, **you still do the browser render check yourself** (HARD 0.31/0.38),
then commit+push the ledger.

## Verification policy (verification is mandatory — anything unverified is slop)
1. **lint_listing.py** (embedded, every publish, fail-closed) — rejection-proof:
   blocks overclaim phrases (browse/scrape/fetch/live/real-time/retrieval/posts/
   sends/.pptx/guaranteed/undetectable…) unless negated, and enforces title≤50 /
   short≤500 / pricing table. This is the C4-rejection learning, made deterministic.
2. **VCSDD adversary** (`vcsdd:vcsdd-adversary`) — spawn for RISKY listings only
   (anything the linter can't judge: subtle retrieval/tool/guarantee claims). Pure
   writing skills can skip it.
3. **browser + remote-status** (me, every publish) — render check + publish-remote-status
   real data (status=1 ∧ cfg=1 ∧ run_online ∧ title ∧ model ∧ pricing).

## How to add ONE new listing (the repeatable recipe)
1. **Pick a winner**: `vendor/capafy-user/scripts/capafy_http.py POST /agent/agents/search`
   (X-Access-Token header) → find a proven seller; GET `/agent/agent/agents/<id>` for its
   pricing/trial/category/structure. Copy facts verbatim; write original words.
2. **Build the skill** under `$LIFE_MANAGER_REPO/skills/<name>/` (pure-LLM, sandbox-complete,
   honest; no web/tool/account claims). Add `test/case1.md`. Grep for leaks (CLEAN).
3. **Write the listing** `$LIFE_MANAGER_STATE_HOME/features/capafy-<name>/LISTING.md` with the
   header (Primary Model / category / tags), a pricing table copied from the winner, and
   `## Title / ## shortDescription / ## welcomeMessage / ## detailedDescription`.
4. **Icon**: OpenAI image_generation (`CAPAFY_HOST_OPENAI_KEY`) → 512px PNG.
5. **Lint**: `scripts/lint_listing.py <LISTING.md>` until PASS.
6. **(risky only)** spawn VCSDD adversary → require PASS.
7. **Publish**: `scripts/publish_one.sh <skill-dir> <LISTING.md> <icon>` → status=1.
8. **Browser-verify** + record in `state/published.jsonl` + commit+push.

## Hard-won rules (full detail in PUBLISHING_RUNBOOK.md)
- **WE COPY**: winner's price/trial/category/structure verbatim; no AI-invented numbers.
- **LEAK GUARD**: publish from clean WS `$LIFE_MANAGER_STATE_HOME/work/capafy` (skill only), never LIVE.
- **LLM host (CP2)**: OpenRouter `anthropic/claude-sonnet-4.6`, format `openai-responses`,
  key `CAPAFY_HOST_OPENROUTER_KEY`; delete any blockrun/localhost card.
- **CP1 15 gotchas** baked into `drive_cp1.py` (RHF element.fill, real mouse clicks,
  unique title, 下書き persist, monetization heading-click, Subscription scroll, provider
  field, per-plan trial = winner config, On-Demand, DPA checkbox, price-tab SVG green,
  get_by_text form-mount, anchored Add Plan). See RUNBOOK §"NEW-AGENT CP1".
- **Cap**: max 5 unlisted (status 0-3) at once; publish-init fails when full. status=4 frees a slot.
- **Browser**: CloakBrowser daily-driver (CDP :9222), never close it (HARD 0.39).

## Folder map
```
capafy-autopublish/
├── SKILL.md (this) · BEST_PRACTICES.md · PUBLISHING_RUNBOOK.md
├── scripts/ publish_one.sh · lint_listing.py · build_config.py · drive_cp1.py
│            · drive_checkpoint2.py · niche_picker.py · logo_gen.js
├── vendor/  capafy-publisher/ (packager.py = Capafy seller CLI, self-updating)
│            capafy-user/      (capafy_http.py = market search CLI)
└── state/   published.jsonl (ledger)
```
Canonical copy lives in `~/.claude/skills/capafy-autopublish` (mirror in `$LIFE_MANAGER_REPO/skills`).
