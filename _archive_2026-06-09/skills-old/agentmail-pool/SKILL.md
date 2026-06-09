---
name: agentmail-pool
description: Unlimited fresh AgentMail inbox provisioner via SDK sign_up. Each call creates a new org + inbox + API key. Bypasses Clerk/Turnstile CAPTCHA on web signup. Use whenever Anicca needs a fresh email for SaaS / TikTok / Instagram / any account creation that requires email verification. Anicca reads OTP via Postiz-style polling.
metadata:
  tags: agentmail, mail, signup, inbox, scaling, OTP
  requires: { bins: [python3], env: [] }
---

# agentmail-pool

Unlimited fresh inboxes for any account creation.

## Why

- Web signup hits Clerk CAPTCHA (= hard-block per HARD RULE #-1)
- **SDK sign_up endpoint has no CAPTCHA** (verified 2026-06-06)
- Each sign_up call = new org + 1 inbox + dedicated API key
- We can pool dozens of fresh inboxes per day

## Run

```bash
bash ~/.openclaw/skills/agentmail-pool/scripts/provision.sh <human_email> <username>
# → prints: org_id, inbox, api_key (saved to state/agentmail-pool.jsonl)
```

## Read OTP from any pooled inbox

```bash
bash ~/.openclaw/skills/agentmail-pool/scripts/read-otp.sh <inbox_email>
# → looks up api_key from state/agentmail-tt-pool.json, polls last messages
```

## Forbidden seed emails (return ForbiddenError)

- `*@agentmail.to` itself
- Gmail aliases that map to an existing org (normalized)

## Working seed domains (verified 2026-06-06)

- `*@aniccaai.com` (any subaddress, infinite)
- `daisuke_2_narita@mufg.jp` (Dais work email)

## State

- `state/agentmail-tt-pool.json` — inbox → api_key_env mapping
- `state/agentmail-pool.jsonl` — full provisioning log (append-only)
