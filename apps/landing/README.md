# apps/landing — Life Manager web surface (scoped subset)

This directory contains ONLY the Life Manager web-tier files migrated from
`Daisuke134/anicca-products:apps/landing/` during 8i REPO-CONSOLIDATE.

The source `apps/landing` is a 397-file shared marketing site hosting many
unrelated products (retreat, fashion, income/UBI, spawn/cloud, cafe, x402).
Per the 8i rule "do not migrate unrelated products", only the files the Life
Manager backend (`apps/life-manager`) is contractually coupled to are migrated:

- `app/lm/` — Telegram/web onboarding client (LmClient/LmBody/page)
- `netlify/functions/lm-onboard.js` — onboarding resume handler
- `netlify/functions/calendar-connect.js` — signed calendar-connect handler

These are consumed by the backend contract tests
(`apps/life-manager/test/onboarding-resume-contract.test.js`,
`apps/life-manager/test/calendar-connect-signature-contract.test.js`) via the
sibling path `../../landing`, kept byte-identical to source.
