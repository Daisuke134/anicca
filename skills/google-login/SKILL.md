---
name: google-login
description: Authenticate an authorized seller-owned Google or Gmail identity, read Gmail verification messages, or complete OAuth/device login without exposing secrets; use for Google sign-in, Gmail receive-otp, login challenges, and expired sessions.
---

# Google Login

Use this procedure only for an account already authorized by the current `JobContract` or exact-cycle
account-owner policy. It permits ordinary login and verification; it does not permit account recovery,
password reset, security-setting changes, logout, KYC, spending, or another person's identity.

## Identity and secrets

1. Resolve the account with `skills/_shared/resource_resolver.py` and the private SSOT
   `~/.local/share/anicca/credentials.json`. Read only the selected credential reference at runtime.
2. Never print, log, echo, hardcode, place in shell arguments, or copy into prompts/evidence any password,
   token, OTP, recovery code, or device code. Inject secrets only through an available UI-safe mechanism.
3. Prefer an already authenticated browser identity. Verify the exact account identity in official Google
   or Gmail DOM before reading mail or using it for another service.

## Ordinary sign-in

Run browser work through `skills/browser/with-browser.sh` or an exact self-owned default-context tab.
Do not navigate or close another owner's tab.

1. Open the normal Google sign-in form and select the authorized seller-owned identity.
2. If a native passkey sheet appears before password entry, cancel it once and choose the ordinary password
   option. Enter the SSOT password without exposing it.
3. If Google accepts the password and then shows a passkey challenge, choose `Try another way` exactly once.
   Select Google Prompt or Gmail-app confirmation when offered. Do not recursively try alternatives.
4. A required phone/app approval is `NEEDS_OWNER_CEREMONY`: preserve the exact pending login checkpoint and
   wait for that approval. Never treat the waiting screen as authenticated and never restart the login while
   the same challenge is pending.
5. Stop immediately on recovery, password reset, alternate recovery email, account lock, or waiting-period
   screens. Record the exact non-secret screen state; do not broaden authorization.

## Gmail verification

After official DOM proves the correct Gmail identity, read only the message needed for the current authorized
signup or OAuth continuation. Bind the sender, recipient identity, subject, received time, and target service
to the project checkpoint. Enter an OTP once in the matching live challenge; never reuse it or expose it.

## Completion

Login is complete only when official Google/Gmail DOM shows the authorized identity as authenticated. A
downstream signup is complete only after that provider's official account readback. Keep login, provider
signup, and later marketplace submission as separate checkpointed effects.
