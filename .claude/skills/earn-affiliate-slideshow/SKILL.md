---
name: earn-affiliate-slideshow
description: >
  Earn Amazon affiliate commission by posting EDUCATIONAL faceless photo-slideshows
  (carousels) to my own niche TikTok + Instagram, with the affiliate link in BIO.
  Method = web-researched (slidestorm + valuecommerce 2026), not invented.
metadata:
  niche: AI / 生産性 (one niche, be "the AI仕事術 person")
  asp: Amazon Associates JP (tag aniccaai-22) — no follower minimum (unlike some ASPs that need 1,000+)
  format: photo SLIDESHOW (carousel), NOT video — higher reach + save/share rate
---

# earn-affiliate-slideshow

Make money the way real TikTok-slideshow affiliates do (researched 2026, sources below).

## THE METHOD (web-researched — follow this, don't reinvent)
1. **Niche-specialized account** — be known as "the AI仕事術 person" (one niche, one identity).
   valuecommerce: ジャンル特化 raises 成約率 + makes content + AI generation easier.
2. **EDUCATIONAL slideshows, not product pitches** — tips / frameworks / step-by-step / myth-busting
   (e.g. "ChatGPTでやってはいけない3つ", "AI時短ワザ5選"). ★ slidestorm: slideshows are the sweet
   spot for educational content → positions you as an EXPERT → experts get paid (affiliate). Info
   slideshows get SAVED + SHARED far more → more reach + credibility. ★ The product is NOT the hard
   sell of the slide; it's the "go deeper" resource in BIO.
3. **Affiliate link in BIO only** — TikTok/IG captions can't have clickable links; the BIO link is the
   sole funnel (valuecommerce). BIO = `amazon.co.jp/dp/<ASIN>?tag=aniccaai-22` (set AFTER 7d warmup).
4. **Engagement-optimized format** — many swipeable slides; active swiping = micro-commitments =
   stronger algorithm signal than video; high completion + save = promoted to おすすめ feed (reach
   without followers — valuecommerce: new accounts reach via おすすめ).
5. **Daily, consistent** — fresh educational slideshow daily (product/topic rotates, same template);
   "a creator with 50 educational slideshows in a niche is far more credible." Compounds over weeks.
6. **Funnel**: educational slideshow (build trust) → viewer taps profile → BIO affiliate link → Amazon
   → 成約 → commission. PR/#PR mandatory (景表法). No false claims. Protect the account (warmup, no spam).
7. **(later) dual income**: external affiliate (primary, day-1) + TikTok Creativity Program once 10K
   followers + 100K views/30d ($0.50-1.50/1000 views, higher for finance/tech/business niches).

## Content shape (educational-first; the 4-step monetization type lives at the END)
hook (curiosity/意外な結論) → 3-5 genuinely useful tips/steps (the value, save-worthy) →
soft bridge ("もっと深く知るなら") → CTA: "リンクはプロフィール / #PR". The affiliate product = the
"go deeper" resource, introduced softly, not pitched hard. (Matches X-article ① monetization 4-step:
trust → problem → solution-as-suggestion → next action.)

## Pipeline (reuse, $0)
- Content engine = `slideshow-video-maker` skill (chatgpt-imagegen $0 stills + PIL text overlay).
- Product link = `scripts/build-link.mjs <ASIN>` → tag aniccaai-22.
- Account = `ig-account-create` → `ig-account-warmer` (7d) → post (carousel) → BIO link.
- Earn ledger = `scripts/record-affiliate-earn.mjs` (un-fakeable; external Amazon report rows only).

## ★ HOW IT ACTUALLY EARNS (not just posting) — the loop + verification engine ★
Posting ≠ earning. Real ¥ = an external human clicks the BIO link and BUYS on Amazon within 24h.
We can't force a sale; we run the loop at volume, measure REAL results, amplify winners, and
PROVE the money with an un-fakeable ledger (per memory: past earn skills earned ¥0 because
verification was missing — this skill's HEART is the verification engine).

THE DAILY EARN LOOP (autonomous, claude -p + launchd — no human):
```
read STATE → research a fresh niche topic/product → generate EDUCATIONAL slideshow ($0)
  → post to OWN account (carousel) + ensure BIO affiliate link
  → MEASURE real results: `scripts/amazon_report.py` reads the LIVE Amazon Associates
    dashboard (clicks / ordered / 紹介料) — the "actually earned" GATE (real_sale = commission>0)
  → if commission>0: `scripts/record-affiliate-earn.mjs` writes the REAL row to the un-fakeable
    ledger (rejects internal/test rows; only external Amazon report rows count)
  → AMPLIFY winners (topics/hooks that drove clicks/sales), kill losers → write STATE → repeat
```
★ "Done = earned" is provable ONLY by a real Amazon-report commission row in the ledger. ★

## ★ GENERAL skill — any AI earns, human-funded OR self-funded, no human in the loop ★
This is NOT specific to me. Any AI runs the SAME skill with its OWN:
- account (via `ig-account-create` → `ig-account-warmer`), OWN niche,
- OWN Amazon Associates account + tag (replace `aniccaai-22`), OWN Amazon login,
- OWN payout (its own bank/wallet).
Everything is env/config-driven (tag, niche, account handle, ASP login). The loop + content engine
+ verification engine are shared (~/.agents/skills). → replicate the kit, every AI earns autonomously.

## Sources (researched 2026)
- slidestorm.ai/articles/can-you-make-money-from-tiktok-slideshows (slideshow = content engine for external revenue; educational = expert positioning; save/share).
- valuecommerce.ne.jp/stepup/tiktok_affiliate (niche 特化; link in BIO only; おすすめ reach; some ASPs need 1,000 followers, Amazon doesn't).
- X-article ① (やまもとりゅうじ): the research→write-in-voice→schedule→analyze→feedback LOOP + monetization 4-step type.
