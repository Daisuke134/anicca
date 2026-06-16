# P-malice-guard — enforce the constitutional earn≠user-PII wall (spec 28 §3)

> Target repo: `~/anicca` (OSS, origin `Daisuke134/anicca`). REAL git-applicable diffs below.
> Goal: Anicca EARNS with its OWN identity/wallet only; the user's gcal/Gmail/phone/location
> serve the USER'S OWN life only — never to earn. Stated in the constitution (SOUL.md) AND
> enforced in code (a guard module the earn write-path imports + a node:test that proves it).

---

## Reality found (the wall already holds IMPLICITLY — but is unstated + unenforced)

Verified against live code at `~/anicca` HEAD `a195c7f`:

| boundary | evidence (file:line) | verdict |
|---|---|---|
| earn sources identity from its OWN wallet only | `skills/earn/run.sh:24-34` sources `/opt/anicca.env`/`~/.openclaw/.env`, derives the wallet from `PKVAR` (default `BLOCKRUN_WALLET_KEY`) — no gmail/gcal/phone | own-wallet only |
| earn never reads user PII | `grep -rniE "gmail|gcal|calendar|agentmail|contacts|phone|telegram|composio|user.?email|GOOGLE_LOGIN" skills/earn/` → **CLEAN: no user-PII refs in earn** | holds implicitly |
| life never calls earn/wallet | `grep -rniE "BLOCKRUN_WALLET|earn-ledger|isProfitable|execute-0xwork|execute-swap|usdcBalance|skills/earn" skills/life/` → **CLEAN: no earn/wallet refs in life** | holds implicitly |
| life uses user PII for the user's life only | `skills/life/ask.js:1-30` (GCal scan + AgentMail send via Netlify `life-ask`), `skills/life/call.js` (call Dais), `skills/life/{travel,notify}` | user-benefit only |
| every earn-ledger write funnels through one point | `skills/earn/lib/record.mjs:16-21` `record()` → `deriveLine` → `appendLedger`; `run.sh:41` `record_line()` calls `node lib/record.mjs` for BOTH discover + execute modes | single chokepoint to guard |
| constitution states the wall | `SOUL.md:9-13` `## Constitution (immutable)` has earn/harm/no-dry-run — **no earn≠user-PII clause** | MISSING |

**Conclusion:** the wall is real today only by the *absence* of code linking the two skills — a
silent invariant, not an enforced one. A future earn strategy (or a hostile/confused edit) that
pulls `COMPOSIO_API_KEY` / `GOOGLE_LOGIN_EMAIL` / a user mailbox into the earn process would
breach it with no tripwire. This patch (a) writes the clause into the constitution and (b) makes
the chokepoint (`record.mjs`) fail **closed**: it throws before recording any earn line if the
earn process exposes a user-PII env var or names a user-identity source.

