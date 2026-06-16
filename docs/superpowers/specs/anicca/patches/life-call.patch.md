# life-call.patch.md — make the REAL Charon call to +818046270314 connect (Telnyx)

PATCH AUTHOR audit + diff for Anicca subsystem **life-call** (Gemini Charon bidirectional phone call).
Mother repo: `/Users/anicca/anicca` (skills). Products: `/Users/anicca/anicca-project`.
Date: 2026-06-16. Spec: `docs/superpowers/specs/anicca/27c-call-design.md` +
`docs/superpowers/specs/2026-06-16-life-call-telnyx-charon-design.md`.

> **This patch does NOT place a call, apply, commit, or push.** It is the grounded change set
> + the exact commands to place a REAL connected call and verify it. The agent self-serves the
> `TELNYX_API_KEY` (camofox Telnyx-portal login on the provisioned Google OAuth session); the
> **only** genuinely-human blocker is B2 — Dais relaying the Telnyx D60 number-verification code
> spoken to his physical handset (he is the callee anyway).

---

## Gaps

| # | gap (spec claim vs reality) | RAW evidence | severity |
|---|---|---|---|
| G1 | **`TELNYX_API_KEY` is NOT in `~/.openclaw/.env`** — but this is **agent-self-serve**, NOT a Dais task. The Telnyx default path (`call/call.js` → `life-call-telnyx.mjs`) dies on the first guard until the agent mints a V2 key in the Telnyx portal (camofox + the already-provisioned Google OAuth session, HARD #-2/0.30 — "there is nothing a human can do"). | `grep -oE '^[A-Z_]*TELNYX[A-Z_]*' ~/.openclaw/.env` → `NO TELNYX* keys`. Runner: `life-call-telnyx.mjs:88` `if (!API) die("TELNYX_API_KEY missing in env")` where `const API = process.env.TELNYX_API_KEY` (line 45). camofox live (`curl localhost:9377 → 200`); `GOOGLE_LOGIN_EMAIL` + `GOOGLE_LOGIN_PASSWORD` present in env. | **BLOCKER** (agent-self-serve) |
| G2 | **The disputed "proof" `CA2c025395dd03adc740faef93f856717d` is NOT a real call to Dais.** 27c-call-design.md §"LIVE CALL PROOF" presents it as proof; it was a Twilio **self-answer to a US number `+19452364286`**, not +818046270314. The verifier already rejected the offload. | `27c-call-design.md:80-97` — "only `To` differs … US call from the same account succeeds". `2026-06-16-…-telnyx-e2e.md:3-6` confirms "no REAL call to Dais's number +818046270314 ever connected". **This patch never cites that SID as proof.** | **HIGH** (false-proof risk) |
| G3 | **Twilio +818046270314 is permanently blocked (err 21216).** Account+destination fraud hold; lifts only via async Support ticket. Not a code gap. | `…-telnyx-e2e.md:15` `POST /Calls.json To=+818046270314 ×3 → {code:21216, 400}`; `27c-call-design.md:91-94`. Also err 13225/21216 family is the JP fraud-control block named in the task. | HIGH (external) |
| G4 | **Telnyx is wired but blocked by D60 trial gate** — outbound to an unverified destination returns Telnyx err 10010 / level D60. | `…-telnyx-e2e.md:46-48` verbatim: `Telnyx POST /calls 403 {"errors":[{"code":10010,"detail":"Can not make calls to non-verified numbers at this account level D60…"}],"telnyx_error":{"error_code":"D60"}}`. | **BLOCKER** (external, one-time) |
| G5 | **Telnyx balance is only $5.00** — enough for a short call, but a real connected Charon call (~1 min PSTN to JP) must not exhaust it mid-call; needs a confirmed positive balance at run time. | `…-telnyx-design.md:31` / `…-telnyx-e2e.md:27` `GET /v2/balance → 200, $5.00`. | MEDIUM |
| G6 | **Bridge has no Telnyx `media_format.encoding`/`track` handling.** The bridge greps inbound `media.payload` generically and assumes PCMU 8k. Telnyx `start.media_format.encoding` is `PCMU` and inbound media frames carry `media.track` (`inbound`/`outbound`); the bridge ignores `track`, so in `both_tracks` mode it feeds BOTH Dais's audio AND Charon's own playback back into Gemini (echo/self-hearing). | `grep -n 'media_format\|encoding\|PCMU\|track' call-bridge.cjs` → **0 matches**. `routeTelnyxMessage` (call-bridge.cjs:72-91) forwards any `event==="media"` frame to Gemini regardless of `media.track`. | MEDIUM (audio-quality / echo) |
| G7 | **Telnyx runner reports `CALL_STATUS` via bridge frame logs, not the carrier.** It never GETs call status from Telnyx; "connected" is inferred from `twilio_start`/`twilio_stop` log strings (Telnyx mode logs the SAME `twilio_*` strings). Acceptance (spec §4 item 2) wants `CALL_STATUS=completed` + duration>0 from the carrier — currently unproven. | `life-call-telnyx.mjs:159-164,183-188` greps `twilio_media`/`gemini_audio`/`twilio_stop` from bridge stdout; bridge emits `EVENT twilio_start/twilio_media/twilio_stop` even in Telnyx mode (call-bridge.cjs:241-245). No `GET /v2/calls/{ccid}` for status/duration. Telnyx hangup webhook carries `hangup_cause` + duration. | MEDIUM (verification rigor) |
| G8 | **No carrier-truth recording verification.** Runner fetches `/v2/recordings?filter[call_session_id]=…` but acceptance needs duration>0 + non-silent (`ffmpeg volumedetect`); that audio check is described in docs but not executed by the runner. | `life-call-telnyx.mjs:170-180` fetches the recording URL only; no download + `volumedetect`. `ffmpeg` present (`/opt/homebrew/bin/ffmpeg`). | MEDIUM |

Present and OK (no gap): `cloudflared` (`/opt/homebrew/bin/cloudflared`), `ws` (resolvable in `apps/landing`), `ffmpeg`, `GEMINI_API_KEY`, the pure transcode logic (μ-law↔PCM16/24, Charon `gemini-2.5-flash-native-audio-preview-09-2025`), `telnyx-verify-number.mjs` helper, `telnyxDialBody` (`stream_track:both_tracks`, `stream_bidirectional_mode:rtp`, `stream_bidirectional_codec:PCMU`).

---

## Diff

Four changes. (1) provision the key, (2) add a balance preflight, (3) honor Telnyx `media.track` to stop echo, (4) read real carrier status + recording duration so the runner's success is carrier-truth not log-grep.

### D1 — provision `TELNYX_API_KEY` (agent-self-serve via camofox; env-only, no code)

The agent mints the key itself — **no Dais step here** (browser order camofox > cloakbrowser >
agent-browser > playwright-cli, HARD 0.30; Google OAuth session already provisioned, HARD #-2):

```bash
# 1. camofox open the Telnyx portal API Keys page (Google OAuth session persists in default sessionKey)
TAB=$(curl -sS -X POST http://localhost:9377/tabs \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://portal.telnyx.com/#/app/api-keys","userId":"anicca","sessionKey":"telnyx"}' | jq -r .tabId)
# 2. if a login wall shows, click "Sign in with Google" (account = GOOGLE_LOGIN_EMAIL, already consented).
#    Confirm the logged-in account owns connection_id 2982013078364751402 / number +14322234204.
# 3. click "Create API Key" → snapshot to read the freshly-minted V2 key string (shown once).
# 4. write it to env (chmod 600, gitignored — NEVER commit):
#    printf 'TELNYX_API_KEY=%s\n' "<KEY...>" >> ~/.openclaw/.env   (idempotent: dedupe if a prior key exists)
```

Result — `~/.openclaw/.env` gains ONE line (value never printed to chat/commit):

```
TELNYX_API_KEY=KEY...            # Telnyx V2 API key (Bearer). agent-minted. NEVER commit.
# optional explicit overrides (else the runner defaults are used):
# TELNYX_CONNECTION_ID=2982013078364751402
# TELNYX_PHONE_NUMBER=+14322234204
```

Self-verify the key works before relying on it: `curl -sS https://api.telnyx.com/v2/balance
-H "Authorization: Bearer $TELNYX_API_KEY" -o /dev/null -w '%{http_code}\n'` → `200`.

### D2 — `life-call-telnyx.mjs`: balance preflight + carrier-truth status/recording

```diff
--- a/apps/landing/scripts/life-call-telnyx.mjs
+++ b/apps/landing/scripts/life-call-telnyx.mjs
@@
 // ---- real run
 if (!API) die("TELNYX_API_KEY missing in env");
 if (!process.env.GEMINI_API_KEY) die("GEMINI_API_KEY missing in env");
+
+// G5 preflight: refuse to dial on an empty Telnyx balance (a mid-call cutoff is a fake "connected").
+// JSON path confirmed against the live /v2/balance payload (Commands §0 prints the raw shape first):
+//   { "data": { "balance": "5.00", "currency": "USD", "available_credit": "...", ... } }
+// `data.balance` is a STRING → Number() coerces it. NOTE: --dry-run exits BEFORE this block
+// (the `if (DRY) … process.exit(0)` at line 76-85), so the preflight only gates a REAL run.
+{
+  const bal = await txGet("/balance").catch((e) => die("balance check failed: " + e.message));
+  const usd = Number(bal && bal.data && bal.data.balance);
+  console.log(`[runner] telnyx balance=$${isFinite(usd) ? usd.toFixed(2) : "?"} currency=${bal?.data?.currency || "?"}`);
+  if (!isFinite(usd)) die(`unexpected /v2/balance shape: ${JSON.stringify(bal)}`); // path-mismatch fail-loud
+  if (usd < 0.50) die(`telnyx balance too low ($${usd}); top up before dialing`);
+}
@@
   // 6. hang up (best effort) + fetch the recording for this call session
   try { await txPost(`/calls/${encodeURIComponent(ccid)}/actions/hangup`, {}); } catch {}
-  await sleep(4000);
+
+  // G7: carrier-truth status + duration (do NOT infer "connected" from bridge log strings).
+  let callStatus = "unknown";
+  try {
+    const c = await txGet(`/calls/${encodeURIComponent(ccid)}`);
+    callStatus = (c.data && (c.data.status || c.data.state)) || callStatus;
+  } catch (e) { console.error("[runner] call status fetch err:", e.message); }
+
   let recUrl = "";
   let recId = "";
+  let recDurSec = 0;
+  // G8: Telnyx finalizes recordings ASYNCHRONOUSLY after hangup — a single 4s wait false-fails the
+  // recDurSec<3 gate. Poll /v2/recordings until a recording with download_urls + duration appears
+  // (up to ~30s: 10 × 3s). A genuinely-connected call will surface here once Telnyx flushes the mp3.
+  for (let i = 0; i < 10; i++) {
+    await sleep(3000);
     try {
       const recs = await txGet(`/recordings?filter[call_session_id]=${encodeURIComponent(sessionId)}`);
       const r = (recs.data && recs.data[0]) || null;
-    if (r) {
+      if (r && (r.download_urls && (r.download_urls.mp3 || r.download_urls.wav))) {
         recId = r.id;
-      recUrl = (r.download_urls && (r.download_urls.mp3 || r.download_urls.wav)) || "";
+        recUrl = r.download_urls.mp3 || r.download_urls.wav;
         recDurSec = Number(r.duration_millis ? r.duration_millis / 1000 : r.recording_duration || 0) || 0;
+        if (recDurSec > 0) break; // recording finalized with a real duration → done waiting
       }
     } catch (e) {
       console.error("[runner] recording fetch err:", e.message);
     }
+    process.stdout.write(`[rec-poll ${i}] recId=${recId || "-"} dur=${recDurSec}s\n`);
+  }
@@
   console.log("\n==== B-call (Telnyx) RESULT ====");
   console.log(JSON.stringify({
     PROVIDER: "telnyx",
     CALL_CONTROL_ID: ccid,
     CALL_SESSION_ID: sessionId,
     CALL_LEG_ID: legId,
     TO,
     FROM,
+    CALL_STATUS: callStatus,
+    RECORDING_DURATION_SEC: recDurSec,
     RECORDING_STARTED: recStarted,
     RECORDING_ID: recId,
     RECORDING_URL: recUrl,
     BRIDGE_STREAM_STARTED: startedOk,
     BRIDGE_GEMINI_SETUP: setupOk,
     UPLINK_FRAMES: lastIn,
     DOWNLINK_FRAMES: lastOut,
   }, null, 2));
@@
   cleanup();
   // success requires the carrier media stream to have started (Dais's leg connected)
   // and Charon to have spoken at least one downlink frame.
   if (!ccid) process.exit(1);
-  if (!startedOk || Number(lastOut) <= 0) {
-    console.error("[runner] no media stream / no Charon audio — exiting non-zero");
+  // G7/G8: carrier-truth gate — the stream started, Charon spoke, AND the recording is non-trivial.
+  if (!startedOk || Number(lastOut) <= 0 || recDurSec < 3) {
+    console.error(`[runner] FAIL streamStarted=${startedOk} downlink=${lastOut} recDur=${recDurSec}s — exiting non-zero`);
     process.exit(2);
   }
   process.exit(0);
 }
```

### D3 — `call-bridge.cjs`: honor Telnyx `media.track` (G6, stop self-echo)

In `both_tracks` mode Telnyx forks BOTH legs; only the **inbound** (caller=Dais) track should reach
Gemini, else Charon hears himself.

```diff
--- a/apps/landing/scripts/call-bridge.cjs
+++ b/apps/landing/scripts/call-bridge.cjs
@@ function routeTelnyxMessage(msg, state, geminiSend) {
   if (event === "media" && msg.media && msg.media.payload) {
+    // Only feed the caller's (inbound) audio to Gemini. In both_tracks the outbound track is
+    // Charon's own playback; forwarding it back creates an echo/feedback loop.
+    const track = msg.media.track;
+    if (track && track !== "inbound") return "media-skip";
     const pcm16b64 = twilioMuLawToGeminiPcm16(msg.media.payload);
     geminiSend(buildGeminiAudioInput(pcm16b64));
     state.inFrames = (state.inFrames || 0) + 1;
     return "media";
   }
```

### D4 — `__tests__/call-bridge.test.cjs`: cover the track filter (TDD, no real I/O)

```diff
+ test("routeTelnyxMessage ignores outbound (Charon-playback) track frames", () => {
+   const sent = [];
+   const st = {};
+   const out = routeTelnyxMessage(
+     { event: "media", stream_id: "s1", media: { track: "outbound", payload: "AAAA" } },
+     st, (o) => sent.push(o)
+   );
+   assert.equal(out, "media-skip");
+   assert.equal(sent.length, 0);
+   assert.equal(st.inFrames || 0, 0);
+ });
+ test("routeTelnyxMessage forwards inbound (caller) track frames to Gemini", () => {
+   const sent = [];
+   const st = {};
+   const out = routeTelnyxMessage(
+     { event: "media", stream_id: "s1", media: { track: "inbound", payload: "AAAA" } },
+     st, (o) => sent.push(o)
+   );
+   assert.equal(out, "media");
+   assert.equal(sent.length, 1);
+ });
```

---

## Commands (place a REAL connected call to +818046270314 and VERIFY duration>0 + recording)

All run from `/Users/anicca/anicca-project`. They have real side effects — run only intentionally.
`set -a; . ~/.openclaw/.env; set +a` loads the (now-present, D1) `TELNYX_API_KEY` + `GEMINI_API_KEY`.

```bash
cd /Users/anicca/anicca-project
set -a; . ~/.openclaw/.env; set +a

# 0. preflight (no side effects). FIRST confirm the live /v2/balance JSON shape so the D2 gate's
#    `data.balance` path is verified against a REAL payload (NOT assumed), THEN extract the field:
curl -sS https://api.telnyx.com/v2/balance -H "Authorization: Bearer $TELNYX_API_KEY" | jq '.data'
#    expected: {"balance":"5.00","currency":"USD","available_credit":...} → confirm .data.balance exists
curl -sS https://api.telnyx.com/v2/balance -H "Authorization: Bearer $TELNYX_API_KEY" | jq -r '.data.balance'
node apps/landing/scripts/life-call-telnyx.mjs --dry-run      # prints dialBody, exit 0, ZERO side effects
#    (NOTE: --dry-run exits before the balance preflight; the gate only runs on the real call below)

# 1. tests green THIS session (HARD 0.31 — never claim pass without running)
node --test apps/landing/netlify/functions/_lib/__tests__/call-logic.test.js \
            apps/landing/scripts/__tests__/call-bridge.test.cjs

# 2. clear the D60 gate ONCE: Telnyx rings Dais, he relays the spoken code (he is the callee)
node apps/landing/scripts/telnyx-verify-number.mjs --request --method call   # → Dais's phone rings
node apps/landing/scripts/telnyx-verify-number.mjs --submit  --code <CODE>    # → number verified
node apps/landing/scripts/telnyx-verify-number.mjs --status                  # confirm verified

# 3. THE REAL CONNECTED CALL (Dais answers; Charon talks two-way; call is recorded)
node apps/landing/scripts/life-call-telnyx.mjs --to=+818046270314
#   → RESULT JSON with CALL_CONTROL_ID, CALL_SESSION_ID, CALL_STATUS, RECORDING_ID,
#     RECORDING_DURATION_SEC, UPLINK_FRAMES>0, DOWNLINK_FRAMES>0

# 4. INDEPENDENT carrier-API re-verify (don't trust the runner's own print)
CCID=<CALL_CONTROL_ID>; SESS=<CALL_SESSION_ID>
curl -sS "https://api.telnyx.com/v2/calls/$CCID" -H "Authorization: Bearer $TELNYX_API_KEY" \
  | jq '{status:.data.status}'                                   # expect a connected/completed state
curl -sS "https://api.telnyx.com/v2/recordings?filter%5Bcall_session_id%5D=$SESS" \
  -H "Authorization: Bearer $TELNYX_API_KEY" \
  | jq '.data[0] | {id, duration_millis, url:.download_urls.mp3}'  # duration_millis > 0

# 5. recording is NON-SILENT (Charon actually spoke) — carrier audio, not the bridge's own count
REC_URL=<download_urls.mp3>
curl -sSL "$REC_URL" -o /tmp/anicca-bcall.mp3
ffmpeg -hide_banner -i /tmp/anicca-bcall.mp3 -af volumedetect -f null - 2>&1 | grep -E 'mean_volume|max_volume'
#   non-silent ≈ mean_volume around -20..-30 dB (NOT -91 dB which is digital silence)
rm -f /tmp/anicca-bcall.mp3
```

Twilio fallback (only if Telnyx is unusable; +818046270314 is 21216-blocked so this needs an async
Support ticket first — NOT the cheap path): `node apps/landing/scripts/life-call.mjs --to=+818046270314`.

---

## Acceptance

A REAL connected bidirectional Charon call to **+818046270314** is proven ONLY when ALL hold, read
back from the **carrier API** (not the runner's self-report, not the disputed Twilio self-answer SID):

1. **Outbound call CONNECTS to +818046270314.** `GET /v2/calls/{ccid}` returns a connected/answered
   state for `to=+818046270314`, `from=+14322234204`, placed AFTER this patch (fresh `call_session_id`).
2. **Bidirectional Charon voice.** Runner RESULT shows `DOWNLINK_FRAMES>0` (Charon PCM24→μ-law to the
   line) AND `UPLINK_FRAMES>0` (Dais's μ-law→PCM16 to Gemini); bridge logged `EVENT setupComplete`.
3. **Recording non-silent.** `GET /v2/recordings?filter[call_session_id]=…` → a recording with
   `duration_millis > 3000`; `ffmpeg volumedetect` mean_volume in a human-speech range (≈ -20..-30 dB),
   NOT ≈ -91 dB digital silence.
4. **Carrier-truth SID + recording URL.** The patch's verification doc cites the fresh
   `CALL_CONTROL_ID` / `CALL_SESSION_ID` + `RECORDING_ID` + `download_urls.mp3`, each re-checkable via
   the Telnyx API by an independent verifier. **The Twilio SID `CA2c025395…` is explicitly NOT proof.**
5. Tests green this session: `node --test … call-logic.test.js … call-bridge.test.cjs` (incl. the new
   D4 track-filter cases).

---

## Blockers (exact external one-time steps — cheapest path first)

| # | blocker | exact action | who/cost |
|---|---|---|---|
| B1 | **`TELNYX_API_KEY` absent from `~/.openclaw/.env`** (confirmed: `grep` → no TELNYX keys). Without it every real run dies at `life-call-telnyx.mjs:88`. **This is AGENT-SELF-SERVE — not a Dais task.** | The AGENT mints it (Diff D1): camofox the Telnyx portal API-keys page on the provisioned Google OAuth session (HARD #-2/0.30) → confirm the account owns connection `2982013078364751402` / number `+14322234204` → Create V2 key → append `TELNYX_API_KEY=KEY...` to `~/.openclaw/.env` (chmod 600) → self-verify `GET /v2/balance` → 200. | **agent**, ~3 min, **$0** |
| B2 | **Telnyx D60 trial gate** — outbound to unverified destinations = err 10010 (RAW: telnyx-e2e.md:46-48). **The ONLY genuinely-human step.** | Run the 2-step verify (Commands §2): Telnyx **calls Dais's handset**, he relays the spoken code → `--submit --code <CODE>`. Code is delivered ONLY to the physical phone (genuine device-OTP, CLAUDE.md HARD #-1) — Dais is the callee, the one allowed human action. | Dais (answer + relay code), ~3 min, **$0** |
| B3 | **Telnyx balance $5.00** — fine for one short JP call (PSTN-to-JP ≈ a few ¢/min), but a positive balance must exist at run time; D2 preflight refuses < $0.50. | Agent confirms balance live (Commands §0); $5 covers a 1-min proof call. Top-up only if it later runs dry. | agent-check; top-up Dais, optional, **~$5** |
| B4 | (Avoid) **Twilio err 21216 / 13225** on +818046270314 — async Support ticket only, days. **Do NOT use the Twilio path for the proof**; Telnyx (B1+B2) is the cheap, same-day route. | — | n/a — skip Twilio |

The agent self-serves B1 + B3; only **B2 requires Dais** (relay the OTP spoken to his handset, ≈3 min, $0).
After B2, run Commands §3–§5 unattended (Dais just answers his phone) to produce the carrier-verified
proof that satisfies all Acceptance items.
