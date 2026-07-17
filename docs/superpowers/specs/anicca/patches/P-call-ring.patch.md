# P-call-ring — make Dais's phone actually ring with Charon (Telnyx bidirectional, docs-verified)

> Spec: `28-product-redesign-merge-2026-06-16.md` §2a. Target repo: `Daisuke134/anicca-products`, path `apps/landing`.
> Task #2. **Goal:** a real outbound Telnyx call to `+818046270314` where Dais's phone rings, Gemini-Live
> **Charon** speaks the next-event briefing two-way, and the recording is non-silent. Run live BY ME (not a
> sub-agent), per Dais 2026-06-16 ("call me for the life manager as well").
> **Zero-uncertainty rule honoured:** every Telnyx param below is confirmed via context7 `/websites/developers_telnyx`
> + firecrawl of `developers.telnyx.com/docs/voice/programmable-voice/media-streaming` (this session). No search at exec time.

---

## §1 Verified facts (context7 + firecrawl, 2026-06-16) — resolves the handoff's wrong "RTP/L16" hypothesis

| concern | VERIFIED truth | source |
|---|---|---|
| dial body | `POST /v2/calls` `{connection_id,to,from,stream_url,stream_track,stream_bidirectional_mode:"rtp",stream_bidirectional_codec:"PCMU"}` is the documented way to start bidirectional RTP streaming on dial | ctx7 + firecrawl "Sending RTP stream" / "RTP stream codec" |
| inbound media frame Telnyx → us | `{event:"media", sequence_number, media:{track,chunk,timestamp,payload}, stream_id}`; **payload = base64-encoded RTP payload (NO headers) = raw μ-law (PCMU 8kHz)** | firecrawl "The payload contains a base64-encoded RTP payload (no headers)" |
| **outbound media frame us → Telnyx** | **`{"event":"media","media":{"payload":"<base64 RTP stream>"}}` — NO `stream_id` in the documented shape**; payload = raw codec (PCMU) base64, chunk 20ms–30s; **1 bidirectional stream/call** | firecrawl "Sending RTP stream … RTP streaming can be sent using media events: {event:media,media:{payload}}" |
| streaming start | starts from the **dial** params (also via `answer`+`streaming_start`) → **no webhook required** for the happy path; bridge detects the WS `start` frame on answer | firecrawl "It can be requested using answer and streaming_start commands in the same way" + dial example |
| codec for AI (future) | `L16` (16kHz linear PCM) "improved support for AI voice agent integrations … eliminating transcoding overhead" — lets Gemini PCM16 pass without μ-law transcode | firecrawl "RTP stream codec" |

**Conclusion:** the existing `telnyxDialBody` + inbound decode (`twilioMuLawToGeminiPcm16`) are CORRECT as-is. The ONLY code change is to make the **outbound** frame match the documented shape (drop `stream_id`), plus add a **`call.answered`→`streaming_start` contingency** (used only if the live call shows the dial-params stream did not auto-start). PCMU stays (lower risk than L16); L16 is recorded as a future optimization, not in this patch.

## §2 Reality found (cited file:line, live tree)

| fact | evidence |
|---|---|
| outbound frame currently includes `stream_id` (docs example omits it) | `apps/landing/netlify/functions/_lib/call-logic.js:266-268` `buildTelnyxMediaFrame` returns `{event:"media",stream_id,media:{payload}}` |
| dial body already correct | `call-logic.js:296-306` `telnyxDialBody` (matches verified dial example) |
| bridge routes Telnyx both ways with tested transcode | `apps/landing/scripts/call-bridge.cjs:72-91` `routeTelnyxMessage`, `:104-119` `routeGeminiMessage(...,buildTelnyxMediaFrame)` |
| runner places the real call + records + accounts frames | `apps/landing/scripts/life-call-telnyx.mjs:112-216` (tunnel → bridge → `/v2/calls` → `record_start` → poll → recording fetch) |
| no `streaming_start` contingency exists | `grep -n "streaming_start" call-logic.js call-bridge.cjs life-call-telnyx.mjs` → 0 hits |
| **live test #17 asserts the OLD `stream_id`** | `__tests__/call-logic.test.js:201-208` `assert.strictEqual(f.stream_id,"32DE0DEA")` — Diff 1 removes `stream_id`, so this test MUST be rewritten (Diff 2), not just appended to, or `node --test` fails |

