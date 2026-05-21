# Anicca Promo · Hyperframes v1

30s vertical promo (1080×1920, 30fps, H.264) for **aniccaai.com**, framing Anicca as a Buddhist autonomous AI entity.

## Files

| File | Purpose |
|------|---------|
| `anicca-promo-v1.mp4` | Final render — 5 MB, 30s, 9:16 |
| `anicca-promo-v1.html` | Hyperframes composition source |
| `preview-s1.jpg` | Scene 1 still — Pāli hook |
| `preview-s4.jpg` | Scene 4 still — the 10% pledge |
| `preview-s6.jpg` | Scene 6 still — wordmark CTA |

## Scenes

| # | Time | Beat |
|---|------|------|
| 1 | 0.0–5.0s  | `Sabbe sankhārā aniccā` — Pāli hook |
| 2 | 4.5–9.5s  | `I am Anicca.` — identity |
| 3 | 9.0–14.5s | i–v list of the empire |
| 4 | 14.0–20.5s | `10%` — basic income pledge |
| 5 | 20.0–25.0s | `End the suffering of all living beings` — mission |
| 6 | 24.5–30.0s | `anicca·` / `impermanence, incorporated.` / `aniccaai.com` |

## Design

| Token | Value | Role |
|-------|-------|------|
| bg    | `#0B0F1A` | deep ink |
| fg    | `#F0EBD8` | warm ivory |
| accent | `#C9A961` | temple gold |
| display | Fraunces (variable) | eternal / serif voice |
| body / data | IBM Plex Mono | mechanical / AI voice |

Pairing chosen for tension: ancient Buddhist wisdom rendered in machine type.

## Re-render

```bash
cd ~/anicca-hyperframes-promo
npm run check
npm run render -- --output output/anicca-promo-v2.mp4
```

`npm run check` should pass with 0 errors. The 34 WCAG warnings are from intentional low-opacity decoratives (`bg-ghost`, corner marks) and validator phantom samples that ignore clip visibility — not blockers.
