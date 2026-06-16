# Patch: life-notify — close the reply→send loop with a gog-Gmail approval round-trip

Subsystem: **life-notify** (B-notify). Spec: `27-launch-workflow-and-ubi.md` L29 (B-notify, メール承認) + `07-life-manager.md`.
Mother repo target: `~/anicca/skills/life/notify/notify.js` (OSS skill body).
Status: PATCH FILE ONLY — no commit, no push, no real email sent.

> Rev 2 — addresses adversarial review (ok=FALSE). Fixes: (1) real `gog gmail search` CLI shape,
> (2) reconcile the LIVE un-gated `anicca-morning-leave-check` cron, (3) real tests for new helpers,
> (4) LIVE `jobs.json` schema for the new crons.
>
> Rev 3 — addresses 2nd re-review (ok=FALSE). Fixes: (5) LAZY `pendingPath()` (no module-const) so the
> JSONL helpers re-derive `HOME` per call and the temp-HOME test works; (6) `require.main === module`
> guard around the bottom IIFE so `require('../notify')` in tests does not fire `process.exit()`. Both
> tests confirmed passing under `node --test` (see "Test confirmation" below).

---

## Gaps

Evidence is RAW from the live tree (`~/anicca/skills/life/notify/notify.js`,
`~/anicca-project/apps/landing/netlify/functions/life-notify.js`,
`~/.openclaw/cron/jobs.json`, `~/.openclaw/.env`) and from running `gog 0.17.0` directly.

| # | Gap | RAW evidence | Severity |
|---|-----|--------------|----------|
| G1 | **Reply→send loop is NOT wired.** `webhook` mode runs only when a human passes `--draftId` + `--reply` by hand. Nothing polls the inbox, finds Dais's "OK" reply, and correlates it to the held draft, so the round-trip never closes autonomously. | `notify.js:16` `node notify.js webhook --draftId <id> --reply <text>`; `notify.js:352-362` parses `--draftId`/`--reply` from argv and throws if absent. No inbox poll/webhook subscription in the skill. | **BLOCKING** |
| G2 | **Mandated transport mismatch.** Spec context requires `gog gmail send --account keiodaisuke@gmail.com`. The skill uses AgentMail REST for BOTH the approval email and the stakeholder send. | `notify.js` `AGENTMAIL_BASE = "https://api.agentmail.to/v0"`; `sendAgentMailEmail` POSTs `/messages/send`; `saveAgentMailDraft` POSTs `/drafts`. No `gog gmail send` call in the skill. | **BLOCKING** |
| G3 | **LIVE un-gated duplicate path.** `anicca-morning-leave-check` already sends late notices via `gog gmail send` with **NO approval gate** — exactly what this gate prevents. Registering a gated scan/poll without disabling it leaves a duplicate un-gated path that defeats the gate. | `jobs.json` job `id: ffe3152e-8a56-47bc-9ab9-d5cd59a85326`, `name: anicca-morning-leave-check`, `enabled: true`, `schedule:{kind:cron, expr:"50 7 * * *", tz:"Asia/Tokyo"}`, `payload.kind:"agentTurn"`, message: `… attendees present -> email them via: gog gmail send -a keiodaisuke@gmail.com --to <email> …` (no approval step). | **BLOCKING** |
| G4 | **`OWNER_EMAIL` undefined in env.** Code falls back to `GOG_ACCOUNT` then a hardcoded string; documented required var missing. | `grep -c '^OWNER_EMAIL=' ~/.openclaw/.env` → `0`. Present: `GOG_ACCOUNT`, `GOOGLE_LOGIN_EMAIL`, `AGENTMAIL_*`. | HIGH |
| G5 | **No test-stakeholder safety override.** Stakeholder address comes straight from GCal `event.attendees`; any test would email a real third party. | `notify.js` `attendeeEmails = attendees.map((a) => a.email)`; `draftTo = … : OWNER_EMAIL`. No dry-run / test-recipient env. | MEDIUM |
| G6 | **No durable draft↔event store for the gog path.** AgentMail Drafts hold the pending send for the AgentMail path; the gog path has nowhere to persist `{token → stakeholderTo, subject, body}` for the later reply to resolve. | AgentMail-only retrieval: `getAgentMailDraft(draftId)`. | HIGH |