## §3 Diffs

### Diff 1 — `call-logic.js`: outbound frame to documented shape + `streaming_start` contingency body

```diff
diff --git a/apps/landing/netlify/functions/_lib/call-logic.js b/apps/landing/netlify/functions/_lib/call-logic.js
--- a/apps/landing/netlify/functions/_lib/call-logic.js
+++ b/apps/landing/netlify/functions/_lib/call-logic.js
@@
 /**
  * Build an outbound Telnyx Media Streaming `media` frame (Charon → caller).
- * @param {string} streamId - the Telnyx stream_id from the start frame
+ * Telnyx's documented bidirectional send-back shape is `{event:"media",media:{payload}}`
+ * with NO stream_id (one bidirectional stream per call; Telnyx routes by the socket).
+ * Verified: developers.telnyx.com/docs/voice/programmable-voice/media-streaming "Sending RTP stream".
+ * @param {string} _streamId - accepted for call-site symmetry with buildTwilioMediaFrame; unused
  * @param {string} b64MuLaw - μ-law 8kHz (PCMU) base64 payload (no RTP/file header)
- * @returns {object} { event:"media", stream_id, media:{ payload } }
+ * @returns {object} { event:"media", media:{ payload } }
  */
-function buildTelnyxMediaFrame(streamId, b64MuLaw) {
-  return { event: "media", stream_id: streamId, media: { payload: b64MuLaw } };
+function buildTelnyxMediaFrame(_streamId, b64MuLaw) {
+  return { event: "media", media: { payload: b64MuLaw } };
 }
+
+/**
+ * Body for `POST /v2/calls/{ccid}/actions/streaming_start` — the contingency used only if a
+ * dial-params stream does not auto-start on answer. Same stream config as the dial body.
+ * Verified: media-streaming "It can be requested using answer and streaming_start commands".
+ * @param {object} o
+ * @param {string} o.streamUrl - public wss of the bridge /ws
+ * @returns {object} request body
+ */
+function telnyxStreamingStartBody({ streamUrl }) {
+  return {
+    stream_url: streamUrl,
+    stream_track: "both_tracks",
+    stream_bidirectional_mode: "rtp",
+    stream_bidirectional_codec: "PCMU",
+  };
+}
```

(and add `telnyxStreamingStartBody` to `module.exports` alongside `buildTelnyxMediaFrame`, `telnyxDialBody`.)

### Diff 2 — `call-logic.test.js`: REPLACE existing test #17 (asserts the old stream_id) + add streaming_start test

> ⚠ The live test at `call-logic.test.js:201-208` currently asserts `f.stream_id === "32DE0DEA"`. Diff 1 removes
> `stream_id`, so this test MUST be **rewritten** (not just appended) or `node --test` fails (§5 step 1). Also add
> `telnyxStreamingStartBody` to the test file's `require(...)` destructure.

