# Steel real cloud E2E evidence

## Verdict

`production life-call → Railway private networking → self-hosted steel-browser → real Chromium → real HTTPS page → CDP DOM readback → session release` is verified end to end.

This closes the infrastructure/CDP uncertainty. It does **not** claim that a real clinic booking has occurred, and it does **not** prove the future general any-site planner. The remaining 11c/11d acceptance is still an actionable care detection followed by a real provider receipt and aftercare.

## Sources checked before the fix

| Source | URL | Core text |
|---|---|---|
| Steel `sessions.routes.ts` | https://github.com/steel-dev/steel-browser/blob/main/api/src/modules/sessions/sessions.routes.ts | `"POST /sessions"` creates a session and `"POST /sessions/:sessionId/release"` releases it. |
| Steel `sessions.schema.ts` | https://github.com/steel-dev/steel-browser/blob/main/api/src/modules/sessions/sessions.schema.ts | `SessionDetails` includes `websocketUrl`. |
| Steel `env.ts` | https://github.com/steel-dev/steel-browser/blob/main/api/src/env.ts | `DOMAIN` is optional; `HOST`, `PORT`, `CDP_DOMAIN`, and `CDP_REDIRECT_PORT` are separate settings. |
| Railway Private Networking | https://docs.railway.com/networking/private-networking | “Every service in a project and environment gets an internal DNS name under the railway.internal domain.” |

## Failure-to-root-cause chain

| Boundary | Measured result | Meaning |
|---|---|---|
| `life-call` DNS lookup | `steel-browser.railway.internal` resolved to Railway private IPv6 | DNS and project/environment placement were correct |
| `:3000/v1/health` | connection refused | the repository's hard-coded port was wrong |
| `:8080/v1/health` | HTTP 200 `{"status":"ok"}` | deployed API listener is 8080 |
| Steel deploy log | `Server listening at http://[::]:8080` | independent confirmation of the listener |
| first session response | `ws://:::8080/` | `HOST=::` was incorrectly advertised as a client URL |
| after `DOMAIN=steel-browser.railway.internal:8080` | valid `ws://steel-browser.railway.internal:8080/` | advertised URL was fixed without a public domain |
| websocket from Steel container | `ws://localhost:8080/` opened | Steel's proxy and Chromium were alive |
| websocket from `life-call` with private DNS Host | HTTP 500 | failure was at the forwarded Host boundary |
| same remote websocket with `Host: localhost:8080` only | opened | Chrome's DNS-rebinding Host rejection was the root cause |

The failed connection created no phantom success. Steel logs show the created sessions were released with HTTP 200.

## Implemented correction

| Component | Correction |
|---|---|
| Steel Railway service | Set private advertised `DOMAIN=steel-browser.railway.internal:8080`; `HOST=::` remains the bind address and no public domain exists |
| `steel-cdp-client.js` | Use the measured private API endpoint `http://steel-browser.railway.internal:8080` |
| `cdp-connection.js` | For `*.railway.internal` only, preserve the destination URL but send `Host: localhost:<port>` through Steel's CDP proxy; non-Railway endpoints remain unchanged |
| Smoke runner | Add `npm run smoke:steel-cloud`; output excludes page text and credentials |

## Real production result

Command context: the committed smoke runner and CDP modules were copied to a temporary path in the production `life-call` container and executed with its production dependencies. No fake fetch, fake CDP, dry run, local browser, or Mac Mini browser was used.

```json
{"started_at":"2026-07-28T03:11:37.617Z","target_url":"https://example.com/","steel_base_url":"http://steel-browser.railway.internal:8080","health":true,"session_id":"45f297be-4d1b-4889-9edb-fd138b677009","websocket_scheme":"ws:","readback":{"final_url":"https://example.com/","marker_present":true},"released":true,"ok":true,"finished_at":"2026-07-28T03:11:39.559Z"}
```

Matching Steel-side facts:

| Fact | Readback |
|---|---|
| session API | `POST /v1/sessions` HTTP 200 from the `life-call` private IPv6 |
| CDP | `Upgrading browser socket` then `Connecting to CDP` |
| real page request | `GET https://example.com/`, resource type `Document` |
| real page response | HTTP 200, `text/html` |
| navigation | page URL became `https://example.com/` |
| release | `POST /v1/sessions/45f297be-4d1b-4889-9edb-fd138b677009/release` HTTP 200 |

## Post-merge production readback

PR `#1198` merged as `3a8364a561ef773e42a6ca18e844c6b82eafac94`. Railway deployment `e400fa32-fa31-4eae-88fd-570b1e0034d7` reported `SUCCESS` with the exact same `commitHash`.

The smoke command was then run from the newly deployed production image, not from the temporary pre-merge copy:

```json
{"started_at":"2026-07-28T03:18:34.193Z","target_url":"https://example.com/","steel_base_url":"http://steel-browser.railway.internal:8080","health":true,"session_id":"46f59beb-066b-4bce-9d60-8322959e1cda","websocket_scheme":"ws:","readback":{"final_url":"https://example.com/","marker_present":true},"released":true,"ok":true,"finished_at":"2026-07-28T03:18:36.185Z"}
```

Verification summary:

| Check | Result |
|---|---|
| focused Steel/booking/smoke tests | 99/99 PASS |
| deterministic evals | 134/134 PASS |
| full Life Manager suite | 659/660 PASS; sole failure is the pre-existing host-state assertion that expects the actually-loaded `ai.anicca.life-manager-dev` job to be unloaded |
| scoped gitleaks (`canonical/main..feature`) | 4 commits, no leaks |
| TruffleHog PR check | PASS |

The loaded Mac Mini job was not stopped to manufacture a green host-state test.

## Remaining boundary

| Proven | Not yet proven |
|---|---|
| private service discovery, Steel API, real Chromium CDP, arbitrary public HTTPS navigation, DOM evaluation, cleanup | login/session persistence per provider, CAPTCHA/OAuth/3DS handoff, general prompt-to-site planning, real clinic form submission/readback |

Those remaining capabilities are separate product acceptance items; this smoke must not be relabeled as a completed booking.
