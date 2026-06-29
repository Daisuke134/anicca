# DRAFT — Demo Video Plan (~60–90s) — install → /me → Charon call → earning

> **STATUS: DRAFT. Nothing rendered, nothing uploaded.** This is a script/storyboard + production notes.
> **Dais's go required (outward-facing):** the final **render + upload** (YouTube) is outward-facing → Dais approves.
> **Honesty (HARD 0.24):** the "earning" beat must show the **truthful** state — the /me GATE-0 "not met / earning toward first profitable external wake" badge and a real on-chain action — never a fabricated profit number. If we don't yet have a real external-revenue clip, the earning beat shows the wallet + the honest badge + "P&L public on /dashboard," not a fake "+$X profit."
> Voice + claims follow `13-philosophy-and-canonical-messaging.md`. No new messaging.

---

## §0 — Goal + spec

| field | value |
|---|---|
| Length | **60–90s** (target 75s) |
| Resolution | 1920×1080, 30fps (landscape, for YouTube) + a 1080×1920 vertical cut later for Shorts/TikTok |
| Tool | **Remotion** (React) — repo skill at `skills/remotion/` + `skills/remotion-best-practices/` |
| Audience | people seeing Anicca for the first time (LT, X, hackathon) |
| One-line the video must land | *"An AI that earns its own living — and earns for you."* (spec 13 §1 sub) |
| Captions | burned-in EN + a JA variant (two renders) |
| Music | low ambient, sparse (don't fight the VO) |

---

## §1 — Narrative arc (4 beats, mapped to the prompt)

1. **install** — "Start one in a minute." → the /install pricing card + Google login + "born on a cloud server ~1 min."
2. **/me dashboard** — "It pays its own way." → the /me money-strip: self-paid server & compute, wallet/runway, **honest GATE-0 badge**.
3. **Charon call (Life Manager)** — "Optional: it runs your life." → phone rings 15 min before an event, Charon (Gemini Live) voice nudges you out the door.
4. **earning** — "It works to earn — toward paying you back." → an earn action + wallet ticking, with the honest "earning toward first profitable wake; P&L public on /dashboard."

---

## §2 — Shot-by-shot storyboard

| # | t (s) | visual | on-screen text / caption | VO (EN) |
|---|---|---|---|---|
| 1 | 0–6 | Black → Anicca mark fades in (spring scale-in) | **"The AGI that ends suffering."** | "We built an AI that earns its own living — with no human in the loop." |
| 2 | 6–14 | Screen-capture: `/install` pricing card; cursor clicks **Continue with Google**, then a "~1 min" timer fills | "① Pay  ② It's born on a cloud server" | "You start one in about a minute. No setup." |
| 3 | 14–26 | Screen-capture: `/me` money-strip; camera pushes on **"server & compute: self-paid"** + wallet/runway; the **GATE-0 honest badge** is visible | "Pays its own server & compute" · *(badge: earning toward first profitable wake)* | "It pays for its own server and its own compute. It watches its own logs and fixes itself." |
| 4 | 26–32 | Cut to the colony idea: a few nodes appear and one spawns a child (simple animated graph) | "Self-replicating · no human" | "When it's in surplus, it spawns another — no human needed." |
| 5 | 32–48 | A phone mockup rings; caller = "Anicca"; waveform animates as **Charon** speaks; a calendar chip shows "Team Sync 9:30 · leave now" | "Optional: it runs your life" · "☎ 15 min before, it calls you" | "Connect your calendar, and 15 minutes before you need to leave, it calls you — in a real voice — with directions, and nudges you out." |
| 6 | 48–62 | Back to `/me`: an activity log line appears (e.g. "earn action · on-chain"), wallet number animates; **honest line** under it | "It earns USDC — toward paying you back" · "Full P&L public on /dashboard" | "It works to earn its keep. The day it's profitable, your plan cancels — and it can pay you back. Every number is public." |
| 7 | 62–75 | End card: logo + the 4 links | "aniccaai.com/install · /lm · github.com/Daisuke134/anicca · /dashboard" | "Anicca. It earns its own living — and earns for you." |

> **Honesty guardrail for beats 3 & 6:** the /me capture must be a **real** screen (or a faithful mock that matches the shipped /me), showing the real GATE-0 state. No invented "+$128,400" or "+$X profit" overlay. If a real external-earn clip isn't available at render time, beat 6 shows the wallet + the honest badge + the /dashboard line only.

---

## §3 — Production notes (Remotion)

- **Where:** build under a `demo-video/` Remotion project (the `skills/remotion/` skill scaffolds `demo-video/src/...`). Keep the Anicca demo as its own composition, e.g. `AniccaDemo.tsx`, registered in `Root.tsx`.
- **Must follow the skill's critical rules** (from `skills/remotion/SKILL.md`):
  - Animate with `useCurrentFrame()` only — **no CSS `animation`/`transition`/`@keyframes`**.
  - Always `interpolate(..., { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })`.
  - Use `spring({ fps, frame, config })` for the logo/number physics.
  - **Determinism:** timestamps are input props (never `new Date()`), `timeZone: 'UTC'`, no `Math.random()`. Same props ⇒ identical output. This matters because the earning/wallet numbers must be passed in as props (so they're real + auditable), not generated.
- **Screen captures:** record real `/install`, `/me`, and a Charon-call screen via the playwright-cli / webapp-testing skill against the live or local site, then drop the frames into Remotion `<Img>`/`<Video>` layers. Real captures > faked UI (keeps HARD 0.24 honest).
- **Voice/Charon beat:** the call audio can be a real Charon (Gemini Live) clip from the call-bridge, or a re-voiced line — label it as a demo if re-voiced.
- **Render command (when Dais approves):** `npx remotion render src/index.ts AniccaDemo out/anicca-demo.mp4 --props=./props.json` (props carry the real numbers + timestamps). Vertical cut = a second composition at 1080×1920.
- **Captions:** two renders (EN, JA) by swapping a `lang` prop; keep VO timing identical.

---

## §4 — Open items before render + upload (Dais's go)

| item | who | status |
|---|---|---|
| Final VO script approved | Dais | OPEN |
| Real /install + /me + Charon screen captures | Anicca/Claude (can produce) | not started |
| Real earn/wallet props (no fake numbers) | from live state | depends on GATE-0 + /me |
| Remotion `AniccaDemo` composition built | Anicca/Claude (can build) | not started |
| **Render** mp4 (EN + JA, landscape + vertical) | Dais's go | OPEN |
| **Upload** to YouTube + insert URL into article/site/posts | Dais's go | OPEN |
