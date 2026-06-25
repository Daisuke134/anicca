# F4b — publish-to-substack skill (design) — 2026-06-24

Mirror of the note (browser) + Zenn (git) publishers, for Substack. Goal: when Dais says "publish", the same
Automaton source md goes to Substack as a free honest explainer + a paid section, monetized, verified E2E.

## Which tooling we use (already installed — NOT building from scratch)
| tool | repo | location | role |
|---|---|---|---|
| **substack-cli** ★the one in the openclaw folder★ | **anshulkhare7/substack-cli** | `~/.openclaw/external/substack-cli` | CLI: draft/publish/update, `--audience` |
| substack-mcp | nanameru/substack-mcp | `~/Developer/substack-mcp` | MCP: create_draft/publish_draft/set_cover_image |
| substack skill | — | `~/.claude/skills/substack/SKILL.md` | wraps the MCP |

All three sit on `ma2za/python-substack` (the unofficial internal API). **Method = API/CLI (like Zenn, NOT browser
like note).** Auth = `substack.sid` cookie (grab once from a logged-in browser; magic-link accounts must set a
password first). NO official public API exists; python-substack reverse-engineers the internal one → treat call
volume conservatively (space out publishes); the cookie can expire → re-auth.

## How we monetize on Substack (record — Dais asked to write it in)
- **Model = recurring paid subscriptions only** (NO one-off purchase). Creator sets **monthly (floor $5/mo) +
  annual (~$30/yr) + optional Founding tier** (donation-like, must be ≥ annual price). Source:
  support.substack.com/hc/en-us/articles/360037459952 + 360042039091.
- **Cut:** Substack 10% + Stripe (~2.9% + $0.30 + 0.7% recurring). Source: 360037607131. Publishing itself is free.
- **Payout:** the writer connects their **own Stripe** ("Connect with Stripe", one-time) → payouts to bank via
  Stripe. This is the one human-cred step → do it ONCE via the persistent daily-driver browser (HARD RULE 0.39),
  then the skill runs API-only.
- **In-post paywall:** a `{'type':'paywall'}` content node placed between paragraphs (python-substack README).
  Free readers see the preview above the line + "This post is for paid subscribers" + a Subscribe button.
  GOTCHA: the paywall only renders when `audience` ∈ {only_paid, founding}; switching to everyone/free REMOVES it.
  Payments must be enabled (Stripe connected) first.

## ★ WHERE we paywall (Dais asked) — SAME boundary as note ★
The split mirrors note exactly (one post = free hook + paid body):
```
FREE (above the paywall node)  = the EXPLAINER:
  Automaton とは → 最も賢いAIが$5… → Web 4.0 → 自分で稼ぐAI全体像 →
  Automatonは「どう動いて」生きているのか → 実際に動かす の導入1行(「…再現できます。」まで)
── {'type':'paywall'} ──  (same boundary as note's membership gate / before「取得してビルドする」)
PAID (below)                   = the SETUP + RESULTS:
  取得してビルドする 以降の全手順 + で、稼げたのか(結果・数字) + 全ログ
```
So: **free = what Automaton is + how it works (explanation); paid = the actual setup steps you run + the results/
logs.** Identical to note. (Zenn is the outlier = free explainer only, no paid section.) Title can be the honest
note-style title (it DOES include the run/results, which are in the paid half) — unlike Zenn's explainer-only title.

## The skill (publish-to-substack) — mirrors note/zenn pattern
```
publish-to-substack.sh publish <source.md> --title … --audience only_paid --paywall-before "取得してビルドする"
 1. ADAPT: source md → Substack post. Markdown → python-substack Post nodes. Insert {'type':'paywall'} at the
    --paywall-before boundary (free explainer above, paid setup/results below). Mermaid → Substack has no native
    mermaid → render to PNG (like note) OR drop diagrams in the free part; tables → Substack renders markdown
    tables. (DIFFERENCE vs Zenn: no native mermaid.) cover image via upload_image()/set_cover_image().
 2. GATE: reuse the no-lie philosophy ONLY for the FREE part is N/A here (Substack's PAID part legitimately
    contains the run/results, like note) → instead verify the SPLIT: free part must not contain the paid data,
    title matches content. (note-style, not zenn-style.)
 3. DRAFT: api.post_draft(post.get_draft()) → returns draft id + edit_url (nothing public).
 4. RENDER VERIFY: fetch the draft preview → confirm free preview renders + the paywall node sits at the boundary.
 5. PUBLISH (gated): api.prepublish_draft(id) → api.publish_draft(id, send=…). --no-send for silent; or send a
    free preview to free subscribers for distribution.
 6. E2E VERIFY (HARD 0.31): capture post_id + live URL → fetch → confirm (a) free preview above the line and
    (b) "This post is for paid subscribers" + Subscribe button below. No completion claim without that evidence.
```