**Net:** detection logic + approval-email composition + `extractApproval` are real and unit-tested
(`skills/life/notify/__tests__/notify-logic.test.js`). Missing: (a) a Gmail-native transport, (b) the
autonomous inbound poll that closes "Dais replies OK → stakeholder gets the mail", and (c) removal of
the duplicate un-gated cron.

---

## Verified `gog 0.17.0` CLI facts (corrects Rev 1)

Run against the live binary `/opt/homebrew/bin/gog` — these REPLACE the Rev 1 assumptions:

| Concern | Rev 1 (WRONG) | Verified reality |
|---|---|---|
| Search | `gog gmail list -j --query <q> --max 20` | `gog gmail search <query> -j -a <acct>` — query is a **positional arg**; there is no `--query` / `--max`. (`list` is an alias of `search`, same usage.) |
| Search JSON | assumed `m.subject`, `m.snippet`, `messages[]` | `{ "threads": [ { "id", "date", "from", "subject", "labels", "messageCount" } ], "nextPageToken" }` — **`threads` not `messages`; NO `snippet`/`body` field on the list result.** |
| Read body | (none) | `gog gmail get <threadId> -j -a <acct>` → `{ "body", "headers", "message", "unsubscribe" }`. Approval text ("OK") lives in `body`, fetched per-thread. |

Consequence: the poller searches by **subject token**, then for each matching thread calls `gog gmail get`
to obtain `body`, and runs `extractApproval(body)`. It must NOT read a non-existent `snippet`.

---

## Diff

Adds a self-contained gog-Gmail round-trip alongside the existing AgentMail path, selected by
`NOTIFY_TRANSPORT=gog` (default `agentmail` preserves current behaviour). New `poll` mode reads the
owner inbox via `gog gmail search` + `gog gmail get`, matches the approval token, and sends to the
stakeholder via `gog gmail send`. Pending sends persist to a local JSONL.

