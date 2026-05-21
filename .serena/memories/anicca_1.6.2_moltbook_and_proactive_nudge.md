1.6.2 add-ons (2026-02-10):
- Added server-side fixed-schedule proactive App Nudge job: POST /api/admin/jobs/proactive-app-nudge (slot=morning|afternoon|evening). Uses NUDGE_ALPHA_USER_ID alpha routing and dedupeKey app:proactive:<YYYY-MM-DD JST>:<slot>.
- Added Moltbook proactive posting job: POST /api/admin/jobs/moltbook-poster. Creates AgentPost with externalPostId moltbook-daily-<YYYY-MM-DD JST> and posts via Mastodon-compatible API.
- Moltbook env vars (API/Railway): MOLTBOOK_BASE_URL, MOLTBOOK_ACCESS_TOKEN. Optional MOLTBOOK_DRY_RUN=true for audit-only.
- iOS /mobile/nudge/trigger debug event renamed to e2e_pause (no sensor wording); backend renders gentle_pause.
- SSOT docs updated: .cursor/plans/ios/1.6.2/implementation/TODO-NEXT-2026-02-09.md and .cursor/plans/reference/openclaw-anicca.md