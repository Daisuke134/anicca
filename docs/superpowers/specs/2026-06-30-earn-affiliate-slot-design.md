# earn/affiliate slot — daily-loop design (2026-06-30, VCSDD, builder=main agent)

EARN-2. Make `earn/affiliate` an independent EVERY-DAY loop that posts an educational faceless
slideshow daily to our own niche account, Amazon affiliate link in BIO → commission. Clip is the
proven daily-loop reference; the carousel DELIVER path already works (ig-account-poster posted a real
6-slide carousel to @aishigoto.labo, verified). So affiliate's gap is the PRODUCE path + slot wiring,
not the deliver path (unlike gig, whose deliver was missing).

## Money path
educational slideshow (AI/productivity niche) → daily post (IG/TikTok carousel) → viewer taps profile
→ BIO Amazon link (Associates JP tag aniccaai-22) → 成約 → commission USDC. No campaign/min-followers
needed; #PR mandatory (景表法). record-affiliate-earn.mjs (INV-7) counts only real commission.

## The earn-core (clone clip's pattern; deliver is already solved)
1. **PRODUCER** (daily) — `producer.sh`: brain writes a deck (hook → 3-5 genuinely useful AI tips →
   soft bridge → CTA "リンクはプロフィール #PR") → generate backgrounds → compose_slides.py → verified
   1080x1920 composed_*.png → drop the slide set + caption into ~/affiliate/queue/<id>/.
2. **POSTER/ACTOR LOOP** — `run.sh` (loop slot contract, EARN_MODE=discover|execute): drain queue →
   post the carousel via ig-account-poster to the ready affiliate account → ensure BIO has the Amazon
   link → record (earn_usdc 0; commission recorded later by record-affiliate-earn). + affiliate-cli.sh
   core (tmux headless claude-p + daily cron) + healthcheck launchd.
3. **VERIFY gate**: verify_slides (each composed PNG exists, 1080x1920, non-empty) before queueing;
   browser-verify the live carousel after posting (投稿 count up, images render).

## Reality gates (must hold; honest if not)
- compose_slides.py runs (PIL ok ✓) — needs a deck.json + slide_<n>.png backgrounds upstream (producer provides both).
- ig-account-poster carousel deliver = PROVEN (@aishigoto.labo). ✓
- Affiliate NICHE account: none yet → create one no-human via ig-account-create (Gmail +alias), niche = AI仕事術, OR (interim) use a sanctioned test account with self-delete for E2E.
- Amazon Associates JP tag aniccaai-22 present (per skill). Commission only lands after real traffic → sale (long game, like clip reach).

## Build order (VCSDD: spec→RED→GREEN→adversary→no-mock E2E→my verify)
1. PRODUCER: deck-gen + bg-gen + compose + verify_slides → a real verified slide set in queue (E2E: real PNGs).
2. run.sh slot + earn-core (affiliate-cli.sh + healthcheck + launchd), daily.
3. Post one real carousel to our own account (browser-verified), BIO link set. (account: create or sanctioned-test+delete)
4. record-affiliate-earn wired (INV-7) — commission accrues later.
DONE = a real educational slideshow posted to our own account daily, BIO Amazon link live, verified in browser.
"composed images exist" ≠ done; "posted + rendered live" = done for the post step; real USDC = commission (later).