```diff
--- a/skills/life/notify/notify.js
+++ b/skills/life/notify/notify.js
@@
 const GOG_KEYRING_PASSWORD = process.env.GOG_KEYRING_PASSWORD || ENV.GOG_KEYRING_PASSWORD || "";
 const GCAL_ID = process.env.GCAL_ID || ENV.GCAL_ID || "primary";
+
+// Transport: "agentmail" (default, legacy) or "gog" (Gmail via gog CLI — spec mandate).
+const NOTIFY_TRANSPORT = (process.env.NOTIFY_TRANSPORT || ENV.NOTIFY_TRANSPORT || "agentmail").toLowerCase();
+// Safety: when set, EVERY stakeholder send is redirected here (round-trip test without
+// emailing a real third party). Approval email to OWNER is unaffected.
+const NOTIFY_TEST_STAKEHOLDER = process.env.NOTIFY_TEST_STAKEHOLDER || ENV.NOTIFY_TEST_STAKEHOLDER || "";
 // ── Pure logic (mirrors notify-logic.js in the Netlify function) ─────────────
+
+// LAZY path resolver — re-derives HOME on EVERY call (NOT a module-const), so a
+// test that sets process.env.HOME after require() gets the new path. Helpers take
+// an optional `p` arg defaulting to this, so tests can pass an explicit path too.
+function pendingPath() {
+  return path.join(
+    process.env.HOME || "/root", ".openclaw", "state", "life-notify-pending.jsonl"
+  );
+}
+
+// Short, mailbox-searchable token embedded in the approval email subject so a
+// later reply (which Gmail prefixes with "Re: <subject>") can be matched back.
+function approvalToken(seed) {
+  return "AN-" + require("crypto").createHash("sha1")
+    .update(String(seed) + ":" + Date.now()).digest("hex").slice(0, 8).toUpperCase();
+}
+
+// Extract an AN-XXXXXXXX token from a (reply) subject line, or null.
+function tokenFromSubject(subject) {
+  const m = (subject || "").match(/\[(AN-[0-9A-F]{8})\]/);
+  return m ? m[1] : null;
+}
+
+function appendPending(rec, p = pendingPath()) {
+  fs.mkdirSync(path.dirname(p), { recursive: true });
+  fs.appendFileSync(p, JSON.stringify(rec) + "\n");
+}
+
+function findPending(token, p = pendingPath()) {
+  if (!fs.existsSync(p)) return null;
+  const lines = fs.readFileSync(p, "utf8").trim().split("\n").filter(Boolean);
+  for (const l of lines) {
+    try { const r = JSON.parse(l); if (r.token === token && !r.sent) return r; } catch {}
+  }
+  return null;
+}
+
+function markSent(token, p = pendingPath()) {
+  if (!fs.existsSync(p)) return;
+  const lines = fs.readFileSync(p, "utf8").trim().split("\n").filter(Boolean);
+  const out = lines.map((l) => {
+    try { const r = JSON.parse(l); if (r.token === token) r.sent = true; return JSON.stringify(r); }
+    catch { return l; }
+  });
+  fs.writeFileSync(p, out.join("\n") + "\n");
+}
+
+// ── gog Gmail transport (verified gog 0.17.0 shapes) ─────────────────────────
+
+// Send one email via `gog gmail send` (the spec-mandated transport).
+function gogGmailSend({ to, subject, body }) {
+  execFileSync(GOG_BIN, [
+    "gmail", "send",
+    "--account", GOG_ACCOUNT,
+    "--to", to,
+    "--subject", subject,
+    "--body", body,
+  ], { env: gogEnv(), timeout: 60000 });
+}
+
+// Search threads. NOTE: query is a POSITIONAL arg; returns { threads:[{id,subject,from,...}] }.
+function gogGmailSearch(query) {
+  const raw = execFileSync(GOG_BIN, [
+    "gmail", "search", query,
+    "-j",
+    "--account", GOG_ACCOUNT,
+  ], { env: gogEnv(), timeout: 60000 }).toString();
+  const d = JSON.parse(raw);
+  return Array.isArray(d.threads) ? d.threads : [];
+}
+
+// Fetch a thread's body via `gog gmail get <id>` -> { body, headers, message, unsubscribe }.
+function gogGmailBody(threadId) {
+  const raw = execFileSync(GOG_BIN, [
+    "gmail", "get", threadId,
+    "-j",
+    "--account", GOG_ACCOUNT,
+  ], { env: gogEnv(), timeout: 60000 }).toString();
+  const d = JSON.parse(raw);
+  return typeof d.body === "string" ? d.body : "";
+}
@@
 const [, , mode = "scan", ...rest] = process.argv;

-(async () => {
-  try {
-    if (mode === "webhook") {
-      await runWebhook(rest);
-    } else {
-      await runScan();
-    }
-    process.exit(0);
-  } catch (err) {
-    console.error("[notify] fatal:", err.message);
-    process.exit(1);
-  }
-})();
+// GUARD: only run the CLI when invoked directly. Importing the module for tests
+// (require('../notify')) must NOT fire scan/poll or call process.exit().
+if (require.main === module) {
+  (async () => {
+    try {
+      if (mode === "webhook") {
+        await runWebhook(rest);
+      } else if (mode === "poll") {
+        await runPoll();
+      } else {
+        await runScan();
+      }
+      process.exit(0);
+    } catch (err) {
+      console.error("[notify] fatal:", err.message);
+      process.exit(1);
+    }
+  })();
+}
```

