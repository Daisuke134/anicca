# F4c — publish-to-x (X / Twitter Articles) — monetization + plan — 2026-06-25

Web-researched (X official help/docs, verbatim). The 4th platform for the same Automaton article, after
note(membership) / Zenn(free) / Substack(paid).

## How you make money writing on X (sourced)
| Rail | Mechanic | X cut | Eligibility |
|---|---|---|---|
| **X Subscriptions** (Subscriber-only Articles) | monthly sub; non-subs see preview + Subscribe button; subs see full | **0%** (keep ~97% on web/Stripe; Apple/Google take 15-30% in-app) — BETTER than note/Substack ~10% | 18+, **2,000 verified followers**, **5M organic impressions / last 3 months**, Premium, apply in Creator Studio (may waitlist) |
| **X Articles** (long-form) | rich long-form (headings/bold/images/lists). Audience = Public OR Subscribers-only | — | **Premium ($8/mo)** at least (Premium+ $40/mo for full surface). Dais HAS Premium. |
| Creator Ad Revenue Sharing | payout by verified-user impressions | — | 500 verified followers + 5M imp/3mo + Premium. Marginal for writers. |
| Tips / paid-DM / subscriber Spaces | bundled into a subscription | — | sub prerequisite |

Verbatim: "X does not take a revenue share ... ~97%" (help.x.com/en/using-x/subscriptions). Eligibility "at least
2,000 verified followers / at least 5M organic impressions within the last 3 months" (subscriptions-creator).
"Subscriber-only Articles are a great way to monetize ... with Subscriptions" (using-x/articles).

## CAN WE PAYWALL THIS ARTICLE ON X NOW? → NO
Subscriber-only Articles require X Subscriptions ENABLED, which requires 2,000 verified followers + 5M
impressions/3mo. We don't have that yet. Premium lets us WRITE Articles but only PUBLIC ones until eligible.

## THE PLAN — 2 stages
```
STAGE 1 (NOW): X = a STANDALONE FREE explainer Article (the SAME content as the Zenn free version:
  Automaton とは → どう動いて + honest close). Build traction → 2,000 verified followers + 5M imp/3mo.
STAGE 2 (after eligibility): apply for Subscriptions → publish the FULL version as a Subscriber-only Article
  (setup + results, like note/Substack paid), X cut 0%. + enable Ad Revenue Sharing as a bonus.
```

## ★ ETHICS — NO SCAMMY FUNNEL (Dais 2026-06-25) ★
The X free Article is a COMPLETE, honest, standalone explainer — it does NOT link out to / tease "the rest is on
my paid note/Substack". We do NOT drive X readers to the paid versions as a bait funnel. "we don't do scammy
dirty shit." X stage 1 = give a genuine free article (like Zenn), full stop. Money on X comes LATER, honestly,
via X Subscriptions once we've earned the audience — not by dangling paid links now. (Mirrors
feedback_sincere_no_unethical_upsell: free content is a complete gift, never a teaser for a paid link.)

## CONTENT for the X Article (stage 1)
= the Zenn explainer (free, honest, no run-claims, NO upsell/funnel link). X Articles support headings/bold/
images but NOT native tables/mermaid → render tables+diagrams to PNG (reuse the note/substack assets) OR keep it
text+image-light. Title honest (徹底解説 / 解説, no 検証してみた since the run is not shown).

## POSTING + AUTOMATION
- Account must be on Premium (✓ Dais). Two paths:
  (a) Browser (daily-driver CloakBrowser, logged into X per HARD 0.39): x.com → compose Article → fill → publish.
  (b) Official Articles API: `POST /2/articles/draft` → `POST /2/articles/{id}/publish` (OAuth2 PKCE, scopes
      tweet.write/tweet.read/users.read, ~$0.015/call). Account still needs Premium.
- VERIFY: open the published Article in the browser (daily-driver) + Read it — title, body, images sane size,
  honest, no funnel link. (Same verify discipline as note/Zenn/Substack: browser eyes-on, not just "posted".)

## Acceptance
1. A FREE public X Article live (the explainer), honest, no upsell/funnel link, images sane size — verified in
   the browser by eye.
2. Recorded that paid X Subscriptions is STAGE 2 (gated on 2,000 followers + 5M imp/3mo).

## DECISION 2026-06-25 — use wshuyi/x-article-publisher-skill (don't reinvent)
Found + adopted https://github.com/wshuyi/x-article-publisher-skill (818★, updated 2026-06-24). BROWSER-based
(x.com/compose/articles, NOT the API → no API credits; the X API returned 402 CreditsDepleted = pay-per-use, 0
credits). Installed → ~/.claude/skills/x-article-publisher (scripts: parse_markdown.py, copy_to_clipboard.py,
table_to_image.py). Deps: Pillow + pyobjc-framework-Cocoa (clipboard rich-text paste). Workflow = parse md →
open editor → cover → title → paste HTML (Cmd+V, formatting preserved) → insert content images at block_index →
SAVE AS DRAFT (never auto-publish). Tables/mermaid → PNG (table_to_image.py / mmdc-or-kroki). We DRIVE the
daily-driver browser via CDP (:9222) following the SKILL.md steps. Source article = the Zenn FREE explainer
(automaton-jido-kasegu-ai-kaisetsu.md): honest, run-claims cut, NO funnel link. Then VERIFY the draft in the
browser (image sizes sane, formatting, honest) → publish public (free). Premium required (Dais has it).

## BUILD STATE 2026-06-25 — setup DONE, raw-CDP editor automation FLAKY (honest)
DONE: skill installed (~/.claude/skills/x-article-publisher) + deps (Pillow, pyobjc-Cocoa) + the article PREPPED
(prep-x-md.py → x-article.md: Zenn free explainer, tables→PNG via table_to_image.py, mermaid→PNG via kroki, H1
title + thumb cover) + parse_markdown.py works (title, cover, 18 content_images w/ block_index, html 20876, 5
dividers) + identified editor fields (title = textarea placeholder "Add a title"; body = [data-testid=composer];
cover = top area; Publish btn top-right). copy_to_clipboard sets NSPasteboardTypeHTML = rich (good).
BLOCKER: driving the X Article editor via RAW CDP (connect_over_cdp :9222 + pg.keyboard/click) is FLAKY — across
7 attempts the editor opens but field selectors intermittently fail (title textarea found ~50% of the time; one
paste landed in a stray post-composer as plain HTML). The skill is DESIGNED for Playwright MCP (browser_snapshot/
click/type), which inspects + targets the editor reliably; raw CDP replication is unreliable. Also created ~6
empty "(Needs title)" drafts (private, need cleanup).
NEXT (realistic): connect a Playwright MCP (the skill's intended tool) → invoke the x-article-publisher Skill →
it drives the editor as designed. OR keep hardening the raw-CDP flow (slower). Verify the published Article in the
browser either way.
