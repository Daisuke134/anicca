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
4. **Normalize + strip on every redirect** (reviewer B1+B2): `safeReturn` clears userinfo (`user:pass@`) and deletes any caller-supplied `uid`/`sig` from `return`/`state`, then emits a reconstructed URL — so the only `uid`/`sig` that reaches the browser is the server-minted pair (kills session-fixation), and the raw attacker string is never echoed into `Location:` (kills userinfo-confusion redirect).
5. **Persist `sig` client-side** (reviewer B3): `LmClient` stores `sig` in localStorage (`SIG_KEY`) so it survives reload, threads it through BOTH save POSTs + gmail-connect, and `history.replaceState`s it out of the visible URL (kills Referer/history leak).

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
+// Allow redirects to our own hosts ONLY, and emit a NORMALIZED url with userinfo cleared and any
+// caller-supplied uid/sig stripped. This defeats (B2) the `https://evil.com@aniccaai.com` userinfo
+// confusion (we never echo the raw input) AND (B1) session-fixation where an attacker threads their
+// own uid/sig through `return` (URLSearchParams.get returns the FIRST occurrence, so a pre-seeded
+// uid would win over the freshly minted one). After stripping, the server-minted pair is the only one.
+function safeReturn(url) {
+  try {
+    const u = new URL(String(url));
+    if ((u.protocol === "https:" || u.protocol === "http:") && ALLOWED_HOSTS.has(u.hostname)) {
+      u.username = ""; u.password = "";                          // B2: drop user:pass@
+      u.searchParams.delete("uid"); u.searchParams.delete("sig"); // B1: drop injected identity
+      return u.toString();                                        // reconstructed, never the raw input
+    }
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

### Diff 3 — `LmClient.tsx`: thread + PERSIST `sig` at ALL sites (read, gmail-connect, 2× save)

> Live-read confirmed the exact sites (apps/landing/app/lm/LmClient.tsx): state `:56`, resume effect
> `:65-75` (today persists ONLY `uid`), `saveName` `:84-97`, `connect` `:99-124`, `savePhone` `:126-140`.
> Because the server now REQUIRES `sig`, it must persist across reload (localStorage) and ride BOTH save
> POSTs + gmail-connect, or the legit flow 403s (reviewer B3). There are **two** save sites, not one.

```diff
diff --git a/apps/landing/app/lm/LmClient.tsx b/apps/landing/app/lm/LmClient.tsx
--- a/apps/landing/app/lm/LmClient.tsx
+++ b/apps/landing/app/lm/LmClient.tsx
@@ state
   const [uid, setUid] = useState<string>('');
+  const [sig, setSig] = useState<string>('');
@@ resume effect (:65-75)
     const params = new URLSearchParams(window.location.search);
     const fromCb = params.get('uid');
+    const fromSig = params.get('sig');
     const saved = window.localStorage.getItem(STORAGE_KEY);
+    const savedSig = window.localStorage.getItem(SIG_KEY);
     const id = fromCb || saved || '';
+    const s = fromSig || savedSig || '';
     if (id) {
       setUid(id);
+      setSig(s);
       window.localStorage.setItem(STORAGE_KEY, id);
+      if (s) window.localStorage.setItem(SIG_KEY, s);
       setStep((s) => (s === 'login' ? 'name' : s));
+      // strip uid/sig from the visible URL so they don't leak via Referer/history (reviewer N2)
+      window.history.replaceState(null, '', '/lm');
     }
   }, []);
@@ saveName body (:91) + deps (:97)
-        body: JSON.stringify({ uid, name: name.trim() }),
+        body: JSON.stringify({ uid, sig, name: name.trim() }),
-  }, [name, uid]);
+  }, [name, uid, sig]);
@@ connect fetch (:107) — sig required by gmail-connect, harmless/ignored by calendar-connect (unchanged) + deps (:123)
-          `/.netlify/functions/${fn}?uid=${encodeURIComponent(uid)}`,
+          `/.netlify/functions/${fn}?uid=${encodeURIComponent(uid)}&sig=${encodeURIComponent(sig)}`,
-    [uid],
+    [uid, sig],
@@ savePhone body (:134) + deps (:140)
-        body: JSON.stringify({ uid, phone: phone.trim() }),
+        body: JSON.stringify({ uid, sig, phone: phone.trim() }),
-  }, [phone, uid]);
+  }, [phone, uid, sig]);
```
Add `const SIG_KEY = 'anicca.lm.sig';` next to the existing `STORAGE_KEY` (`'anicca.lm.uid'`) const — dot convention to match.

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
2. node:test (or live curl) proves ALL of: forged/blank `sig` → **403** on gmail-connect + save; `state=https://evil.com` → `https://aniccaai.com/lm`; `state=https://evil.com@aniccaai.com/lm` → emitted host is `aniccaai.com` with userinfo removed (B2); `return=https://aniccaai.com/lm?uid=lm_attacker&sig=X` → the final return URL contains ONLY the server-minted uid/sig, attacker's stripped (B1).
3. A real `/lm` onboarding round-trip still completes (google-start → Composio consent → callback → gcal+Gmail connected) with a VALID signed uid — no regression to the working flow.
4. PR #61 unblocked.

## §6 Boundaries
Only `lm-onboard.js`, `gmail-connect.js`, `LmClient.tsx`. Composio call shape, `lm_users` table, calendar-connect.js UNCHANGED. No new deps (Node `crypto` + `URL` only). New env `LM_UID_SECRET` (secret, env-only).