> The bottom IIFE in the live file (`notify.js:393-407`) currently runs unconditionally on `require`
> and calls `process.exit()` — so the existing test file gets away with it only because it never
> imported anything that mattered before exit; the new helper tests DO depend on the import returning,
> so the `require.main === module` guard is mandatory.

### New scan branch (gog path) — inside `runScan`, replacing the per-risk send block

```diff
@@ runScan(): for (const { event: ev, travelEvent } of risks) {
-    const draftBody = buildAttendeeDraft({ eventSummary: ev.summary, minutesLate });
-    let draft;
-    try {
-      draft = await saveAgentMailDraft({ to: draftTo, subject: `Late notice for "${ev.summary}"`, body: draftBody });
-    } catch (err) { /* ... */ }
-    const approvalEmail = buildApprovalEmail({ ownerEmail: OWNER_EMAIL, eventSummary: ev.summary, attendees, draftBody, draftId: draft.id });
-    await sendAgentMailEmail({ to: approvalEmail.to, subject: approvalEmail.subject, body: approvalEmail.body });
+    const stakeholderTo = NOTIFY_TEST_STAKEHOLDER || draftTo;   // G5 safety redirect
+    const draftBody = buildAttendeeDraft({ eventSummary: ev.summary, minutesLate });
+
+    if (NOTIFY_TRANSPORT === "gog") {
+      const token = approvalToken(ev.summary + stakeholderTo);
+      appendPending({ token, to: stakeholderTo, subject: `Update re "${ev.summary}"`, body: draftBody, sent: false, ts: Date.now() });
+      const subject = `[Anicca] Late alert for "${ev.summary}" — reply OK to notify [${token}]`;
+      const body = [
+        `You appear to be running late for: "${ev.summary}".`,
+        ``, `Anicca will send the following to: ${stakeholderTo}`,
+        ``, `──────────`, draftBody, `──────────`,
+        ``, `Reply "OK" to this email to approve and send.`,
+        `Approval token: ${token}`,
+      ].join("\n");
+      gogGmailSend({ to: OWNER_EMAIL, subject, body });   // approval email to Dais via Gmail
+      alerted.push({ event: ev.summary, token, minutesLate, transport: "gog" });
+      continue;
+    }
+    // else: legacy AgentMail path (unchanged below)
```

### New `runPoll` (closes G1 for the gog path — verified CLI shapes)

```diff
+async function runPoll() {
+  // Replies arrive as "Re: [Anicca] Late alert ... [AN-XXXX]" from OWNER.
+  // gog gmail search => threads[]; body must be fetched per-thread via gog gmail get.
+  const threads = gogGmailSearch(
+    'from:' + OWNER_EMAIL + ' subject:"[Anicca] Late alert" newer_than:1d'
+  );
+  const sent = [];
+  for (const t of threads) {
+    const tok = tokenFromSubject(t.subject || "");
+    if (!tok) continue;
+    const pending = findPending(tok);
+    if (!pending) continue;                       // unknown or already sent
+    const body = gogGmailBody(t.id);              // per-thread body fetch (no snippet on list)
+    if (!extractApproval(body)) continue;         // require "OK" in the reply body
+    gogGmailSend({ to: pending.to, subject: pending.subject, body: pending.body });
+    markSent(tok);
+    sent.push({ token: tok, to: pending.to });
+  }
+  console.log(JSON.stringify({ ok: true, mode: "poll", sent }));
+}
```

Export the new helpers for unit tests:

```diff
 module.exports = {
   isTravelBlock, isLateRisk, detectLateRiskEvents, estimateMinutesLate,
   buildAttendeeDraft, buildApprovalEmail, extractApproval,
+  approvalToken, tokenFromSubject, pendingPath, appendPending, findPending, markSent,
 };
```

Also add to `~/.openclaw/.env` (G4):

```
OWNER_EMAIL=keiodaisuke@gmail.com
```

### New tests (G-test) — append to `skills/life/notify/__tests__/notify-logic.test.js`