```diff
diff --git a/apps/landing/netlify/functions/_lib/__tests__/call-logic.test.js b/apps/landing/netlify/functions/_lib/__tests__/call-logic.test.js
--- a/apps/landing/netlify/functions/_lib/__tests__/call-logic.test.js
+++ b/apps/landing/netlify/functions/_lib/__tests__/call-logic.test.js
@@ require destructure (L20-23)
   buildTelnyxMediaFrame,
   parseTelnyxStart,
   telnyxDialBody,
+  telnyxStreamingStartBody,
 } = require("../call-logic");
@@
-// ── 17. Telnyx outbound media frame uses stream_id (not streamSid) ─────────────
-test("buildTelnyxMediaFrame: event=media, stream_id, base64 payload", () => {
-  const f = buildTelnyxMediaFrame("32DE0DEA", "QUJD");
-  assert.strictEqual(f.event, "media");
-  assert.strictEqual(f.stream_id, "32DE0DEA");
-  assert.strictEqual(f.media.payload, "QUJD");
-  assert.strictEqual(f.media.streamSid, undefined, "Telnyx uses stream_id not streamSid");
-});
+// ── 17. Telnyx outbound media frame = documented {event:media,media:{payload}} (NO stream_id) ──
+test("buildTelnyxMediaFrame matches Telnyx docs shape (no stream_id)", () => {
+  const f = buildTelnyxMediaFrame("ignored", "QUJD");
+  assert.strictEqual(f.event, "media");
+  assert.strictEqual(f.media.payload, "QUJD");
+  assert.ok(!("stream_id" in f), "outbound frame must omit stream_id per Telnyx docs");
+});
+// ── 17b. streaming_start contingency body ──
+test("telnyxStreamingStartBody carries rtp+PCMU+both_tracks", () => {
+  const b = telnyxStreamingStartBody({ streamUrl: "wss://x/ws" });
+  assert.strictEqual(b.stream_bidirectional_mode, "rtp");
+  assert.strictEqual(b.stream_bidirectional_codec, "PCMU");
+  assert.strictEqual(b.stream_track, "both_tracks");
+});
```

### Diff 3 — `life-call-telnyx.mjs`: streaming_start contingency if no `start` frame within 6s of dial

```diff
@@  after record_start, before the poll loop
+  // Contingency: if the bridge has not logged a Telnyx `start` frame a few seconds after dial,
+  // the dial-params stream did not auto-start — explicitly request it (docs: answer/streaming_start).
+  await sleep(6000);
+  if (!/twilio_start/.test(bridgeLog)) {
+    try {
+      const { telnyxStreamingStartBody } = require(
+        path.join(here, "..", "netlify", "functions", "_lib", "call-logic.js"));
+      await txPost(`/calls/${encodeURIComponent(ccid)}/actions/streaming_start`,
+        telnyxStreamingStartBody({ streamUrl: wsUrl }));
+      console.log("[runner] streaming_start contingency sent");
+    } catch (e) { console.error("[runner] streaming_start err:", e.message); }
+  }
```

## §4 Run commands

```bash
cd apps/landing
# 1. unit
node --test 'netlify/functions/_lib/__tests__/call-logic.test.js'
# 2. env (no hardcoded secrets)
set -a; . ~/.openclaw/.env; set +a   # TELNYX_API_KEY, TELNYX_CONNECTION_ID, GEMINI_API_KEY
# 3. REAL call to Dais — phone rings, Charon speaks, recording saved
node scripts/life-call-telnyx.mjs --to=+818046270314
```

## §5 E2E acceptance (HARD 0.24/0.31 — no fake)
1. `node --test` for call-logic green THIS session (incl. the 2 new asserts).
2. Live run prints `CALL_CONTROL_ID` + `CALL_SESSION_ID`, `BRIDGE_STREAM_STARTED:true`, `DOWNLINK_FRAMES>0` (Charon spoke), `UPLINK_FRAMES>0` (Dais spoke).
3. **Dais's real phone rings and he hears Charon** (the only human in the loop is him answering).
4. Recording mp3 fetched; `ffmpeg -i rec.mp3 -af volumedetect -f null -` shows non-silent (mean_volume > -50 dB).
5. `docs/verifications/2026-06-16-b-call-charon-dais-telnyx-e2e.md` records the real CALL_SESSION_ID + recording id.

## §6 Boundaries
Only `call-logic.js` (+ its test) and `life-call-telnyx.mjs` change. `telnyxDialBody`, inbound decode, `routeTelnyxMessage`, Twilio path UNCHANGED. No new deps. PCMU kept (L16 = future optimization, separate patch).
