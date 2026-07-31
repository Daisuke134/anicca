# PANEL-0 corrective-4 — rotated-session logout only

Work in `/Users/anicca/anicca-project/.worktrees/lm-panel-control-center` on `feature/lm-panel-control-center`, exact base `5353bc0c1713301d4f4c4194368cbd51296a2ab7`. You are the fresh Sol builder. Do not edit the canonical consolidation spec. Do not deploy, merge, apply migrations, start OAuth, send messages/calls/email, or mutate external systems.

One substantive blocker only: `resolvePanelSession()` returns a `family_id`-derived CSRF used by the rendered panel/control center, while `POST /panel/logout` validates only `csrfToken(raw session)`. Manager reproduction at base returned HTTP 403 and zero revoke calls.

TDD order:

1. Add one production-path RED that starts from a real `resolve_lm_panel_session` response containing `family_id`, obtains the CSRF actually rendered/sent by the UI, POSTs `/panel/logout` with the same cookie and exact Origin, and proves the current base returns 403/revokes 0. The test must also assert wrong Origin/CSRF perform zero revoke.
2. Commit/push RED separately.
3. Minimal GREEN: make logout use the same authoritative resolved-session CSRF contract as commands without weakening Origin/POST/current-binding checks. Successful logout revokes the entire family, clears both cookies, redirects to stable `/panel`, and immediate revisit renders the login path. Do not create a second CSRF scheme.
4. Run the new test, corrective3 4/4, permanent 17/17, focused 63/63, full npm test, eval 33/33, API/UI smoke, diff-check. Inspect changed assertions for weakening.
5. Write `.vcsdd/features/life-manager-panel-control-center/evidence/panel-corrective4-logout.md`, commit/push, and report exact RED/GREEN/evidence SHAs plus upstream/PR head equality and clean status. Side effects must remain 0. Do not claim L3/done.