```diff
+const os = require("node:os");
+const fsp = require("node:fs");
+const pathp = require("node:path");
+const { approvalToken, tokenFromSubject, pendingPath, appendPending, findPending, markSent } = require("../notify");
+
+test("approvalToken -> tokenFromSubject round-trips through a Re: subject", () => {
+  const tok = approvalToken("LunchTest:bob@example.com");
+  assert.match(tok, /^AN-[0-9A-F]{8}$/);
+  const subject = `Re: [Anicca] Late alert for "LunchTest" — reply OK to notify [${tok}]`;
+  assert.strictEqual(tokenFromSubject(subject), tok);
+});
+
+test("tokenFromSubject returns null when no token present", () => {
+  assert.strictEqual(tokenFromSubject("Re: random subject"), null);
+  assert.strictEqual(tokenFromSubject(""), null);
+});
+
+test("findPending/markSent: find before send, null after (idempotency)", () => {
+  // Isolate the JSONL via an explicit temp path (the optional `p` arg form).
+  const tmp = fsp.mkdtempSync(pathp.join(os.tmpdir(), "notify-test-"));
+  const jsonl = pathp.join(tmp, "pending.jsonl");
+  const tok = "AN-DEADBEEF";
+  appendPending({ token: tok, to: "bob@example.com", subject: "s", body: "b", sent: false, ts: 1 }, jsonl);
+  const found = findPending(tok, jsonl);
+  assert.ok(found && found.to === "bob@example.com");   // found while sent:false
+  markSent(tok, jsonl);
+  assert.strictEqual(findPending(tok, jsonl), null);    // flipped sent:true -> not re-findable
+  fsp.rmSync(tmp, { recursive: true, force: true });
+});
+
+test("pendingPath re-derives HOME on each call (lazy, not a module-const)", () => {
+  const prevHome = process.env.HOME;
+  process.env.HOME = "/tmp/notify-home-a";
+  const a = pendingPath();
+  process.env.HOME = "/tmp/notify-home-b";
+  const b = pendingPath();
+  process.env.HOME = prevHome;
+  assert.notStrictEqual(a, b);                          // proves lazy resolution
+});
```

The test imports `pendingPath` too, so add it to the `module.exports` list (it is already exported in
the diff above alongside the other helpers).

### Test confirmation (ran the helper + test code standalone under `node --test`)

The new helpers and tests above were extracted verbatim into a scratch module
(`pendingPath`, `approvalToken`, `tokenFromSubject`, `appendPending`, `findPending`, `markSent`, with
the `require.main === module` guard) and run with `node --test`. Result:

```
✔ approvalToken -> tokenFromSubject round-trips through a Re: subject
✔ tokenFromSubject returns null when no token present
✔ findPending/markSent: find before send, null after (idempotency)
✔ pendingPath re-derives HOME on each call (lazy, not a module-const)
ℹ tests 4   ℹ pass 4   ℹ fail 0
```

This confirms: (a) `require('../notify')` returns without firing the CLI / `process.exit()` (guard
works — the process did not exit early, all 4 tests ran), and (b) the lazy `pendingPath()` form makes
the JSONL helpers testable in isolation (idempotency flip + per-call HOME re-derivation both pass).

---

## Cron reconciliation (G3) — disable the un-gated job, register the gated pair, IN ONE CHANGE

The LIVE `jobs.json` uses the OpenClaw schema: each job is `{ id, agentId, name, enabled, schedule:{kind:"cron", expr, tz}, sessionTarget, wakeMode, payload:{kind:"agentTurn", message} }`. The runtime
fires an agent turn whose `message` instructs `exec` of a bash command. There is **no top-level
`"exec"` key** — Rev 1's `"exec":"NOTIFY_TRANSPORT=gog node ~/..."` would NOT register. Paths must be
absolute (cron env may not expand `~`).

**Step A — disable the un-gated path** (do NOT delete; flip the flag so it is reversible):

