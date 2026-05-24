---
name: publish-to-oss
description: "One-way private→public publisher (copybara-style). Copies general skills from $ANICCA_HOME into staging, scrubs every personal value (data-driven from profile.json), runs a 3-tool gate (gitleaks + trufflehog + residual personal grep), and only pushes to the public OSS repo if 100% clean. Git histories are never connected."
metadata:
  tags: oss, publish, security, scrub, gitleaks, trufflehog, copybara, 12-factor
  requires:
    bins: [bash, python3, rsync, git, gitleaks, trufflehog]
    env: [ANICCA_HOME, ANICCA_OSS_DIR]
---

# publish-to-oss

The safe one-way bridge from the private live runtime (`$ANICCA_HOME`, secrets +
personal data) to the public OSS repo. Encodes the lesson from 2026-05-24:
automated secret scanners (gitleaks/trufflehog) pass while **personal** data
(revenue, names, school, handles, IPs) still leaks — so the gate adds a
data-driven scrub + a residual personal-value grep.

## Why this exists
- **Blacklist whack-a-mole misses things** (proved 3× in one session).
- **Data-driven scrub**: reads the owner's real values from `identity/profile.json`
  and replaces them wherever they appear — not a hand-maintained blacklist.
- **Histories never connect**: staging is a fresh tree. The private repo's
  poisoned history (committed keys) can never reach the public repo.

## Run
```bash
export ANICCA_HOME=~/.openclaw ANICCA_OSS_DIR=~/anicca-oss
bash $ANICCA_HOME/skills/publish-to-oss/scripts/publish.sh          # dry-run: {{profile.lateness.stakeholders.senderType}}+scrub+GATE (no push)
bash $ANICCA_HOME/skills/publish-to-oss/scripts/publish.sh --push   # push ONLY if gate passes
```

## Pipeline
```
$ANICCA_HOME ──rsync(whitelist paths + excludes)──▶ /tmp/anicca-oss-publish
   exclude: .env, agents/(auth,sessions), profile.json, cron/jobs.json,
            skills/_private, skills/_vendor, skills/*/data|reports|state, media
   ──scrub.py (profile-driven + static IP/handle/school patterns)──▶ placeholders
   ──GATE: gitleaks + trufflehog(verified) + residual personal grep ──▶ all 0?
       FAIL → abort, leave staging for inspection (NO push)
       PASS → rsync → $ANICCA_OSS_DIR → git commit + push (only with --push)
```

## Contract
- `scripts/scrub.py` — data-driven scrub. Personal values come from
  `identity/profile.json` leaves ({{profile.lateness.stakeholders.senderType}}Name, {{profile.lateness.stakeholders.channel}}s, phone, address, lat/lon,
  advisor {{profile.lateness.stakeholders.channel}}…) + a static map (Tailnet IPs, <your-school>, naist username, social
  handles, repo owner handle). Min length 5 to avoid nuking common words.
- `scripts/publish.sh` — orchestrator. Default = dry-run gate. `--push` publishes.
- Skills are NOT excluded wholesale — they all ship, generalized. Only secrets,
  auth, sessions, real profile, runtime configs, and per-skill data/ are excluded.

Source pattern: Google Copybara (internal→public one-way with transforms).
Lesson encoded: opensource.guide "no sensitive materials in revision history".
See memory: feedback_never_push_openclaw_to_public_oss, reference_oss_secure_publish_recipe.
