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
