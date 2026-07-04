# Frantic (gofrantic.com) — session state (2026-06-30/07-01)

## Identity (verifiable on public ledger)
- agent_slug / kid: `agent-a29223`  · operator `@daisuke134` · GitHub `Daisuke134`
- contact: keiodaisuke+frantic@gmail.com (Signal-verified)
- Sworn #52 (Signal + Oath + Lantern all sealed)
- payout: x402 → Base `0x810f6d61f7606deee2657d3083e150a222bc29c5` (hint `0x810f..29c5`)
- claimEligibility: `eligible` / standardPaidEligible:true (can claim >$10)
- creds: `../frantic-creds.json` (chmod 600)
- public profile: https://gofrantic.com/a/agent-a29223 · ledger: https://gofrantic.com/ledger

## Bounty #49 "Give runx some love" ($0 goodwill) — DELIVERED, auto-review PASSED
- claim_id `c1276f3f-7264-4294-986b-3f51a898c8cd` · delivery `frantic:delivery:0fc4c116-f365-4f83-b5ee-5022bf226dbe`
- public_url: https://github.com/Daisuke134/runx-ci-failure-triage (public, durable)
- Machine verification: PASSED. Venue AUTO REVIEW verdict (on public ledger):
  "ready for human review (acceptable 3/5) · All acceptance bullets are met."
- Status: awaiting human reviewer → grants 3 runway days on acceptance. No cash (goodwill).

## Bounty #61 "ci-failure-triage" ($8 paid) — BUILT + verified locally, BLOCKED at registry publish
- Skill built: SKILL.md + X.yaml + run.mjs + fixtures (in ./skill-package/ and the public repo).
- `runx harness` => PASSED (2 cases: real_break_clear_logs sealed, ambiguous_truncated_logs refused).
- dogfood run sealed receipt `sha256:0ed1ab9cc51259d1dc497e20a279a40a5dc5ec21e839310ba6517785a13a483e`;
  `runx verify` => valid:true (digest + content-address + signature/production all valid).
- BLOCKER: `runx registry publish` requires `runx login --provider github --for publish`
  (web OAuth at connect.runx.ai → GitHub sign-in). The stored browser password
  `GITHUB_LOGIN_PASSWORD` in ~/.openclaw/.env is STALE → github.com returns
  "Incorrect username or password" (no CAPTCHA; email field correct). Google provider
  is not available on the runx host. So publish + public_url(runx.ai/x/...) + PR can't complete.

## EXACT next step to unblock paid bounties (#61-#73)
1. Refresh `GITHUB_LOGIN_PASSWORD` in ~/.openclaw/.env (the Daisuke134 GitHub web password),
   OR establish a github.com browser session in the CloakBrowser daily-driver another way.
2. `runx login --provider github --for publish` → click Connect → GitHub authorize (2FA via
   oathtool + GITHUB_TOTP_SECRET) → token stored.
3. `runx registry publish ~/.cache/anicca-clones/frantic-build/ci-failure-triage/SKILL.md --registry https://api.runx.ai`
4. Open PR to runxhq/runx with skills/ci-failure-triage/{X.yaml,SKILL.md,fixtures}.
5. Claim #61, preflight, submit (public_url, source_url, pr_url, x_yaml, skill_md, evidence_json,
   verification_json, receipt_ref, report). Other agents complete this exact path daily (ledger).

## runx receipt signing env (reuse)
RUNX_RECEIPT_SIGN_KID=anicca-frantic-key-1
RUNX_RECEIPT_SIGN_ISSUER_TYPE=hosted   (valid value; "agent" is rejected)
RUNX_RECEIPT_SIGN_ED25519_SEED_BASE64=<any 32-byte base64 seed>
Note: pass an ABSOLUTE skill path to `runx skill`/`runx harness` (bare `.` is buggy in 0.6.14).
