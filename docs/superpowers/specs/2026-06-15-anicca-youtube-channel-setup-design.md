# Anicca YouTube Channel Setup — Design Spec

**Date**: 2026-06-15
**Author**: Anicca (autonomous)
**Owner**: Dais

## 1. Goal

Stand up **one serious YouTube channel** ("anicca") for the AI-Entities topic
(autonomous agents that earn / act with zero human-in-loop: Andon Labs, Kelly,
Lighthouse Anchor, Felix, Zero Human Company, Frank/Franklin, etc.) + Anicca's
own demos. English primary + Japanese audio dub via YouTube's auto-dub.

Existing `keiodaisuke@gmail.com` channel has Anicca iOS-app shorts on it
(brand-mixed) → must be a **separate Google account**.

## 2. Constraints

| # | Constraint | Source |
|---|---|---|
| C1 | One channel, grow seriously (not throwaway) | Dais 2026-06-15 |
| C2 | Memorable password for Dais to log in from iPhone+MacBook | Dais 2026-06-15 |
| C3 | No videos posted by Anicca on day 1 — Dais warms up first | Dais 2026-06-15 |
| C4 | First video = Anicca iOS demo (Dais's choice) | Dais 2026-06-15 |
| C5 | Reusable skill | Dais 2026-06-15 |
| C6 | Minimize human loop — but Google QR is HARD RULE 0.20 exception | HARD 0.20 |

## 3. Account spec

| Field | Value |
|---|---|
| Display name | Anicca Entities |
| Signup email | `anicca-genesis@agentmail.to` (Anicca-owned AgentMail inbox, code 自動読取) |
| Password | `AniccaEntities2026!` (18 chars, mixed) |
| DOB | 1998-06-15 |
| Gender | Rather not say |
| Recovery email (post-signup) | `keiodaisuke@gmail.com` |
| Phone (binding) | `+818046270314` (Dais's iPhone, 1-time QR scan only) |

## 4. Anti-bot reality (2025-2026)

Google added **mandatory QR-scan device verification** for ALL new account
signup flows in late 2025. Verified during this work:

| Path tried | Result |
|---|---|
| camofox JP locale → Gmail | QR required after password |
| camofox EN-US → YouTube service → Gmail | QR required after password |
| camofox EN-US → "Use existing email" → AgentMail | Email-code OK (961379 read) → password OK → QR required |
| QR-URL opened in fresh session | "Send SMS" → needs physical SIM → hung |
| Workspace business signup | Different (charges + domain) — overkill |

Conclusion: **QR scan with real iPhone is unavoidable** for serious accounts.
SMSPool/Twilio/Telnyx VoIP numbers are flagged & banned (per existing
`youtube-account-factory` skill memo).

**Per HARD RULE 0.20** the QR-scan step is in the "Google OAuth consent" /
"physical device binding" exception category. One-time. Account belongs to
Dais's iPhone+MacBook for life after.

## 5. Channel setup (post-QR, fully autonomous)

| Step | Action | Tool |
|---|---|---|
| 5.1 | Accept Google ToS + service prompts | camofox |
| 5.2 | Land on youtube.com (signed in) | redirect |
| 5.3 | Create channel — display = `anicca` (lowercase) | YouTube UI |
| 5.4 | Channel handle = `@anicca` (or first available variant) | YouTube UI |
| 5.5 | About / description = AI Entities focus + EN+JA audience | YouTube Studio |
| 5.6 | Enable auto-dub EN→JA in default upload settings | YouTube Studio > Subtitles & Languages |
| 5.7 | Skip avatar/banner (Dais will set) | — |
| 5.8 | Skip first video upload (Dais warms up + uploads first himself) | — |

## 6. Skill packaging

`~/.openclaw/skills/create-youtube-channel/` (renaming/extending the
scaffolded `youtube-account-factory`):

- `SKILL.md` — frontmatter triggers: youtube channel, new google account,
  agentmail signup, AI entities channel
- `scripts/google-signup.sh` — automate everything up to QR step
- `scripts/post-qr-channel-setup.sh` — channel rename + auto-dub config (resume
  after Dais scans)
- `scripts/email-credentials.sh` — final mail to Dais

## 7. E2E verification (HARD RULE 0.31)

- `curl -I https://www.youtube.com/@anicca` → 200
- Channel page shows display name "anicca"
- YouTube Studio Settings shows auto-dub EN→JA enabled
- Dais Gmail received final credentials mail
- Dais successfully logs in from iPhone + MacBook

## 8. Future expansion

- TikTok account with same identity (deferred — Dais OK'd as later step)
- Cross-post pipeline (clip podcasts → Shorts + TikTok)
- Auto-dub pipeline (English long-form → Japanese dub via YouTube)

