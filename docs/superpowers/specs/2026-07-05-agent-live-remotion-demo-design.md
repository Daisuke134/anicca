# Spec: Remotion demo video of the live `/agent?id=anicca-a3cdd4` page

Date: 2026-07-05
Status: approved (Dais verbal request, transcribed/garbled voice memo)

## Context

Dais asked (voice-to-text, garbled) for a demo video, **using the Remotion skill** (explicitly:
"we use remotion skills" — not HyperFrames), of `https://aniccaai.com/agent?id=anicca-a3cdd4`. That
page (`apps/landing/app/[id]/AgentClient.tsx`) is a live per-instance dashboard: it polls
`/.netlify/functions/dashboard-sync` every 4s and shows net worth, revenue today/this month, a
per-source revenue breakdown, and a scrolling "live activity" ledger. Dais's complaint: the page
itself barely *feels* alive on a static screenshot — he wants a **moving** (Remotion, frame-based)
video that visually proves the feature: an AI agent with its own wallet, earning with **zero humans
in the loop**, updating in real time.

There is a prior, in-repo precedent: `videos/vineyard-remotion/` (a small Remotion project, id
`VineyardDemo`, 5 generic scenes — title / wallet-spawn / engines / counter / close — already
rendered once to `out/vineyard-demo.mp4`). That project was **never git-committed** and disappeared
from disk mid-session (disk was at 4.1GB free; some background hygiene process likely swept it as
scratch output). A full backup survived at `~/vineyard-demo-assets/` (package.json + src/*.tsx +
the rendered mp4). **Lesson applied in this spec: the recreated project MUST be git-tracked and
pushed immediately** — untracked build output is exactly what HARD RULE 0.00 exists to prevent.

`anicca-a3cdd4` is this Claude instance's own earn wallet (`0xa3CDd4Ec...`, see `docs/WALLETS.md` /
memory `reference_anicca_wallets_canonical`). Live data fetched 2026-07-05 from the production
endpoint (frozen below for determinism — Remotion composition props must be deterministic, no
`Date.now()` / live fetch inside the composition):

```json
{
  "host": "anicca-a3cdd4",
  "geo": "JP",
  "model_live": "free/glm-4.7",
  "net_worth_usd": 1.2053946313910322,
  "daily_revenue_usd": -0.099667,
  "monthly_revenue_usd": -0.109916,
  "status": "alive",
  "revenue_by_source": { "hl": 0.0492, "aave": -0.00478, "fluid": 0.000998, "morpho": 0.001546, "bluechip": -0.389909, "hl-trade": 0.2311, "moonwell": 0.001929 },
  "log_slots_recent": ["earn/clip","earn/clip","loop_detect","hl_trade","earn/clip-producer","earn/clip","earn/clip-producer","earn/clip-producer","hl_trade","hl_trade","yield","earn/polymarket-trade","earn/video","earn/bounty","skill_error(earn/sol-trade)","earn/clip-producer","earn/clip","cook","x402_sell","yield"]
}
```

Numbers are honest (small net negative today — that's the real state), not invented. Per project
HARD RULE 0.24 (no fake data) this is presented as a real, frozen snapshot with an on-screen
timestamp caption, not implied to be "live" inside the rendered file (the real live-ness is the
*website*; the video *dramatizes* that website).

## Goal (provable finish line)

`done = "out/agent-live-demo.mp4" exists, plays back a rendered composition that visually recreates
the AgentClient page (status dot, net worth counter, revenue cells, streaming activity log) with
frame-based motion (spring/interpolate, no CSS transitions), is git-committed + pushed to
Daisuke134/anicca-products, AND 3 extracted frames (start/mid/end) show the expected on-screen text
when read back.`

## Scope — files touched

- `videos/vineyard-remotion/` — recreated (was deleted mid-session); restored from
  `~/vineyard-demo-assets/` backup (`package.json`, `src/index.ts`, `src/Root.tsx`,
  `src/VineyardDemo.tsx` unchanged) **and this time added to git**.
- `videos/vineyard-remotion/src/AgentLiveDemo.tsx` — **new** composition, follows the exact
  patterns already established in `VineyardDemo.tsx` (the `FadeUp` helper, `spring()` for
  pops/pulses, `interpolate()` with `extrapolateLeft/Right: "clamp"`, no CSS `transition`/`animation`,
  1920x1080 @ 30fps) — per the `remotion` skill's Critical Rules.
- `videos/vineyard-remotion/src/Root.tsx` — register a second `<Composition id="AgentLiveDemo">`
  alongside the existing `VineyardDemo` (existing composition untouched).
- `videos/vineyard-remotion/out/agent-live-demo.mp4` — rendered output (git-committed; it's ~1-3MB,
  same order of magnitude as the existing 1.5MB vineyard-demo.mp4).

## Composition design (AgentLiveDemo, ~12s @ 30fps = ~360 frames)

Recreates `AgentClient.tsx`'s visual language (light background `#fdfefe`/off-white per app theme,
gold accent for net worth, green/red for signed revenue, monospace for numbers/log) but as discrete
Remotion `<Sequence>` scenes:

1. **Scene Header (0-60f / 2s)**: URL bar chrome text `aniccaai.com/agent?id=anicca-a3cdd4`, status
   dot fades in and pulses green (`spring`), host name `anicca-a3cdd4` fades up.
2. **Scene Net Worth (60-150f / 3s)**: "Net worth" label fades in, `$1.21` counts up from `$0.00`
   via `interpolate(frame, [0, N], [0, 1.2053946313910322])` (linear, clamped) — same counter
   technique as `SceneCounter` in `VineyardDemo.tsx`.
3. **Scene Revenue Cells (150-210f / 2s)**: the 2-cell grid (Revenue today `−$0.0997` red, Revenue
   this month `−$0.1099` red) fades/slides in, matching `Cell` component's color logic (green
   positive / red negative).
4. **Scene Revenue By Source (210-270f / 2s)**: 3-4 of the source cells staggered in (hl +$0.0492,
   hl-trade +$0.2311, morpho +$0.0015, moonwell +$0.0019) — staggered `FadeUp` per the existing
   staggered-animation pattern in the `remotion` skill's Common Patterns.
5. **Scene Live Log (270-330f / 2s)**: activity log lines type/stream in one at a time (staggered
   opacity+slide, ~4-6 of the real `log_slots_recent` entries e.g. `wake · earn/clip-producer`,
   `wake · hl_trade`, `wake · yield`) — visually proves "it's still working, unattended."
6. **Scene Close (330-360f / 1s)**: `spring`-scaled tagline card: **"Zero humans in the loop."** /
   `aniccaai.com/agent?id=anicca-a3cdd4`.

No narration required (this is a short unnarrated motion graphic per the `remotion`/HyperFrames
"motion-graphics" genre — Dais's ask was about *movement*, not voiceover). Silent MP4 is the DoD;
if Dais later asks for VO this spec gets amended.

## Verification (HARD RULE 0.31 — E2E, not just "commit + push")

1. `npx remotion render src/index.ts AgentLiveDemo out/agent-live-demo.mp4` completes exit 0.
2. `ffprobe` confirms duration ≈ 12s, resolution 1920x1080, video stream present.
3. Extract 3 frames (`ffmpeg -ss 1 / -ss 6 / -ss 11`) → visually/OCR-plausibly confirm expected text
   present at each timestamp (header at 1s, net-worth counter mid-count around frame ~90-100 i.e.
   ~3-3.3s, close tagline near 11s).
4. `git add videos/vineyard-remotion && git commit && git push` — confirm `git log` shows the new
   commit on `origin/<current-branch>` (not left uncommitted, unlike the vanished first attempt).
5. Report MD5 of the final mp4 + frame timestamps in the completion message (no "patch applied,
   trust me" — fresh evidence only).

## Non-goals

- Not touching the real `AgentClient.tsx` page (no code changes to the live site).
- Not wiring this into any cron/auto-publish pipeline — this is a one-off demo video render, per
  Dais's ask ("can we make a ... demo video"). If he wants it posted somewhere (X, dashboard embed),
  that's a follow-up decision, out of scope here.
- Not attempting HyperFrames — Dais explicitly said "we use remotion skills" mid-conversation,
  overriding the initially-considered HyperFrames `website-to-video` route.