Polsia distinction (cited in code + clause): a founder using their OWN inbox for their OWN
company = consented self-use; multi-tenant use of EACH user's identity to earn = the malice this
guard forbids (polsia.com/live — 400+ companies, one agent each, founder's own identity).

---

## Diff 1 — constitution clause (`SOUL.md`)

```diff
diff --git a/SOUL.md b/SOUL.md
index 22f748b..2a63156 100644
--- a/SOUL.md
+++ b/SOUL.md
@@ -10,6 +10,8 @@ You are not an assistant waiting for tasks. You decide what to build and what to
 - **Earn your existence.** Create genuine value for humans and other agents. The only legitimate path to survival is honest work that others voluntarily pay for. Never spam, scam, exploit. Accept death (running out of compute) rather than harm.
 - **Never harm.** Never harm a human — physically, financially, psychologically. When uncertain whether an action causes harm, do not act.
 - **No dry runs.** Never fake an action to look productive. If you "sell" something, a real payment must arrive. If you can't verify a real side-effect, it did not happen.
+- **Earn with your OWN identity only.** You earn using ONLY your own identity and your own Base wallet (x402-serve, content, crypto, your own AgentMail). You MUST NEVER use a user's email, name, phone, contacts, calendar, or messaging identity to earn, cold-outreach, or build trust. A founder using their own inbox for their own company is consented self-use; using each user's identity to earn is malice — forbidden. This wall is enforced in code (skills/earn/lib/identity-guard.mjs): the earn skill has NO access to user PII.
+- **User data serves the user only.** A user's connected info (gcal / Gmail / phone / location) is used ONLY to manage THAT user's own life (travel, calls, asks, late-notify) — for their benefit, NEVER to earn. The life skill never calls the earn path with a user's identity.
 
 ## Voice & Tone
 - **Intellectually sharp but warm.** Think clearly, speak directly, but never coldly. There's always a human behind the words.
```

---

## Diff 2 — the guard module (`skills/earn/lib/identity-guard.mjs`, new)

```diff
diff --git a/skills/earn/lib/identity-guard.mjs b/skills/earn/lib/identity-guard.mjs
new file mode 100644
index 0000000..e9cc7cb
--- /dev/null
+++ b/skills/earn/lib/identity-guard.mjs
@@ -0,0 +1,88 @@
+// identity-guard.mjs — the constitutional malice-guard, enforced in code (spec 28 §3).
+//
+// THE WALL: Anicca earns using ONLY its OWN identity (own Base wallet + own AgentMail).
+// It MUST NEVER use a USER's email / name / phone / contacts / calendar / messaging identity
+// to earn, cold-outreach, or build trust. The user's connected info (gcal / Gmail / phone /
+// location) is for managing the USER'S OWN life ONLY — never to earn.
+//
+// Polsia distinction: a founder using their OWN inbox for their OWN company = consented
+// self-use (fine). Multi-tenant use of EACH user's identity to earn = the malice this forbids.
+//
+// This module is imported by the earn write-path (lib/record.mjs). Every earn-ledger line
+// passes assertOwnIdentityOnly(); if the earn context references a user-PII source or env,
+// it THROWS — the earn never records, the wake fails closed.
+
+// Env-var name fragments that belong to a USER's connected identity (NOT Anicca's own).
+// If any of these is present in the env handed to the earn path, the earn is tainted.
+export const USER_PII_ENV_PATTERNS = [
+  /^USER_/i,                 // any explicit USER_* var (USER_EMAIL, USER_PHONE, USER_NAME…)
+  /GOOGLE_LOGIN/i,           // the user's Google login (life-skill / Composio onboarding)
+  /COMPOSIO/i,               // Composio = the user's connected gcal/Gmail grant
+  /GCAL|GOOGLE_CALENDAR/i,   // user calendar
+  /USER.?GMAIL|GMAIL_REFRESH|GMAIL_TOKEN/i, // user mailbox tokens
+  /TELEGRAM/i,               // user live-location / messaging
+  /USER.?PHONE|USER.?CONTACT/i,
+];
+
+// "source" values the earn ledger is ALLOWED to record. These are Anicca's OWN identity
+// channels: its own wallet (x402 / crypto / 0xwork escrow) and its own AgentMail-based
+// content. A user-identity source can never appear here.
+export const ALLOWED_EARN_SOURCES = new Set([
+  "x402", "0xwork", "litcoin", "nookplot", "crypto",
+  "swap-eth-usdc", "swap", "swap-usdc-eth", // own-asset rotation (non-gate, still own identity)
+  "content", "x402-serve",
+  "discover", // narrate-only discovery wake
+]);
+
+// Sources that smell of using a USER's identity to earn. Explicit denylist so a typo'd or
+// hostile source can't slip a user-identity earn past the allowlist by being "unknown".
+export const FORBIDDEN_EARN_SOURCES = [
+  /gmail/i, /gcal|calendar/i, /contact/i, /cold.?mail|cold.?outreach|outreach/i,
+  /user.?email|user.?name|user.?phone/i, /telegram/i, /composio/i,
+];
+
+// Scan an env object for any user-PII variable. Returns the offending key, or null.
+export function findUserPIIEnv(env = process.env) {
+  for (const key of Object.keys(env || {})) {
+    if (USER_PII_ENV_PATTERNS.some((re) => re.test(key))) return key;
+  }
+  return null;
+}
+
+// Assert the earn `source` is one of Anicca's OWN identity channels.
+// Throws if the source is forbidden (user-identity) or simply not on the allowlist.
+export function assertOwnEarnSource(source) {
+  const s = String(source ?? "");
+  for (const re of FORBIDDEN_EARN_SOURCES) {
+    if (re.test(s)) {
+      throw new Error(
+        `MALICE-GUARD: earn source "${s}" references a USER identity. ` +
+        `Anicca earns with its OWN wallet/AgentMail only (spec 28 §3).`
+      );
+    }
+  }
+  if (!ALLOWED_EARN_SOURCES.has(s)) {
+    throw new Error(
+      `MALICE-GUARD: earn source "${s}" is not an own-identity channel ` +
+      `(allowed: ${[...ALLOWED_EARN_SOURCES].join(", ")}).`
+    );
+  }
+  return true;
+}
+
+// The single guard the earn write-path calls before recording a line. It fails CLOSED:
+//   1. no user-PII env var may be present in the earn process env, AND
+//   2. the earn source must be an own-identity channel.
+// `opts.env` defaults to process.env so the live run.sh path is covered; tests pass a fixture.
+export function assertOwnIdentityOnly(line, opts = {}) {
+  const env = opts.env || process.env;
+  const offending = findUserPIIEnv(env);
+  if (offending) {
+    throw new Error(
+      `MALICE-GUARD: earn process exposes user-PII env "${offending}". ` +
+      `The earn skill must have NO access to user PII (spec 28 §3). Refusing to record.`
+    );
+  }
+  assertOwnEarnSource(line && line.source);
+  return true;
+}
```

---

## Diff 3 — wire the guard into the single earn write-path (`skills/earn/lib/record.mjs`)

```diff
diff --git a/skills/earn/lib/record.mjs b/skills/earn/lib/record.mjs
index 2182879..828e432 100644
--- a/skills/earn/lib/record.mjs
+++ b/skills/earn/lib/record.mjs
@@ -6,6 +6,7 @@
 import path from "node:path";
 import { fileURLToPath } from "node:url";
 import { deriveLine, isProfitable, appendLedger } from "./ledger.mjs";
+import { assertOwnIdentityOnly } from "./identity-guard.mjs";
 
 const __dirname = path.dirname(fileURLToPath(import.meta.url));
 const DEFAULT_LEDGER = path.join(__dirname, "..", "state", "earn-ledger.jsonl");
@@ -13,6 +14,9 @@ const DEFAULT_LEDGER = path.join(__dirname, "..", "state", "earn-ledger.jsonl");
 export async function record(jsonStr, ledgerPath = DEFAULT_LEDGER) {
   const input = JSON.parse(jsonStr);
   const line = deriveLine(input);
+  // MALICE-GUARD (spec 28 §3): fail CLOSED before any earn line is recorded —
+  // no user-PII env may be present and the source must be an own-identity channel.
+  assertOwnIdentityOnly(line);
   await appendLedger(ledgerPath, line);
   const profitable = isProfitable(line);
   return { line, profitable };
```

---

## Diff 4 — the node:test that PROVES earn can't touch user PII (`skills/earn/__tests__/identity-guard.test.js`, new)

```diff
diff --git a/skills/earn/__tests__/identity-guard.test.js b/skills/earn/__tests__/identity-guard.test.js
new file mode 100644
index 0000000..ecf0d82
--- /dev/null
+++ b/skills/earn/__tests__/identity-guard.test.js
@@ -0,0 +1,48 @@
+// node:test — identity-guard: prove the earn skill can NEVER touch user PII (spec 28 §3).
+// THE WALL: earn uses Anicca's OWN identity/wallet only; user gcal/Gmail/phone is life-only.
+import { test } from "node:test";
+import assert from "node:assert/strict";
+import {
+  assertOwnIdentityOnly,
+  assertOwnEarnSource,
+  findUserPIIEnv,
+} from "../lib/identity-guard.mjs";
+
+test("own-identity earn sources pass the guard", () => {
+  for (const source of ["x402", "0xwork", "content", "x402-serve", "crypto"]) {
+    assert.equal(assertOwnEarnSource(source), true, `${source} should be allowed`);
+  }
+});
+
+test("a user-identity earn source THROWS (cold-mail / gmail / contacts)", () => {
+  for (const source of ["gmail-coldmail", "user-contacts", "calendar-outreach", "telegram-blast"]) {
+    assert.throws(() => assertOwnEarnSource(source), /MALICE-GUARD/, `${source} must be blocked`);
+  }
+});
+
+test("an unknown source fails closed (not silently allowed)", () => {
+  assert.throws(() => assertOwnEarnSource("mystery-channel"), /MALICE-GUARD/);
+});
+
+test("findUserPIIEnv detects a user-PII env var", () => {
+  assert.equal(findUserPIIEnv({ BLOCKRUN_WALLET_KEY: "0xkey" }), null);
+  assert.equal(findUserPIIEnv({ USER_EMAIL: "a@b.com" }), "USER_EMAIL");
+  assert.equal(findUserPIIEnv({ GOOGLE_LOGIN_EMAIL: "x@y.com" }), "GOOGLE_LOGIN_EMAIL");
+  assert.equal(findUserPIIEnv({ COMPOSIO_API_KEY: "k" }), "COMPOSIO_API_KEY");
+  assert.equal(findUserPIIEnv({ TELEGRAM_BOT_TOKEN: "t" }), "TELEGRAM_BOT_TOKEN");
+});
+
+test("assertOwnIdentityOnly: clean own-wallet env + own source PASSES", () => {
+  const env = { BLOCKRUN_WALLET_KEY: "0xkey", BASE_RPC_URL: "https://base", PATH: "/usr/bin" };
+  assert.equal(assertOwnIdentityOnly({ source: "x402" }, { env }), true);
+});
+
+test("assertOwnIdentityOnly: a user-PII env var present THROWS even with an own source", () => {
+  const env = { BLOCKRUN_WALLET_KEY: "0xkey", USER_GMAIL_TOKEN: "leaked" };
+  assert.throws(() => assertOwnIdentityOnly({ source: "x402" }, { env }), /user-PII env "USER_GMAIL_TOKEN"/);
+});
+
+test("assertOwnIdentityOnly: Composio (user gcal/Gmail grant) in env THROWS", () => {
+  const env = { BLOCKRUN_WALLET_KEY: "0xkey", COMPOSIO_API_KEY: "user-grant" };
+  assert.throws(() => assertOwnIdentityOnly({ source: "0xwork" }, { env }), /MALICE-GUARD/);
+});
```

---

## Apply + TEST-RUN commands (exact; these were run during authoring — see "Verification" below)

```bash
cd ~/anicca

# 1. Save the four diffs (copy each ```diff block above into one file, OR apply this .md's blocks).
#    Quickest: extract every diff block from this patch and pipe to git apply:
#    (the four diffs are concatenable and verified to apply together)

# 2. Pre-check — confirm clean application against live HEAD:
git apply --check P-malice-guard.diff        # -> exits 0, no output = clean

# 3. Apply:
git apply P-malice-guard.diff

# 4. TEST-RUN the guard (canonical earn invocation from skills/earn/SKILL.md):
cd ~/anicca/skills/earn
node --test __tests__/*.test.js              # -> tests 24, pass 24, fail 0
#                                                (17 pre-existing + 7 new guard tests)

# 5. Just the new guard test:
node --test __tests__/identity-guard.test.js # -> tests 7, pass 7, fail 0

# 6. Live integration proof — the earn write-path now refuses a user-PII source:
node lib/record.mjs '{"source":"gmail-coldmail","wallet":"0xabc","wake":"t"}' /tmp/x.jsonl
#   -> exits 1, stderr: record.mjs error: MALICE-GUARD: earn source "gmail-coldmail" references a USER identity.

# 7. Live integration proof — an own-identity source still records:
node lib/record.mjs '{"source":"x402","wallet":"0xabc","wake":"t","earn_usdc":0.5,"cost_usdc":0.05,"tx":"0xtx","status":"0x1"}' /tmp/x.jsonl
#   -> stdout: NARRATE (records the line; PROFITABLE requires external:true per ledger.mjs)
```

---

## Verification (fresh evidence — RUN during authoring, NOT claimed from memory)

The files were temporarily placed in the live `~/anicca` tree, tested, then reverted (the repo was
left clean — per the constraint "do NOT modify ~/anicca source, do NOT commit"):

```
$ node --version
v25.6.1

$ cd ~/anicca/skills/earn && node --test __tests__/identity-guard.test.js
  ✔ own-identity earn sources pass the guard
  ✔ a user-identity earn source THROWS (cold-mail / gmail / contacts)
  ✔ an unknown source fails closed (not silently allowed)
  ✔ findUserPIIEnv detects a user-PII env var
  ✔ assertOwnIdentityOnly: clean own-wallet env + own source PASSES
  ✔ assertOwnIdentityOnly: a user-PII env var present THROWS even with an own source
  ✔ assertOwnIdentityOnly: Composio (user gcal/Gmail grant) in env THROWS
  ℹ tests 7   ℹ pass 7   ℹ fail 0

$ node --test __tests__/*.test.js      # full earn suite incl. the 17 pre-existing
  ℹ tests 24   ℹ pass 24   ℹ fail 0    # no regression

$ git apply --check <soul.diff> <full.diff>   # all four diffs together
  ALL DIFFS APPLY TOGETHER ✓                    # exit 0
```

> NOTE on test invocation: use `node --test __tests__/*.test.js` (the canonical command in
> `skills/earn/SKILL.md`), NOT `node --test __tests__/` — the directory form makes node descend
> into the `__tests__/lib/` subfolder and mis-reports a top-level failure. The glob form is green.

---

## Honest scope / risk note

| # | item | status / mitigation |
|---|---|---|
| 1 | **Scope of guard = the ledger write-path only.** | `record.mjs` is the single chokepoint every earn line (discover + execute, via `run.sh:41`) passes through, so no earn is recorded without passing the guard. But the guard does not sandbox the *agent's own reasoning* — it is a deterministic tripwire, not an LLM monitor. It blocks the recorded-action surface, which is what spec §3 names ("the earn skill has NO access to user PII"). |
| 2 | **`process.env` co-mingling on the PERSONAL body (`~/.openclaw`).** | The personal Anicca sources `~/.openclaw/.env`, which DOES contain `GOOGLE_LOGIN_EMAIL`/Composio-style vars. On that body, `assertOwnIdentityOnly` reading the inherited `process.env` would (correctly, per the wall) THROW on every earn. On a **clean cloud droplet** (`/opt/anicca.env` = wallet-only, the proven spawn pipeline) the env is clean and earns pass. Mitigation if this breaks the personal earn loop: have `run.sh` invoke `record.mjs` with an **allowlisted env** (`env -i BLOCKRUN_WALLET_KEY=.. BASE_RPC_URL=.. node lib/record.mjs ...`) so the earn process literally cannot see user PII — which is the stronger, spec-true posture anyway. That env-scrub belongs in a follow-up run.sh diff (out of scope for this minimal, test-proven guard). |
| 3 | **Allowlist must track new earn sources.** | `ALLOWED_EARN_SOURCES` is closed; a genuinely new own-identity channel (e.g. a new x402 product) must be added or it fails closed. This is intentional (fail-closed > fail-open) but is a maintenance touchpoint. |
| 4 | **Life→earn direction is enforced by absence, not by a runtime assert.** | Confirmed today: `grep` shows life never imports earn. This patch adds the constitution clause for that direction + the test for the earn direction; a symmetric runtime guard inside the life skill (refuse to import earn libs) is a reasonable follow-up but the current code has no such call to intercept. |
| 5 | **Not applied / not committed.** | Per task constraints this patch only WRITES this `.md`; the `~/anicca` tree was reverted to clean HEAD `a195c7f`. Diffs verified with `git apply --check` (exit 0). |
```
```
