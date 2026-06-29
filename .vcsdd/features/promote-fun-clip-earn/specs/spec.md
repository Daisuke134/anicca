# Behavioral Spec — promote-fun-clip-earn (VCSDD, lean)

## Goal (provable finish line)
An autonomous, no-human loop that earns real USDC-Solana on Promote.fun by clipping active brand
campaigns and posting to the verified IG account @aishigoto.labo. DONE = a real on-chain USDC inflow
recorded in the ledger via a confirmed Promote.fun payout (or, pre-payout, a clip LIVE + submitted +
accruing views, with every gate evidence-backed).

## Context (already proven E2E, no-human)
- Promote.fun account `aniccaclips` created + logged in (creds `~/.cloak/promotefun-anicca.json`).
- IG `@aishigoto.labo` LINKED + ✓Verified on Promote.fun (bio-code BQ8RUXY8).
- Auth: web login (username+password from creds) → session cookie; email OTP via `gog gmail`
  (needs env `GOG_KEYRING_PASSWORD` from ~/.openclaw/.env).
- Payout currency = USDC on Solana; wallet `xxKC33TYJ2czjGQAADrvDCLjF6pRvtHX125fCwP5u9H`.

## EARS Requirements
- REQ-1 (campaign select): WHEN the loop wakes, the system SHALL fetch ACTIVE Promote.fun campaigns
  (authenticated) and select one not already clipped this cycle, preferring higher (CPM × remaining budget).
- REQ-2 (source + specs): WHEN a campaign is selected, the system SHALL obtain its source video URL and
  clip spec (length 15–45s, vertical 9:16, allowed platforms incl. Instagram).
- REQ-3 (clip): WHEN source + spec are known, the system SHALL produce a 15–45s 1080×1920 clip
  (reuse earn-clip-rewards: yt-dlp + faster-whisper + ffmpeg) meeting the spec; NO mock asset.
- REQ-4 (post): WHEN a clip exists, the system SHALL post it to @aishigoto.labo via ig-reels-poster
  (browser-direct, local=CloakBrowser / cloud=headless) and capture the live post URL (verify on profile).
- REQ-5 (submit): WHEN posted, the system SHALL submit the post URL to the campaign on Promote.fun and
  confirm the submission is accepted (status visible in stats).
- REQ-6 (measure): The system SHALL read views + earnings per submission from Promote.fun stats.
- REQ-7 (record-earn): WHEN Promote.fun pays out USDC on-chain to the wallet, the system SHALL record
  ONLY the real EXTERNAL on-chain USDC inflow to the ledger (lib/ledger.mjs isProfitable: tx+0x1+net>0+external).
- REQ-8 (no-human INVARIANT): every step SHALL run with zero human — captcha→CapSolver, OTP→gog gmail,
  login→stored creds. ANY human step = a defect.
- REQ-9 (idempotent + bounded): safe to run every wake; dedup posted campaigns (history ledger);
  respect SKILL_TIMEOUT_S (split: generate vs post vs measure if >timeout).
- REQ-10 (slot contract): entrypoint `run.sh` spawnable by runSkill, reads wallet from env (keys scrubbed),
  prints ONE structured line (did + earned_usdc/cost_usdc), exit 0.

## Verification architecture (how each REQ is checked — maker≠checker)
- REQ-1/2/5: live Promote.fun API/UI read shows the selected campaign + accepted submission (fresh screenshot/JSON).
- REQ-3: the clip file exists, ffprobe confirms duration 15–45s + 1080×1920 + audio stream present (no silent).
- REQ-4: the post URL resolves on @aishigoto.labo profile (a /p/ or /reel/ tile), browser-verified.
- REQ-6: stats endpoint returns view count for the submission (real number, may be 0 early — honest).
- REQ-7: ledger line has tx + status 0x1 + external:true + net>0 (an actual on-chain USDC transfer).
- REQ-8: grep the impl for any human-gating call; none allowed. fresh-context adversary audits.
- 5-GATE (earn engine): V1 campaign-picked / V2 clip-posted-live / V3 submitted-accepted / V4 views-inbound /
  V5 USDC-withdrawn-recorded. pass-without-evidence is grep-blocked.

## Out of scope (this feature)
- TikTok (IG only for now). Slideshow track (@aishigoto.labo educational) stays SEPARATE.
- The OUTER self-improvement loop (#6) + self-heal (#8) are follow-on features.

## NOTE / risk
@aishigoto.labo is day-1 warming + AI-niche; campaigns are mainstream (Crocs/music/sports). Dais OK'd
using it. A dedicated clip account may be cleaner later. The bio still holds BQ8RUXY8 (removable).