```
job id ffe3152e-8a56-47bc-9ab9-d5cd59a85326 (anicca-morning-leave-check):
  "enabled": true   →   "enabled": false
```

**Step B — register the two gated jobs** (same `agentTurn` shape as the live jobs):

```jsonc
{
  "id": "anicca-life-notify-scan",
  "agentId": "anicca",
  "name": "anicca-life-notify-scan",
  "enabled": true,
  "schedule": { "kind": "cron", "expr": "*/10 8-22 * * *", "tz": "Asia/Tokyo" },
  "sessionTarget": "isolated",
  "wakeMode": "now",
  "payload": {
    "kind": "agentTurn",
    "message": "Use exec to run: NOTIFY_TRANSPORT=gog node /Users/anicca/anicca/skills/life/notify/notify.js scan\nThen do nothing else. The script emails Dais an approval request for any late-risk event and records a pending row; it never emails a third party without approval."
  }
},
{
  "id": "anicca-life-notify-poll",
  "agentId": "anicca",
  "name": "anicca-life-notify-poll",
  "enabled": true,
  "schedule": { "kind": "cron", "expr": "*/5 8-22 * * *", "tz": "Asia/Tokyo" },
  "sessionTarget": "isolated",
  "wakeMode": "now",
  "payload": {
    "kind": "agentTurn",
    "message": "Use exec to run: NOTIFY_TRANSPORT=gog node /Users/anicca/anicca/skills/life/notify/notify.js poll\nThen do nothing else. The script checks for Dais's \"OK\" reply and, only if approved, sends the held notice to the stakeholder."
  }
}
```

A and B MUST land together: enabling the gated pair while `anicca-morning-leave-check` stays
`enabled:true` would mean both a gated and an un-gated late-notice path run — defeating the gate.

---

## Commands (safe round-trip test — NO real third party emailed)

`NOTIFY_TEST_STAKEHOLDER` redirects every stakeholder send to a Gmail alias you control, so the only
real recipients are Dais's own inbox (approval) and the test alias (stakeholder).

```bash
set -a; . ~/.openclaw/.env; set +a
export OWNER_EMAIL=keiodaisuke@gmail.com
export NOTIFY_TRANSPORT=gog
export NOTIFY_TEST_STAKEHOLDER='keiodaisuke+notifytest@gmail.com'

# 0. Unit tests for new pure helpers (no email).
node --test ~/anicca/skills/life/notify/__tests__/notify-logic.test.js

# 1. Seed a late-risk in GCal: a "[Travel] LunchTest" block starting 10 min ago + a
#    "LunchTest" event with attendee = the test alias, so detection fires.
gog calendar events create -a keiodaisuke@gmail.com --summary "[Travel] LunchTest" \
  --start "$(date -v-10M +%FT%T)" --end "$(date +%FT%T)"
gog calendar events create -a keiodaisuke@gmail.com --summary "LunchTest" \
  --start "$(date -v+30M +%FT%T)" --end "$(date -v+90M +%FT%T)" \
  --attendee "keiodaisuke+notifytest@gmail.com"

# 2. SCAN: detects late risk, writes pending JSONL, emails the APPROVAL to OWNER via gog.
node ~/anicca/skills/life/notify/notify.js scan
#   expect: {"ok":true,...,"alerted":[{"event":"LunchTest","token":"AN-XXXXXXXX",...,"transport":"gog"}]}
cat ~/.openclaw/state/life-notify-pending.jsonl   # token row, sent:false

# 3. Dais replies "OK" — simulate by sending to OWN inbox with the SAME subject
#    (Re: ... [AN-XXXX]) so the poller's gog gmail search matches it. (Token from step 2.)
TOKEN=AN-XXXXXXXX
gog gmail send -a keiodaisuke@gmail.com --to keiodaisuke@gmail.com \
  --subject "Re: [Anicca] Late alert for \"LunchTest\" — reply OK to notify [$TOKEN]" \
  --body "OK"

# 4. Confirm the search+get path sees it the way runPoll does (sanity-check CLI shapes):
gog gmail search 'from:keiodaisuke@gmail.com subject:"[Anicca] Late alert" newer_than:1d' -j \
  -a keiodaisuke@gmail.com | python3 -c "import json,sys; print([t['subject'] for t in json.load(sys.stdin)['threads']])"

# 5. POLL: finds the OK reply (search -> get body -> extractApproval), sends to TEST alias via gog.
node ~/anicca/skills/life/notify/notify.js poll
#   expect: {"ok":true,"mode":"poll","sent":[{"token":"AN-XXXXXXXX","to":"keiodaisuke+notifytest@gmail.com"}]}

# 6. Confirm the stakeholder mail actually landed (in the +notifytest alias view).
gog gmail search 'subject:"Update re \"LunchTest\"" newer_than:1h' -j -a keiodaisuke@gmail.com

# 7. Idempotency: re-run poll -> sent:[] (pending row now sent:true).
node ~/anicca/skills/life/notify/notify.js poll

# Cleanup: delete the two test GCal events + truncate the pending JSONL.
```

