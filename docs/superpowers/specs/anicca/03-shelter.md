# 03 — Shelter (home)
Goal: where the body runs. **Default fast paths only** (no 15-min crypto):
  - local: the user's own machine (free, instant) — OSS default.
  - cloud: **DigitalOcean droplet via API key** (~1 min). App: WE hold key/pay. OSS-cloud: user pastes own key.
  - Conway: FUTURE (locked) — README note; when live, agent self-pays + replicates.
  - Akash crypto self-pay: optional "sovereign mode" footnote (proven, but NOT default).
Files: skills/shelter/local.mjs, skills/shelter/do-droplet.mjs (DO API → create droplet, cloud-init runs birth.sh), skills/shelter/akash/* (optional).
Acceptance: with a DO token, `node skills/shelter/do-droplet.mjs` returns a running droplet IP in ≤2 min with Anicca booting on it.
