# apps/landing — Mr.bot web surface (scoped subset)

This directory contains ONLY the Mr.bot web-tier files migrated from
`Daisuke134/anicca-products:apps/landing/` during 8i REPO-CONSOLIDATE.

The source `apps/landing` is a 397-file shared marketing site hosting many
unrelated products (retreat, fashion, income/UBI, spawn/cloud, cafe, x402).
Per the 8i rule "do not migrate unrelated products", only the files the Mr.bot backend (`apps/mr-bot`) is contractually coupled to are migrated:

- `app/lm/` — Telegram/web onboarding client (LmClient/LmBody/page)
- `netlify/functions/lm-onboard.js` — onboarding resume handler
- `netlify/functions/calendar-connect.js` — signed calendar-connect handler

These are consumed by the backend contract tests
(`apps/mr-bot/test/onboarding-resume-contract.test.js`,
`apps/mr-bot/test/calendar-connect-signature-contract.test.js`) via the
sibling path `../../landing`, kept byte-identical to source.
