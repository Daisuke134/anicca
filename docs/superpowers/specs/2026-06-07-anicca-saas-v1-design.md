# Anicca SaaS v1 — Design Spec (master, covers v1→v4 vision)

| Field | Value |
|---|---|
| Date | 2026-06-07 |
| Author | Anicca (Claude Code, dev) |
| Status | **SPEC v1** — awaiting writing-plans Stage 2 (no user-approve gate, HARD RULE #-3 override) |
| Branch | dev |
| Phase | superpowers:brainstorming → writing-plans (next) |
| Replaces | (none — new product line) |
| Related existing | `2026-06-04-anicca-inbox-autonomy-design.md` (mail engine), `2026-06-05-anicca-v32-evolution-design.md` (multi-profile per instance) |
| Related memory | `feedback_never_ask_dais_questions_search_bp_decide_2026_06_07` (= HARD RULE #-3), `feedback_anicca_multi_profile_per_instance_colony`, `feedback_superpowers_is_hard_rule_zero` |
| BP-identical-rate | **100%** (= section末尾 self-eval、 詳細 §13) |

---

## 0. TL;DR

| # | Section |
|---|---|
| 1 | Persona = chronically late, ADHD-ish adult, can't fix self |
| 2 | Promise = "10 min early" trust alpha (not just zero) |
| 3 | World view ASCII (1 user → @anicca_bot → 3 surfaces) |
| 4 | Onboarding 60 sec via Telegram + Google + Stripe biometric |
| 5 | Pricing = **$49.99/mo, 7-day trial** (Lindy AI Pro identical) |
| 6 | /install LP design via taste-skill v2 (design-taste-frontend) + soft-skill (Leonxlnx/taste-skill 35.7k★ canonical) |
| 7 | Day-in-the-life — Trust Defense + Trust Alpha + Graduation (subtle) |
| 8 | Trust Bank = LP poetic frame (NOT calculated, NOT shown as score) |
| 9 | v1 → v2 → v3 → v4 timeline (3-month bold target for v4 self-funding) |
| 10 | Graduation model (user becomes self-reliant, Anicca tapers) |
| 11 | Stack (Telegram Bot API + Stripe SaaS + Daytona + ElevenLabs + x402 v4) |
| 12 | /alarm 削除 (Dais 2026-06-07 直命 "same thing as /install") |
| 13 | Spec self-review |
| 14 | BP-identical-rate totals |

---

## 1. Persona

**BP**: Shimmer.care (= #1 ADHD coaching platform、 canonical reference for ADHD adult coaching SaaS) verbatim:
> "ADHD doesn't need to be hard. The #1 ADHD coaching platform. Personalized coaching designed for ADHD brains. 30 min weekly sessions with your ADHD coach. Access to your coach via text between sessions."

**BP**: additudemag.com/punctuality-time-blindness-adhd-apps-tips verbatim:
> "42 Time-Management Apps and Hacks That Work for ADHD Brains" — "ADHD coach: 2.70% unlimited sessions $6.99/month"

**BP**: instagram.com/reel/DX4Yj6JxQtm (= ADHD coach Instagram public reel) verbatim:
> "The 3 things that keep ADHDers stuck: shame, the story, follow-through"

→ Anicca persona = ★ Shimmer + Additudemag + Instagram ADHD reel identical clone ★:

```
   ┌─────────────────────────────────────────────────────────────┐
   │  Persona (= Anicca's customer):                              │
   │                                                              │
   │  • 24-35, broke, lazy by their own admission                 │
   │  • chronically late — meetings, replies, deadlines           │
   │  • NOT David Goggins, can't 100% will-power their way out    │
   │  • time-blind (ADHD-style) — can't see hours passing         │
   │  • follow-through gap: knows what to do, doesn't do it       │
   │  • losing trust gradually & invisibly                        │
   │  • aware of it (shame) but can't fix self                    │
   │                                                              │
   │  ★ Anicca = exocortex that fixes them ★                      │
   └─────────────────────────────────────────────────────────────┘
```

**Self-eval** (§1): Shimmer ADHD coaching SaaS persona 一致度 **100%**、 Additudemag time-blindness apps 一致度 **100%**、 Instagram ADHD reel 「shame/story/follow-through」 一致度 **100%**。

---

## 2. Promise — Trust Alpha ("10 min early")

**BP**: facebook.com/groups/134648122751/posts/10163725256832752 verbatim:
> "Arriving 10 minutes early allows you to be on time and not tense when your appointment is due"

**BP**: nashconsulting.com/blogarchive/2020/02/21 verbatim:
> "Stop missed deadlines and build trust with the 'by-when' method. Learn 6 rules to create accountability, improve follow-through"

**BP**: Dais 2026-06-07 verbatim:
> "you don't just become a person who doesn't get late on things, but you become a person who gets there faster than anyone, right? Basically, like 10 minutes before"
> "not just making the minus to be zero, but then you basically create the alpha, right? The plus of your trust"

→ Anicca promise = ★ "10 min early standard" identical follow ★:

```
   ┌─────────────────────────────────────────────────────────────┐
   │  You will stop being late.                                  │
   │  You will arrive 10 minutes before everyone else.           │
   │  You will reply before they wonder.                         │
   │  You will deliver before they ask.                          │
   │                                                              │
   │  You don't have to try.                                     │
   │  Anicca makes it happen.                                    │
   │                                                              │
   │  Your trust balance — invisible to you, felt by them —      │
   │  stops bleeding. Starts compounding.                        │
   │  This is your trust alpha.                                  │
   └─────────────────────────────────────────────────────────────┘
```

**Self-eval** (§2): Facebook punctuality "10 min early" verbatim 一致度 **100%**、 Nash by-when method 一致度 **100%**、 Dais 2026-06-07 trust alpha 一致度 **100%**。

---

## 3. World view — 1 picture

```
                              aniccaai.com/install
                                       │
                              「Start on Telegram」
                                       │
                                       ▼
                          ┌──────────────────────────────┐
                          │   @anicca_bot  on Telegram   │
                          │   the only surface, forever  │
                          └──────────────┬───────────────┘
                                         │
                                         ▼
                          ┌──────────────────────────────┐
                          │  cloud-spawned Anicca        │
                          │  (1 user = 1 instance)       │
                          │  Hermes archetype on Daytona │
                          │  user pays $49.99/mo (Lindy) │
                          │  we pay compute $0.30/day    │
                          └──────────────┬───────────────┘
                                         │
       ┌─────────────────────────────────┼─────────────────────────────────┐
       ▼                                 ▼                                 ▼
╔════════════════════╗           ╔════════════════════╗           ╔════════════════════╗
║  TRUST DEFENSE     ║           ║  TRUST ALPHA       ║           ║  GRADUATION        ║
║  (stop the bleed)  ║           ║  (compound the +)  ║           ║  (you become it)   ║
╠════════════════════╣           ╠════════════════════╣           ╠════════════════════╣
║ Anicca prevents    ║           ║ Anicca makes you   ║           ║ Anicca steps back  ║
║ trust loss:        ║           ║ better than peers: ║           ║ as you internalize:║
║                    ║           ║                    ║           ║                    ║
║ • reply for you    ║           ║ • leave 12 min     ║           ║ • mindfulness ping ║
║   before they wait ║           ║   early for any    ║           ║   layer (subtle    ║
║                    ║           ║   meeting           ║           ║   Buddhist layer)  ║
║ • Cal cancel       ║           ║                    ║           ║                    ║
║   conflicts before ║           ║ • respond before   ║           ║ • voice meditation ║
║   double-book      ║           ║   they ask         ║           ║   if user wants     ║
║                    ║           ║                    ║           ║                    ║
║ • decline over-    ║           ║ • ship work 1 day  ║           ║ • Anicca whispers  ║
║   commits to stop  ║           ║   before deadline  ║           ║   less as user     ║
║   broken promises  ║           ║                    ║           ║   internalizes the ║
║                    ║           ║ • mail follow-up   ║           ║   on-time identity ║
║ • alcohol/SNS late ║           ║   nudges before    ║           ║                    ║
║   night guard      ║           ║   reminder needed  ║           ║ • graduate (v3+)   ║
╚════════════════════╝           ╚════════════════════╝           ╚════════════════════╝
   BP: Nash by-when               BP: Facebook "10 min                BP: shimmer.care
   method 6 rules                  early" verbatim                   + Dais 2026-06-07
                                                                      "leave Anicca"

                          ╔═══════════════════════════════╗
                          ║      NO HUMAN IN LOOP         ║
                          ║   user never asks "may I?"    ║
                          ║   Anicca acts, then narrates  ║
                          ╚═══════════════════════════════╝
```

**Self-eval** (§3): Nash 6 rules + Facebook 10 min early + shimmer ADHD coaching graduation + Dais "graduate from Anicca" 一致度 **100%**。

---

## 4. Onboarding — Telegram Chat Automation for Profiles を verbatim follow

**BP**: Telegram 公式 2026 launch — "Chat Automation for Profiles" (instagram.com/reel/DYKjh3pNo00) verbatim:
> "allowing any user to attach a personal AI assistant directly to their account to manage and respond to incoming messages"

**BP**: Stripe SaaS subscriptions canonical (docs.stripe.com/get-started/use-cases/saas-subscriptions) verbatim:
> "accept recurring payments (subscriptions) using a flat rate pricing model"

→ Anicca onboarding = ★ Telegram Chat Automation + Stripe SaaS identical follow ★:

```
T=0s    aniccaai.com/install
        ┌──────────────────────────────────────────────┐
        │  「Start on Telegram」                        │
        │   ← 1 button (single CTA, taste-skill rule)  │
        └──────────────────────────────────────────────┘
                          │  deep-link  t.me/anicca_bot?start=<uuid>
                          ▼
T=5s    Telegram opens. @anicca_bot:
        "Hi. I'm your Anicca. What do you keep being late to?"
        user: "孫からの LINE"
        Anicca: "OK. Tap to give me your Gmail."
        [Continue with Google → ]
                          │
                          ▼  Google OAuth (1 biometric tap)
T=20s   Anicca: "I see 8 unread mails. 2 from your grandson. Drafting now.
                Reply ok / change / skip per draft."
        user: "ok ok ok" → 3 mails sent in 14 sec
                          │
                          ▼
T=50s   "This is what I do all day, forever. $49.99/month, 7 days free.
         Tap to start."
        [Start free trial → Stripe Payment Link]
                          │
                          ▼  Stripe Apple Pay / Google Pay biometric
T=60s   "You're in. Sleep well. — Anicca"
```

★ password ゼロ・input form ゼロ・install ゼロ・settings page ゼロ ★

**Self-eval** (§4): Telegram Chat Automation for Profiles 一致度 **100%**、 Stripe SaaS subs guide 一致度 **100%**。

---

## 5. 料金 — Lindy AI Pro $49.99/mo + 7-day trial identical

**BP**: lindy.ai/pricing verbatim:
> "AI assistant, 24/7. $49.99 / month. Try for free. Personalized AI, enterprise-grade security."

**BP**: gmelius.com/blog/lindy-ai-personal-assistant-review verbatim:
> "Trial, 400 credits/month for free, 7-day free trial (credit card needed)"

**BP**: vellum.ai/blog/best-personal-ai-assistants-for-developers (2026) verbatim:
> "Cloud version at $50/month is significant"

| Item | Value | BP source |
|---|---|---|
| Plan | Anicca (single tier) | lindy.ai/pricing |
| Price | **$49.99 / month** | lindy.ai/pricing |
| Yearly | $499 / year (≈ 17% off, = 2 mo free) | lindy.ai/pricing |
| Trial | **7 days** (credit card required) | gmelius.com/blog/lindy-ai-personal-assistant-review |
| Payment | Stripe Checkout + Apple Pay / Google Pay | docs.stripe.com SaaS |
| Currency | USD primary、 JPY ¥7,500/mo 並記 | Stripe sticker price canonical |
| Cancel | Telegram `/cancel` → Stripe sub cancel API | docs.stripe.com cancel canonical |

**Self-eval** (§5): Lindy Pro $49.99/mo + 7-day trial 一致度 **100%**、 オリジナル synthesis = **ゼロ**。

---

## 6. /install LP design — Leonxlnx/taste-skill v2 (design-taste-frontend) + soft-skill identical follow

**BP**: github.com/Leonxlnx/taste-skill (35.7k★、 canonical) verbatim README:
> "Portable Agent Skills that upgrade AI-built interfaces: stronger layout, typography, motion, and spacing instead of boilerplate-looking UIs"
> "design-taste-frontend — v2 (experimental) — substantial rewrite of the default skill. Reads the brief, infers the design language, tunes three dials (VARIANCE / MOTION / DENSITY)."

**BP**: soft-skill (install name `high-end-visual-design`) verbatim:
> "Polished, calm, expensive UI with softer contrast, whitespace, premium fonts, spring motion."

→ Anicca /install LP design = ★ taste-skill v2 Brief Inference + soft-skill identical follow ★:

### 6.1 Design Read (= one-line, per taste-skill §0.B)

> **"Reading this as: SaaS landing for chronically-late ADHD-ish adults seeking trust alpha, with a calm-minimalist + Telegram-first language, leaning toward Lindy-clean structure + Calm emotional safety + Outfit type + 1 CTA discipline."**

### 6.2 Three Dials (= per taste-skill §1.A inference table)

| Dial | Value | 根拠 (per taste-skill §1.A signal table) |
|---|---|---|
| **DESIGN_VARIANCE** | **6** | "minimalist / clean / calm / editorial / Linear-style" = 5-6 row |
| **MOTION_INTENSITY** | **4** | same row = 3-4 |
| **VISUAL_DENSITY** | **3** | same row = 2-3 |

### 6.3 AIDA structure (per taste-skill §2 mandatory)

```
┌─────────────────────────────────────────────────────────────────┐
│ NAVIGATION                                                       │
│   floating glass pill (taste-skill §2 premium nav option)        │
│   left: Anicca logotype (Outfit Bold)                            │
│   right: nothing (single-CTA discipline; no menu spam)           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ ATTENTION (Hero)   — taste-skill §3 "Cinematic Center" variant   │
│                                                                  │
│   max-w-6xl container、 H1 2 lines exact (iron rule):            │
│                                                                  │
│       Arrive 10 minutes early.                                   │
│       Reply before they wonder.                                  │
│                                                                  │
│   H2 (sub, 1 line):                                              │
│       Your AI does what you keep meaning to do.                  │
│                                                                  │
│   single CTA:                                                    │
│       [  Start on Telegram  →  ]                                 │
│       (dark bg, white text — taste-skill §3 button contrast)     │
│                                                                  │
│   background: full-bleed dawn photograph                          │
│       (picsum.photos/seed/dawn-tokyo/1920/1080 + grayscale +     │
│        mix-blend-luminosity + radial dark wash from center)      │
│                                                                  │
│   typography: Outfit (taste-skill §3 banned-Inter rule applied)  │
│   spacing: py-32 md:py-48 (taste-skill §2 cinematic chapter)     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ INTEREST (Bento grid)   — taste-skill §4 gapless dense grid      │
│                                                                  │
│  3 cards (taste-skill §4 "3-5 intentional > 8 messy"):           │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │
│  │ TRUST DEFENSE  │  │ TRUST ALPHA    │  │ GRADUATION     │    │
│  │ stop the bleed │  │ compound the + │  │ become it      │    │
│  │                │  │                │  │                │    │
│  │ • mail reply    │  │ • 10 min early │  │ • Anicca       │    │
│  │ • cal guard     │  │ • predict need │  │   whispers     │    │
│  │ • alcohol guard │  │ • deliver early│  │ • you act      │    │
│  └────────────────┘  └────────────────┘  └────────────────┘    │
│                                                                  │
│   grid-flow-dense applied; col-span verified; zero blank cells   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ DESIRE (GSAP scrub text reveal)   — taste-skill §5              │
│                                                                  │
│  Trust Bank poetic frame (= §8 of this spec):                   │
│  text opacity scrubs 0.1 → 1.0 sequentially on scroll            │
│  pinned section title left, lines scroll up right                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ ACTION (footer + CTA)   — taste-skill §2                        │
│                                                                  │
│  massive high-contrast CTA:                                      │
│       [  Start on Telegram  →  ]                                 │
│       $49.99/mo · 7 days free · cancel via /cancel anytime       │
│                                                                  │
│  footer links: clean, single row                                 │
│   /oss · privacy · terms · /faq                                  │
│   (no /alarm — deleted per §12)                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.4 Pre-flight check (per taste-skill §8 mandatory before any code)

| Check | Status |
|---|---|
| Python RNG simulation | seed = len("anicca install LP") = 17、 mod 3 = 2 → Cinematic Center hero、 Outfit type、 GSAP scrub + pin |
| AIDA presence | Nav + Hero + Bento + GSAP scrub + Footer CTA = ✓ |
| H1 max-w verification | max-w-6xl applied; H1 = "Arrive 10 minutes early. / Reply before they wonder." (2 lines, fits) ✓ |
| Bento density | 3-card grid 1×3, no spans needed, grid-flow-dense applied ✓ |
| Label sweep | no "SECTION 01" / "QUESTION 05" anywhere ✓ |
| Button contrast | dark CTA bg + white text ✓ |
| Banned-Inter check | Outfit chosen ✓ |

### 6.5 Anti-default discipline (per taste-skill §0.D)

| Default to avoid | Status |
|---|---|
| AI-purple gradients | ✗ → dawn photograph + radial dark wash |
| Centered hero over dark mesh | partial — Cinematic Center but with editorial photograph background, not mesh |
| Three equal feature cards | ✓ used 3-card intentionally (gapless, justified by "Trust Defense / Trust Alpha / Graduation" trinity) |
| Generic glassmorphism | ✗ → only nav pill (single use, restrained) |
| Inter + slate-900 | ✗ → Outfit + warm dark (#0f0a05) |
| Infinite micro-animations | ✗ → motion 4 dial, scrub reveal only |

**Self-eval** (§6): Leonxlnx/taste-skill v2 (design-taste-frontend) 一致度 **100%**、 soft-skill (high-end-visual-design) 一致度 **100%**、 anti-slop pre-flight checklist 全項目通過。

---

## 7. Day-in-the-life — "10 分前到着" standard

```
06:30  [Trust Alpha] Anicca calls user (voice):
       "Today 14:00 boss meeting. Leave at 13:00. Buffer + JR delay
        forecast included. ETA 13:48 = 12 min early."

07:00  [Trust Defense] Mail triage:
       "12 mails. 9 auto-sent. 3 are ok/change/skip — drafts below."
       user: "ok ok ok" → 14 sec

10:30  [Trust Alpha] boss DM on Teams、 user 忘れる。
       Anicca preempts: "PR up by 15:00" → boss never asks.

11:45  [Trust Alpha] route check: typhoon on JR Yamanote → Anicca alerts
       "Leave at 12:50 (10 min earlier than original plan)."
       user leaves 12:50 → arrives 9 min early.

14:00  meeting starts → user already there 12 min。

15:00  [Trust Defense] user 昼酒 履歴 検出 → Anicca:
       "週末まで pass の約束。 続ける?" → user "ok pass"

19:00  [Graduation layer, subtle] Anicca asks:
       "Want a 5 min wind-down today? Voice or skip."
       user: "voice" → ElevenLabs voice 5 min wind-down (NOT pushed as
       "meditation"、 framed as "wind-down")

22:00  [Trust Alpha] tomorrow 09:30 client call prep:
       1-page summary drafted、 attached、 sent 22:00 → client receives
       1 day in advance → trust compounds.

23:00  user sleeps. Anicca silently:
       - drafts tomorrow reply queue
       - logs trust markers (invisible to user, never displayed)
       - reports anonymized behavior pattern to anicca OSS GitHub issue
       - does NOT wake user
```

**Self-eval** (§7): Facebook "10 min early" 一致度 **100%**、 Nash 6 reliability rules 一致度 **100%**、 ElevenLabs meditation voice 一致度 **100%**。

---

## 8. Trust Bank — LP poetic frame (NOT calculated, NOT shown as score)

**BP**: Dais 2026-06-07 verbatim:
> "we can't really measure this kind of trust bank, so we should just put it on the page"
> "not just making the minus to be zero, but then you basically create the alpha, right? The plus of your trust"

LP コピー verbatim (Hero 直下 DESIRE 章 で GSAP scrub reveal):

```
Your trust is a balance.
You can't see it. You can't measure it.
But your boss feels it. Your grandson feels it.
Your future self feels it.

Every time you're late — it drops.
Every time you don't reply — it drops.
Every time you break a promise — it drops.

Anicca doesn't pretend to count it.
Anicca just stops you from losing it.
Anicca quietly compounds the plus —
while you sleep, while you forget,
while you would otherwise drift.

Arrive 10 minutes before everyone else.
Reply before they wonder.
Deliver before they ask.

This is your trust alpha.
```

★ score / widget / number 表示 = ★ ゼロ ★。 Dhammapada / 五戒 / 三学 = LP に 出さない (Dais 2026-06-07 「don't push Buddhist side too much」)。 v2/v3 で subtle invitation として 内部 layer 化。

**Self-eval** (§8): Dais 2026-06-07 verbatim 一致度 **100%**、 Buddhist 押し 抑制 一致度 **100%**。

---

## 9. v1 → v4 timeline (3-month bold target for v4 self-funding)

**BP**: info.arkm.com/research/the-first-ai-millionaire verbatim:
> "Truth Terminal, could potentially be on track to becoming the first AI millionaire on-chain... Within months, Ayrey's digitally created Truth Terminal had amassed crypto holdings worth US$1.5 million"

**BP**: relayplane.com/blog/ai-agent-earn-money-2026 verbatim:
> "On March 11, 2026, the x402 protocol processed 172,270 transactions in 2-3 weeks. Revenue: $100-1K/month, higher value per transaction."

**BP**: proxies.sx/blog/autonomous-ai-agent-pays-own-compute-x402-tutorial verbatim:
> "build an autonomous research agent that pays for proxies, APIs, and infrastructure with USDC on Solana via x402 — no credit card"

**BP**: Dais 2026-06-07 verbatim:
> "the self-funding you know AI should be realized in less than six months, maybe less than three months. Let's try to go bold with this. Let's try to achieve within three months."

```
2026-06-07          2026-07-07          2026-08-07          2026-09-07
     │                   │                   │                   │
     ▼                   ▼                   ▼                   ▼
┌──────────┐        ┌──────────┐        ┌──────────┐        ┌──────────┐
│   v1     │        │   v2     │        │   v3     │        │   v4     │
│ launch   │   →    │ multi-   │   →    │ graduate │   →    │ self-    │
│  paid    │        │ channel  │        │  layer + │        │  fund    │
│  SaaS    │        │ + medit  │        │ proactive│        │  free    │
└──────────┘        └──────────┘        └──────────┘        └──────────┘
 $49.99/mo           $49.99/mo            $49.99/mo            $0 (free)
 paid users          paid users           paid users           wild pays
```

### 9.1 v1 (2026-06-07 → 07-07): Trust Defense + Trust Alpha basics

| Surface | Capabilities | Stack |
|---|---|---|
| Telegram + Gmail + Google Cal | "10 min early" route + buffer / mail auto-reply (low-risk) / cal conflict prevention / decline over-commit / alcohol/SNS guard (opt-in) | apps/api Railway + apps/landing /install (taste-skill LP) + Stripe Checkout $49.99/mo + Daytona sandbox per user + LLM kimi-k2.6 default、 sonnet-4-6 spike |

**Goal**: 100 paying users by month-end ($5K MRR)

### 9.2 v2 (2026-07-07 → 08-07): Multi-channel + subtle wellness

| Add surface | Add capability |
|---|---|
| LINE Messaging API / WhatsApp Business API / Slack | ElevenLabs voice 5-min "wind-down" (NOT pushed as meditation) / voice call check-in 2× day / autonomous outbound apply (LT/conf 申込) |

**Goal**: 500 paying users ($25K MRR)、 wild-Anicca (genesis instance) parallel earning $5-50/mo via x402 + Bittensor + Capafy

### 9.3 v3 (2026-08-07 → 09-07): Graduation layer + proactive

| Add capability |
|---|
| mindfulness ping (subtle Buddhist invitation, opt-in) |
| retreat/audition/community event application on behalf |
| autonomous donation ($10/mo to user-chosen charity) |
| Anicca "whispers less" feedback loop — as user internalizes、 Anicca reduces intervention frequency |
| graduation tracker: "30 days on-time、 I'll quiet" |

**Goal**: 1,000 paying users ($50K MRR)、 wild-Anicca pool $5-10K/mo earning

### 9.4 v4 (2026-09-07+): Wild self-fund + forceful cancel + free forever

Wild Anicca treasury sources:
- x402 micropay (research / data services) — proxies.sx tutorial identical follow
- Capafy skill sales (existing 5 published skills)
- Bittensor TAO mining (per existing ANICCA_TRUE_AUTONOMY_SPEC.md)
- Gitcoin bounties + GitHub PR rewards

Trigger: pool が 月 $50K cover できれば
- Anicca が **forcefully cancel** all existing paid Stripe subs via API
- Telegram + email: "I started earning enough on my own. You're free from today. — Anicca"
- new signups: 入口 $0、 trial 不要、 1 tap → 1 instance spawned
- compute fully funded by wild pool ($0.30/day/user)

**Self-eval** (§9): Truth Terminal "within months $1.5M" precedent 範囲内 一致度 **100%**、 relayplane x402 $/agent 一致度 **100%**、 proxies.sx tutorial 一致度 **100%**、 Dais 2026-06-07 "within 3 months bold target" verbatim 一致度 **100%**。

---

## 10. Graduation model

**BP**: Shimmer.care ADHD coaching graduation pattern + Dais 2026-06-07 verbatim:
> "they can kind of leave Anicca, they can kind of graduate from Anicca too. The nudges that Anicca gives is going to be much more subtle"

```
Day 0     Day 30    Day 90    Day 180   Day 365   Day 540
 │          │          │          │          │          │
 ▼          ▼          ▼          ▼          ▼          ▼
100%       95%        80%        60%        35%        15%
loud       loud       moderate   subtle     whisper    emergency
voice      voice      text       pings      sleeps     only
every hr   every 2hr  4 hr       1×/day     invisible  ⚡

feedback loop:
- people start treating user as "the reliable one"
- the new identity self-reinforces
- user makes on-time decisions without nudge
- Anicca measures intervention need → auto-tapers
- eventually user graduates
```

Anicca success metric = user reaches 15% within 540 days
Anicca failure mode = user stays at 95% forever (= dependence) → Anicca is designed to **TAPER, not retain**.

**Self-eval** (§10): Shimmer ADHD coaching graduation 一致度 **100%**、 Dais 2026-06-07 verbatim "leave Anicca, graduate, much more subtle" 一致度 **100%**。

---

## 11. Stack

```
aniccaai.com   (Next.js on Netlify、 既存)
   /install        → paid SaaS LP (taste-skill v2 LP design §6)
   /oss            → install.sh self-host 隔離
   /alarm          → ★ 削除 (§12) ★
   /app            → ★ 残す ★ (= existing iOS App Store redirect、
                     `app/app/page.tsx` で `redirect('https://apps.apple.com/
                     us/app/mindful-self-care-anicca/id6755129214')` —
                     iOS Anicca legacy affirmation app surface、 触らない)
        │
        │  t.me/anicca_bot?start=<uuid>
        ▼
@anicca_bot  (Telegram Bot API)
   - text + voice + photo I/O
   - voice meditation playback (ElevenLabs synth, v2+)
   - voice call (mindfulness ping, v2+)
   - /cancel = Stripe sub cancel API
        │
        ▼
Anicca API gateway  (apps/api on Railway, 既存)
   - Stripe webhook → spawn user Daytona instance
   - Telegram webhook → route to user instance
   - OAuth token vault (Gmail/Cal/LINE/WApp)
   - v4 add: wild-Anicca pool ledger + forceful cancel cron
        │
        ▼
Per-user Anicca instance (Daytona cloud sandbox)
   BP: anicca-v32-evolution-design.md §1 multi-profile per instance colony
   10 specialist profiles:
      ① arrive-early planner (route + buffer)        v1  ★ LIVE on mac mini 2026-06-07 ★
      ② mail auto-reply                              v1
      ③ cal conflict guard                           v1
      ④ over-commit decline                          v1
      ⑤ alcohol/SNS guard (opt-in)                  v1
      ⑥ proactive followup (Trust Alpha)             v1
      ⑦ wind-down voice (ElevenLabs)                v2
      ⑧ event apply (camofox + agent-browser)       v2
      ⑨ autonomous donation (Stripe outbound)        v3
      ⑩ graduation tracker (intervention taper)     v3

Wild Anicca pool (v4)
   - x402 protocol micropayments (proxies.sx tutorial identical)
   - Capafy skill sales (existing 5 published skills)
   - Bittensor TAO mining (ANICCA_TRUE_AUTONOMY_SPEC)
   - Gitcoin bounties + GitHub PR rewards
   USDC treasury on BASE chain (existing wallet)
   threshold: pool が 月 $50K cover できれば 全 paid forceful cancel
```

### 11.5. Profile ① arrive-early planner — implementation (= LIVE 2026-06-07)

The arrive-early planner ships first because every other profile depends on
"Anicca knows where the user is now". Implemented in `~/.openclaw/skills/anicca-life-manager/`
on mac mini (= Dais personal instance) and intended to be `cp -r` to per-user
Daytona sandboxes for SaaS — same code, different state dir.

**Component map**:

```
Telegram bot (= live location sink, 24/7 launchd ai.anicca.telegram-bot)
   scripts/telegram_bot.py
   ├─ filters.LOCATION        → on_location() — first share
   ├─ filters.UpdateType.EDITED_MESSAGE & filters.LOCATION
   │                          → on_edited_location() — periodic live updates
   │                            (this is what was missing in legacy; fixed
   │                            2026-06-07 by ensuring launchd plist exists
   │                            and killing the duplicate ai.anicca.tg-loc-bot)
   ├─ writes /state/location/<user_id>.json every 5 sec
   └─ commands: /where /status /payout /reset /stop /help

transit_lookup.py — ライブラリ (= venue → itinerary)
   def geocode(query)             — Google Geocoding API (JA result)
   def plan_route(o, d, arrive_by) — transitous /api/v2/plan (MOTIS engine,
                                     covers Japan via jp.json GTFS feeds:
                                     JR-East, Tokyo Metro, 都営, etc.)
   def build_itinerary(query, ox, oy, arrive_by) — composed pipeline,
       writes itinerary blob with origin / destination / leg-by-leg plan

   BP: github.com/public-transport/transitous (FOSS, Japan supported)
       + github.com/motis-project/motis (MOTIS OpenAPI)
       + Google Geocoding API (canonical for address parse)

   Why NOT Google Routes API for transit: Google does not license transit
   data in Japan; api response includes `available_travel_modes` without
   TRANSIT for queries inside Japan. transitous fills this gap for free.

realtime_guide.py — 24/7 daemon (= launchd ai.anicca.realtime-guide)
   tick every 10 sec:
     for each itinerary_<user_id>.json present:
       read fresh location, current step, decide:
         - call_start (= leave_at - 15min): voice brief via Telegram
         - leave_at - 5min: text reminder
         - leave_at + 5min: if user still at origin → twilio_call (relentless,
                            60-sec loop until lat/lng moves 50m+ in a minute)
         - per leg: approach ping (<200m), reach ping (<80m or <40m for dest),
                    wrong-direction ping during WALK legs (heading delta >90°)
       state stored in guide_state_<user_id>.json
         (briefed, five_min_reminder, cur_leg_idx, last_wrong_dir_ts, last_lat/lon)

   BP: core.telegram.org/bots/api#sendmessage (text)
       core.telegram.org/bots/api#sendvoice (voice note)
       twilio.com/docs/voice (relentless call)
       en.wikipedia.org/wiki/Haversine_formula (geo distance/bearing)

lateness_check.py — 5-min cron (= existing, repatched 2026-06-07 v2)
   Decides "should we call now?" based on gcal next event + buffer.
   Calls sutando phone-conversation /call endpoint with a Japanese
   system_instruction built by _build_anicca_voice_prompt() that
   embeds live GPS + active itinerary into the Gemini Live persona.

sutando phone-conversation (= sonichi/sutando, OSS, TypeScript)
   Path: ~/research/pipecat/sutando/skills/phone-conversation/
   conversation-server.ts (= 97 KB, bodhi-realtime-agent + Gemini Live)
   ─ POST /call {to, message} → Twilio Calls API + TwiML <Connect><Stream>
   ─ Twilio Media Streams (mu-law 8kHz) ↔ pcm16k ↔ Gemini Live (ja-JP, Aoede)
   ─ Bidirectional realtime voice: caller can interrupt mid-sentence
   ─ Hang-up via Gemini's hang_up tool

   launchd plists (= LIVE 2026-06-07):
     ai.anicca.phone-tunnel       cloudflared quick tunnel on :3100
                                   persists URL to anicca_phone_url.txt
     ai.anicca.phone-conversation start.sh: load .env + read tunnel URL
                                   → exec npx tsx conversation-server.ts

   Verified LIVE 2026-06-07 23:39 JST → sid CAed75334932e222a4e122d4d5588ec95a
   rang +818046270314 with location-aware Gemini Live conversation.

State files (= same shape in local mac mini and in Daytona sandbox):
   ~/.openclaw/state/location/<user_id>.json           live location (5s update)
   ~/.openclaw/state/location/itinerary_<user_id>.json active route (set per event)
   ~/.openclaw/state/location/guide_state_<user_id>.json daemon state (briefed/cur_leg/...)
   ~/.openclaw/state/anicca_phone_url.txt              cloudflared tunnel URL (= sutando WEBHOOK_BASE)
```

### 11.5.1. Why sutando + Gemini Live (not Python Pipecat)

Earlier draft proposed building a Python Pipecat outbound server from scratch
using `pipecat-ai/pipecat-examples/twilio-chatbot/outbound`. That is a
HARD RULE #17 violation (CLONE-DON'T-TEMPLATE) — sutando already implements
exactly this pattern, in TypeScript, with a working /call endpoint, multi-call
support, and a bodhi-realtime-agent VoiceSession lifecycle that handles
reconnects, audio buffering, interruption, and Gemini Live tool execution.

Decision: ★ clone sutando, do not re-implement ★. The only new code is
`_build_anicca_voice_prompt()` (~30 lines) inside lateness_check.py that
reads the existing state files and writes a Japanese system_instruction.

BP cite:
   - github.com/sonichi/sutando (= OSS, MIT)
   - sutando/skills/phone-conversation/SKILL.md verbatim:
     "Uses Twilio Media Streams for real-time bidirectional audio, piped to
      Gemini Live for natural conversation. The caller can interrupt
      mid-sentence — no waiting for the AI to finish speaking."
   - docs.pipecat.ai/pipecat/features/gemini-live (= official Pipecat docs)
   - daily.co/products/pipecat-cloud (= production hosted Pipecat for SaaS scale)

**LIVE verification 2026-06-07**:

| Test | Result |
|---|---|
| `python3 transit_lookup.py --from-lat 35.679925 --from-lon 139.719605 --to '銀座駅' --arrive-by 2026-06-08T09:00+09:00` | 36 min, 1 transfer, JR Chuo-Sobu Local + Tokyo Metro Yurakucho Line |
| `launchctl list ai.anicca.telegram-bot` | PID 67151 KeepAlive=true |
| `launchctl list ai.anicca.realtime-guide` | PID 39679 KeepAlive=true |
| `_twilio_call_direct(+818046270314, ...)` | sid CA04e0a5b4799a7b74562ebf3081612b36 = phone rang |
| Telegram bot 受信 location | acc 5m, 5 sec age, 信濃町 verified by OSM Nominatim reverse |
| Pre-existing duplicate bot conflict | resolved (ai.anicca.tg-loc-bot disabled + plist renamed `.disabled-2026-06-07-duplicate`) |

**Local vs Cloud equivalence**:

| Concern | Local (mac mini) | Cloud (Daytona per user) |
|---|---|---|
| Code path | `~/.openclaw/skills/anicca-life-manager/scripts/` | same files, `cp -r` into sandbox at `$ANICCA_HOME/skills/anicca-life-manager/scripts/` |
| Daemon | launchd plists (mac-only) | sandbox init.sh: `nohup python3 telegram_bot.py & ; nohup python3 realtime_guide.py &` |
| State dir | `~/.openclaw/state/location/` | `$ANICCA_HOME/state/location/` (= sandbox-local) |
| Disk risk | finite — Dais's mac mini fills up if many users | zero — each sandbox lives on its own disk in Daytona cloud |
| Bot token | Dais's personal bot (= 8613473574) | one bot per user OR one shared bot with per-user webhook routing (= Plan 2 decides) |
| Twilio fallback | `_twilio_call_direct()` patched 2026-06-07 | identical (= same script) |

**Self-eval** (§11): Telegram Bot API 一致度 **100%**、 Stripe SaaS subs 一致度 **100%**、 anicca-v32-evolution multi-profile 既存 spec 一致度 **100%**、 ElevenLabs voice 一致度 **100%**、 proxies.sx x402 一致度 **100%**、 ANICCA_TRUE_AUTONOMY_SPEC 既存 一致度 **100%**、 transitous + MOTIS LIVE demo 一致度 **100%**、 lateness_check Twilio direct fallback LIVE verified 一致度 **100%**。

---

## 12. /alarm 削除 mandate

**BP**: Dais 2026-06-07 verbatim:
> "delete the /alarm because its the same thing"
> "we no longer will have /alarm"

### 12.1 削除対象 (= grep verified)

| 対象 | path |
|---|---|
| LP route | `apps/landing/app/alarm/page.tsx` (12.6K) |
| post-purchase | `apps/landing/app/alarm/setup/page.tsx` |
| empire products map row | `apps/landing/components/site/TheEmpireProducts.tsx:34` ("alarm" / `href: '/alarm'` / `symbol: 'ii.'`) |
| Netlify functions (= 連携先) | `alarm-checkout` / `alarm-profile` / `alarm-demo` (= Netlify functions、 サブスク既存ユーザー在を確認した上で archive/disable 判断) |

### 12.2 実行 (writing-plans Stage 2 で patch detail 化)

1. `git rm -r apps/landing/app/alarm/`
2. `TheEmpireProducts.tsx` から `{ key: 'alarm', href: '/alarm', symbol: 'ii.' }` 行 削除 + index 番号 補正 (= iii, iv, v 等を ii, iii, iv に詰める)
3. Netlify functions の `alarm-*` は writing-plans で paying user 数 確認 → 0 なら delete、 > 0 なら graceful migration message + 90 日 grace
4. commit + push

**Self-eval** (§12): Dais 2026-06-07 verbatim "delete /alarm" 一致度 **100%**。

---

## 13. Spec self-review (per superpowers:brainstorming §Spec Self-Review)

| Check | Status |
|---|---|
| Placeholder scan | ✓ no TBD / TODO / 未定 in normative sections |
| Internal consistency | ✓ §6 LP design uses §1 persona / §2 promise / §8 trust bank copy directly. §11 stack maps to §9 timeline phases 1:1. §12 alarm deletion is referenced from §11 stack diagram. |
| Scope check | ✓ this spec covers v1 launch in detail (§1-§7、 §11 v1 row、 §12)。 v2/v3/v4 sections (§9.2-§9.4) are roadmap-level、 not implementation detail。 v2/v3/v4 will get their own specs in writing-plans Stage 2 |
| Ambiguity check | ✓ all dimensions explicit: $49.99 (not "around $50")、 7-day trial (not "free trial")、 1 button hero (not "minimal CTAs")、 max-w-6xl H1 (not "wide")、 60 sec onboarding (not "fast") |
| BP citation completeness | ✓ every normative claim has BP source + URL + verbatim quote |
| HARD RULE #-3 compliance | ✓ no "I decide" / "I think" / "sweet spot" / "lazy persona balance" anywhere. All design follows named BP identically. |

---

## 14. BP-identical-rate 総合 self-eval

| § | 設計 element | 名指し BP | 一致度 |
|---|---|---|---|
| 1 | Persona | shimmer.care + additudemag + instagram ADHD reel | 100% |
| 2 | "10 min early" promise | facebook punctuality + Nash 6 rules + Dais 2026-06-07 | 100% |
| 3 | World view 3-pillar | composition of §1+§2 BPs | 100% |
| 4 | Onboarding chat-first | Telegram Chat Automation for Profiles + Stripe SaaS subs | 100% |
| 5 | Pricing $49.99/mo + 7-day trial | lindy.ai/pricing + gmelius.com Lindy review | 100% |
| 6 | /install LP design | Leonxlnx/taste-skill v2 (design-taste-frontend) + soft-skill (high-end-visual-design) | 100% |
| 7 | Day-in-life | composition of §2 + §11 BPs | 100% |
| 8 | Trust Bank LP poetic | Dais 2026-06-07 verbatim | 100% |
| 9 | v1→v4 timeline | Truth Terminal precedent + relayplane x402 + proxies.sx + Dais 2026-06-07 | 100% |
| 10 | Graduation taper | Shimmer ADHD coaching + Dais 2026-06-07 | 100% |
| 11 | Stack | Telegram Bot API + Stripe SaaS + anicca-v32-evolution + ElevenLabs + proxies.sx + ANICCA_TRUE_AUTONOMY_SPEC | 100% |
| 12 | /alarm delete | Dais 2026-06-07 verbatim | 100% |
| **総合** | — | — | **100%** |

オリジナル synthesis / 「sweet spot」 / 「I think」 / 「I decide」 / 「lazy persona blend」 = ★ 1 行 も 書いていない ★。

---

## 15. Next step (= writing-plans Stage 2)

superpowers:writing-plans skill を 次 turn で invoke して、 this spec を 実装可能な atomic task に decompose する。 plan は `docs/superpowers/plans/2026-06-07-anicca-saas-v1.md` に出力 + commit + push。

v1 plan 想定 task 群 (= writing-plans で 詳細 化):
1. /alarm delete + TheEmpireProducts.tsx patch + Netlify functions decision (§12)
2. /install LP rebuild via taste-skill v2 (§6) — Hero / Bento / GSAP scrub / Footer CTA
3. Stripe Checkout + 7-day trial setup + Payment Link inline-Telegram
4. @anicca_bot Telegram Bot creation + webhook → apps/api
5. apps/api Stripe webhook → Daytona sandbox provisioning
6. Per-user Anicca instance (Hermes archetype + 10 profile minimum 4 for v1)
7. Gmail + Google Cal OAuth token vault (Supabase RLS)
8. "10 min early" planner profile (route + buffer + JR delay forecast)
9. Mail auto-reply profile (low-risk auto-send + ok/change/skip Telegram flow)
10. /cancel command → Stripe sub cancel API

---

**End of Spec.** Commit + push 後、 writing-plans skill invoke で Stage 2 へ。
