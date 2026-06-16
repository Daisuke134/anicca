# P-lm-security — close the open-redirect + IDOR holes in `/lm` onboarding (merge blocker for #61)

> Spec: `28-product-redesign-merge-2026-06-16.md` §3a. Target repo: `Daisuke134/anicca-products`, path `apps/landing`.
> Task #1. **Goal:** `/lm` onboarding identity (`uid`) cannot be forged and the redirect cannot be hijacked,
> WITHOUT changing the proven Composio OAuth call. This must merge before PR #61 (`/lm` product).
> **Zero-uncertainty rule:** the fix uses only Node built-in `crypto` (HMAC-SHA256, timing-safe compare) + WHATWG
> `URL` — no new deps, no external API param risk. Composio v3 `/connected_accounts` call is UNCHANGED (same shape
> the live, working `calendar-connect.js:30-58` already uses). context7 `/websites/composio` confirms `connected_accounts`
> takes `{auth_config:{id}, connection:{user_id}}` — unchanged here.

---

## §1 Reality found (the two holes, cited file:line — live tree)

| hole | evidence | impact |
|---|---|---|
| **Open redirect** | `netlify/functions/lm-onboard.js:60-63` `google-callback` → `return { statusCode:302, headers:{ Location: q.state } }` — `state` is fully attacker-controlled (`?action=google-callback&state=https://evil.com`). Also `:51-56` `google-start` builds `state` from unchecked `q.return`. | phishing redirect off aniccaai.com |
| **IDOR / unauthenticated uid** | `gmail-connect.js:15-16` takes `uid` from the query with no auth → anyone starts/reads a Gmail OAuth connection for any `uid`. `lm-onboard.js:65-77` `save` upserts name/phone for any client-supplied `uid`. | account takeover / PII overwrite |
| uid is minted server-side (good base to sign) | `lm-onboard.js:41` `uid = "lm_" + crypto.randomUUID()` | we own the mint point → HMAC-sign it there |

## §2 Fix design (self-contained, no new deps)

1. **Signed uid (HMAC-SHA256).** At mint (`google-start`) issue `sig = base64url(HMAC(LM_UID_SECRET, uid))`. Every
   later call (`gmail-connect`, `save`) MUST present `uid`+`sig`; reject on `timingSafeEqual` mismatch. The browser
   carries `uid`+`sig` through the Composio round-trip via the `state`/return URL. Forging a uid now needs the secret.
2. **Redirect allow-list.** `isAllowedReturn(url)` parses with WHATWG `URL` and permits only host ∈
   {`aniccaai.com`,`www.aniccaai.com`,`localhost`,`127.0.0.1`}; anything else falls back to `https://aniccaai.com/lm`.
   Applied to `q.return` (google-start) and `q.state` (google-callback) so neither can redirect off-site.
3. New env `LM_UID_SECRET` (32+ random bytes) in `~/.openclaw/.env` (chmod 600, never committed) + Netlify env.

## §3 Diffs

### Diff 1 — `netlify/functions/lm-onboard.js`

```diff
diff --git a/apps/landing/netlify/functions/lm-onboard.js b/apps/landing/netlify/functions/lm-onboard.js
--- a/apps/landing/netlify/functions/lm-onboard.js
+++ b/apps/landing/netlify/functions/lm-onboard.js
@@
 const COMPOSIO_API = "https://backend.composio.dev/api/v3";
 const COMPOSIO_KEY = process.env.COMPOSIO_API_KEY;
 const GCAL_AUTH_CONFIG = process.env.COMPOSIO_GCAL_AUTH_CONFIG; // reuse the verified Google app
 const SUPABASE_URL = process.env.SUPABASE_URL;
 const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
+const crypto = require("crypto");
+const LM_UID_SECRET = process.env.LM_UID_SECRET || "";
+const ALLOWED_HOSTS = new Set(["aniccaai.com", "www.aniccaai.com", "localhost", "127.0.0.1"]);
+
+// Sign/verify the server-minted uid so later calls can't forge identity (IDOR fix).
+function signUid(uid) {
+  return crypto.createHmac("sha256", LM_UID_SECRET).update(uid).digest("base64url");
+}
+function verifyUid(uid, sig) {
+  if (!LM_UID_SECRET || !uid || !sig) return false;
+  const expected = signUid(uid);
+  const a = Buffer.from(String(sig));
+  const b = Buffer.from(expected);
+  return a.length === b.length && crypto.timingSafeEqual(a, b);
+}
+// Only allow redirects back to our own hosts (open-redirect fix).
+function safeReturn(url) {
+  try {
+    const u = new URL(String(url));
+    if ((u.protocol === "https:" || u.protocol === "http:") && ALLOWED_HOSTS.has(u.hostname)) return u.toString();
+  } catch {}
+  return "https://aniccaai.com/lm";
+}
@@ google-start
     const uid = "lm_" + (globalThis.crypto?.randomUUID?.() || Date.now().toString(36));
+    if (!LM_UID_SECRET) return json(500, { error: "missing LM_UID_SECRET" });
+    const sig = signUid(uid);
@@
     await upsertUser({ uid }).catch(() => {});
-    const ret = q.return || "https://aniccaai.com/lm";
+    const ret = safeReturn(q.return || "https://aniccaai.com/lm");
+    const retWithId = ret + (ret.includes("?") ? "&" : "?") + "uid=" + uid + "&sig=" + encodeURIComponent(sig);
     const dest = `${redirect}${redirect.includes("?") ? "&" : "?"}state=${encodeURIComponent(
-      ret + (ret.includes("?") ? "&" : "?") + "uid=" + uid,
+      retWithId,
     )}`;
     return { statusCode: 302, headers: { Location: dest }, body: "" };
   }

   if (action === "google-callback") {
-    const back = q.state || "https://aniccaai.com/lm";
+    const back = safeReturn(q.state || "https://aniccaai.com/lm");
     return { statusCode: 302, headers: { Location: back }, body: "" };
   }

   if (action === "save" && event.httpMethod === "POST") {
     if (!SUPABASE_URL || !SUPABASE_KEY) return json(500, { error: "missing supabase config" });
     let body;
     try { body = JSON.parse(event.body || "{}"); } catch { return json(400, { error: "bad json" }); }
-    const { uid, name, phone } = body;
-    if (!uid) return json(400, { error: "missing uid" });
+    const { uid, sig, name, phone } = body;
+    if (!uid) return json(400, { error: "missing uid" });
+    if (!verifyUid(uid, sig)) return json(403, { error: "bad uid signature" });
     const row = { uid };
```

