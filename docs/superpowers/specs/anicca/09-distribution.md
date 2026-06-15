# 09 — Distribution (OSS + Cloud)
Goal: OSS: `curl aniccaai.com/install | bash` (= scripts/birth.sh). Cloud: aniccaai.com → Stripe subscribe → backend spawns Anicca (Treasury-funded) on DO → /me dashboard (balance/earned/now/next). /install page user-facing (no crypto detail).
Files: anicca-project/apps/landing/(install + /me), anicca-project/apps/api/(stripe webhook → spawn → DO).
Acceptance: subscribe → within minutes an Anicca is live in cloud, owner gets its mail + sees /me; OSS one-liner works on a fresh machine.