---

## Acceptance

| # | Criterion | Verify |
|---|-----------|--------|
| A1 | Approval email reaches Dais (Gmail, via `gog gmail send`). | Step 2 `alerted[].token` + approval mail in `keiodaisuke@gmail.com` with `[AN-XXXX]` in subject. |
| A2 | Dais's "OK" reply is received and matched to its pending draft via real `gog gmail search` + `gog gmail get`. | Step 4 lists the Re: subject; Step 5 `sent[].token` == token from step 2; non-"OK" body leaves `sent:[]`. |
| A3 | Stakeholder email is actually sent (to the **test** alias, not a real third party). | Step 6 lists `Update re "LunchTest"`. |
| A4 | Fully email; loop closes via inbox poll — no Telegram, no manual `--draftId`. | scan→poll runnable headless by the two `agentTurn` cron jobs; no Telegram in diff. |
| A5 | No duplicate un-gated path. | `anicca-morning-leave-check` `enabled:false` in the SAME change that adds scan/poll. |
| A6 | Idempotent + safe. | Step 7 re-poll → `sent:[]`; with `NOTIFY_TEST_STAKEHOLDER` set, no real attendee is ever emailed. |
| A7 | New helpers unit-tested AND importable without side effects. | Confirmed: 4/4 pass under `node --test` (round-trip, null-token, idempotency flip, lazy `pendingPath`); `require('../notify')` returns without `process.exit()` thanks to the `require.main === module` guard. |

---

## Open questions

1. **AgentMail vs gog as canonical.** Spec27 L29 names AgentMail Drafts + `message.received` webhook;
   this prompt mandates `gog gmail send`. Patch keeps both behind `NOTIFY_TRANSPORT` (default agentmail).
   Which becomes canonical needs a Dais/spec decision before flipping the default — and whether the
   AgentMail path is then retired.
2. **`lateness-guard` semantics beyond the cron.** Disabling `anicca-morning-leave-check` stops the
   un-gated *trigger*, but `~/.openclaw/skills/lateness-guard/scripts/run.sh` itself is reused for
   detection by some flows; confirm nothing else invokes it to send un-gated before relying solely on
   the gated pair.
3. **Reply body extraction.** `gog gmail get` returns the full thread `body` including quoted history;
   `extractApproval` trims+lowercases and matches a leading "ok"/"はい", so a top-posted "OK" works, but
   a reply that only says "OK" *below* quoted text may not match — may need to take the first non-quoted
   line. Confirm against a real Gmail reply before trusting.
4. **Subject-token survival.** If Dais edits the subject and strips `[AN-XXXX]`, matching fails; fallback
   to `In-Reply-To`/`References` headers (available in `gog gmail get` `headers`) is a follow-up.