## The ONE code gap to add (the "fixing" Dais mentioned — platforms differ)
- `substack-cli`/`client.py` `from_markdown` has `audience` but does NOT insert the `{'type':'paywall'}` node →
  add a `--paywall-marker` (e.g. `<!-- PAYWALL -->` or `--paywall-before "<heading>"`) that injects the paywall
  node at the boundary. This is the single missing piece for the free/paid split.
- Platform diffs to handle in ADAPT: no native mermaid (render PNG or omit in free), ProseMirror needs `\n\n`
  (single `\n` → HTTP 500 on Notes), prepublish before publish, draft_section_id only settable after first post_draft.

## E2E test plan (no-prod, like note's draft test)
1. Connect Stripe once (daily-driver, gated) — prerequisite for paid audiences.
2. Create a DRAFT (api.post_draft) with the adapted post (paywall node at boundary) → no public.
3. Fetch draft preview → verify free/paid split + paywall position by eye.
4. Delete the draft (no residue). Only publish for real on Dais's "go".

## Revenue role
Substack = a 3rd daily-article channel toward 10k MRR (note membership + Zenn badges/Books + Substack paid subs).
Same source md → 3 platforms, each adapted + verified. Zenn = free (reach/SEO), note + Substack = paid (revenue).

## BUILD + VERIFY LOG (2026-06-24) — E2E draft proven
- ✅ AUTH works via SUBSTACK_SESSION_COOKIE (substack.sid) + SUBSTACK_PUBLICATION=aniccabuddha.substack.com.
- ✅ substack-publish.py BUILT (scripts/substack-publish/) + RUN: created DRAFT 203497099 (audience=only_paid),
  free explainer + {'type':'paywall'} node + paid setup/results, reusing the note PNG assets (29 uploaded).
- ✅ VERIFIED deterministically (api.get_draft): 1 paywall node at node 664/1282; images + paragraphs both before
  (free: 128 paras) and after (paid: 113 paras). audience=only_paid. (Editor screenshot blocked by playwright
  rejecting the signed substack.sid cookie format — structure proven via API instead; images are the already-
  eyes-verified note assets.)
- PLATFORM LEARNINGS (the "fixing" — Substack differs from note/zenn):
  * python-substack `from_markdown` renders NEITHER tables NOR mermaid → must PNG them (we reuse note assets).
  * paywall split = build Post, `from_markdown(free)` → `post.add({'type':'paywall'})` → `from_markdown(paid)`
    (from_markdown APPENDS). `_normalize_prosemirror` on draft_body before post_draft.
  * 429 Too Many Requests on burst image uploads → pace uploads (~1.5s) + cache URLs to disk
    (~/.cloak/note-work/substack-img-cache.json) so retries skip re-upload.
  * Publishing for real (SUBSTACK_GO=1) needs Stripe connected on the publication (one-time, daily-driver) for
    the only_paid audience to actually gate.

## ★ PAYWALL PLACEMENT — researched + DECIDED (generalizable rule) ★
Web research (Substack official + beehiiv 2026 + note編集部 100-article analysis) converges on ONE rule:
**gate AFTER the explainer, at the top of the setup — free = WHAT + WHY + HOW-IT-WORKS, paid = the concrete
METHOD/SETUP + the RESULTS/numbers.** Sources (verbatim):
- note編集部 (note.com/notemag/n/na9fd8ce1a166): 「無料部分でトレーニングに必要な考え方や得られる効果を書き、
  有料部分では具体的な方法を伝える」 = free concept/benefit, paid concrete method. + 「冒頭からすべて有料に
  してしまうと…読者が離脱」 (do NOT gate at the intro).
- Substack (on.substack.com/p/why-free-posts-pay): 「the most successful publications make much of their best and
  most accessible content free.」
- beehiiv 2026: 「nothing converts subscribers better than a scoop」 — the exclusive results/numbers are a top
  gated asset; end the free part on a deliberate cliffhanger before the payoff.
- note編集部 100-article free-area = (A)共感・問いかけ (B)変化の物語(Before/After) (C)ベネフィット提示.
GENERALIZED for our [explainer → setup → results] articles (applies to note + substack; Zenn = all-free):
  FREE = explainer (what it is + how it works) ending on a cliffhanger that PROVES it works + teases the result.
  PAID = the setup (exact steps/commands) + the results (did it earn / the numbers).
  This is EXACTLY our current cut (free up to 実際に動かす intro, paid from 取得してビルドする). CONFIRMED correct.
  Conversion target 5-10% (Substack) — lever is intentional execution, gated content must over-deliver.