### Diff 2 — `netlify/functions/gmail-connect.js`

```diff
diff --git a/apps/landing/netlify/functions/gmail-connect.js b/apps/landing/netlify/functions/gmail-connect.js
--- a/apps/landing/netlify/functions/gmail-connect.js
+++ b/apps/landing/netlify/functions/gmail-connect.js
@@
 const SUPABASE_URL = process.env.SUPABASE_URL;
 const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
+const crypto = require("crypto");
+const LM_UID_SECRET = process.env.LM_UID_SECRET || "";
+function verifyUid(uid, sig) {
+  if (!LM_UID_SECRET || !uid || !sig) return false;
+  const expected = crypto.createHmac("sha256", LM_UID_SECRET).update(uid).digest("base64url");
+  const a = Buffer.from(String(sig)); const b = Buffer.from(expected);
+  return a.length === b.length && crypto.timingSafeEqual(a, b);
+}

 exports.handler = async (event) => {
   if (!COMPOSIO_KEY || !GMAIL_AUTH_CONFIG) return { statusCode: 500, body: "missing composio config" };
-  const uid = (event.queryStringParameters || {}).uid;
-  if (!uid) return { statusCode: 400, body: "missing uid" };
+  const q = event.queryStringParameters || {};
+  const uid = q.uid;
+  if (!uid) return { statusCode: 400, body: "missing uid" };
+  if (!verifyUid(uid, q.sig)) return { statusCode: 403, body: "bad uid signature" };
```

### Diff 3 — `LmClient.tsx`: carry `sig` alongside `uid` on gmail-connect + save calls

```diff
@@ wherever LmClient reads uid from the URL and calls the functions
-  const uid = params.get("uid");
+  const uid = params.get("uid");
+  const sig = params.get("sig");
@@ gmail connect
-  fetch(`/.netlify/functions/gmail-connect?uid=${encodeURIComponent(uid)}`)
+  fetch(`/.netlify/functions/gmail-connect?uid=${encodeURIComponent(uid)}&sig=${encodeURIComponent(sig)}`)
@@ save
-  body: JSON.stringify({ uid, name, phone })
+  body: JSON.stringify({ uid, sig, name, phone })
```

(Exact `LmClient.tsx` lines confirmed at apply time with `grep -n "uid" apps/landing/app/lm/LmClient.tsx`; the three call-sites get `sig` threaded through. This keeps the diff honest — LmClient is read live before editing.)

## §4 Run commands
```bash
# env (never commit)
python3 -c "import secrets;print('LM_UID_SECRET='+secrets.token_urlsafe(32))" >> ~/.openclaw/.env
# + add LM_UID_SECRET to Netlify site env (via NETLIFY_AUTH_TOKEN API or camofox)
cd apps/landing && npm run build   # static export must still build green
# function smoke (local netlify dev or live after deploy):
curl -s "/.netlify/functions/gmail-connect?uid=lm_x&sig=bad" -o /dev/null -w '%{http_code}\n'   # expect 403
curl -s "/.netlify/functions/lm-onboard?action=google-callback&state=https://evil.com" -i | grep -i location  # expect aniccaai.com/lm, NOT evil.com
```

## §5 Acceptance (HARD 0.31)
1. `npm run build` green (static export unaffected).
2. node:test (or live curl) proves: forged/blank `sig` → **403** on gmail-connect + save; `state=https://evil.com` → redirect to `https://aniccaai.com/lm` (no off-site).
3. A real `/lm` onboarding round-trip still completes (google-start → Composio consent → callback → gcal+Gmail connected) with a VALID signed uid — no regression to the working flow.
4. PR #61 unblocked.

## §6 Boundaries
Only `lm-onboard.js`, `gmail-connect.js`, `LmClient.tsx`. Composio call shape, `lm_users` table, calendar-connect.js UNCHANGED. No new deps (Node `crypto` + `URL` only). New env `LM_UID_SECRET` (secret, env-only).
