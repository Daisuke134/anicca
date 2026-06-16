# Patch: life-notify — close the reply→send loop with a gog-Gmail approval round-trip

Subsystem: **life-notify** (B-notify). Spec: `27-launch-workflow-and-ubi.md` L29 (B-notify, メール承認) + `07-life-manager.md`.
Mother repo target: `~/anicca/skills/life/notify/notify.js` (OSS skill body).
Status: PATCH FILE ONLY — no commit, no push, no real email sent.

---

## Gaps

Evidence is RAW from the live tree (`~/anicca/skills/life/notify/notify.js`,
`~/anicca-project/apps/landing/netlify/functions/life-notify.js`,
`~/.openclaw/cron/jobs.json`, `~/.openclaw/.env`).

| # | Gap | RAW evidence | Severity |
|---|-----|--------------|----------|
| G1 | **Reply→send loop is NOT wired.** `webhook` mode exists but only runs when a human passes `--draftId` + `--reply` by hand. Nothing polls the inbox, finds Dais's "OK" reply, and correlates it back to the held draft. So the round-trip never closes autonomously. | `notify.js:16` `node notify.js webhook --draftId <id> --reply <text>`; `notify.js:352-362` parses `--draftId`/`--reply` from argv and throws if absent. No inbox poll/webhook subscription exists in the skill. | **BLOCKING** |
| G2 | **Mandated transport mismatch.** Prompt + spec context require `gog gmail send --account keiodaisuke@gmail.com`. The skill uses AgentMail REST for BOTH the approval email and the stakeholder send (`messages/send`, `drafts`). | `notify.js` `AGENTMAIL_BASE = "https://api.agentmail.to/v0"`; `sendAgentMailEmail` POSTs `/messages/send`; `saveAgentMailDraft` POSTs `/drafts`. No `gog gmail send` call anywhere in the skill. | **BLOCKING** |
| G3 | **`OWNER_EMAIL` is undefined in env.** Code falls back to `GOG_ACCOUNT` then a hardcoded string, but the documented required var is missing. | `grep -c '^OWNER_EMAIL=' ~/.openclaw/.env` → `0`. Present: `GOG_ACCOUNT`, `GOOGLE_LOGIN_EMAIL`, `AGENTMAIL_API_KEY`, `AGENTMAIL_INBOX_ID`, `AGENTMAIL_WEBHOOK_SECRET`. | HIGH |
| G4 | **No cron trigger for scan mode.** The only live late-detection cron is `lateness-guard`, which sends to the stakeholder **directly via `gog gmail send` with NO approval gate** — the opposite of B-notify's design. | `jobs.json:3342` `bash ~/.openclaw/skills/lateness-guard/scripts/run.sh` … `attendees present -> email them via: gog gmail send -a keiodaisuke@gmail.com --to <email>`. No `notify` job in `jobs.json` (`grep -n notify` → only line 3342, which is lateness-guard). | HIGH |
| G5 | **No test-stakeholder safety override.** Stakeholder address comes straight from GCal `event.attendees`, so any test of the round-trip would email a real third party. No env to redirect the send to a test address. | `notify.js` `attendeeEmails = attendees.map((a) => a.email)`; `draftTo = attendeeEmails.length > 0 ? attendeeEmails.join(",") : OWNER_EMAIL`. No `NOTIFY_TEST_STAKEHOLDER` / dry-run guard. | MEDIUM |
| G6 | **No durable draft↔event store for the gog path.** The AgentMail path leans on AgentMail Drafts to hold the pending send. If we move to gog Gmail (G2), there is no place to persist `{ token → stakeholderTo, subject, body }` so the later reply can resolve what to send. | AgentMail-only persistence: `getAgentMailDraft(draftId)` is the sole retrieval path. | HIGH |

**Net:** detection logic + approval-email composition + `extractApproval` parsing are real and unit-tested
(`skills/life/notify/__tests__/notify-logic.test.js`). What is missing is (a) a Gmail-native transport
and (b) the autonomous inbound poll that closes "Dais replies OK → stakeholder gets the mail".

---

## Diff

Adds a self-contained gog-Gmail round-trip alongside the existing AgentMail path, selected by
`NOTIFY_TRANSPORT=gog` (default `agentmail` to preserve current behaviour). New `poll` mode reads
the owner inbox, matches the approval token, and sends the held message to the stakeholder via
`gog gmail send`. Pending sends are persisted to a local JSONL so the reply can resolve them.

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
+// Durable store of pending approvals for the gog path (token -> {to,subject,body}).
+const PENDING_PATH = path.join(
+  process.env.HOME || "/root", ".openclaw", "state", "life-notify-pending.jsonl"
+);

 // ── Pure logic (mirrors notify-logic.js in the Netlify function) ─────────────
+
+// Short, mailbox-searchable token embedded in the approval email subject so a
+// later reply (which carries "Re: <subject>") can be matched back to its draft.
+function approvalToken(seed) {
+  return "AN-" + require("crypto").createHash("sha1")
+    .update(String(seed) + ":" + Date.now()).digest("hex").slice(0, 8).toUpperCase();
+}
+
+function appendPending(rec) {
+  fs.mkdirSync(path.dirname(PENDING_PATH), { recursive: true });
+  fs.appendFileSync(PENDING_PATH, JSON.stringify(rec) + "\n");
+}
+
+function findPending(token) {
+  if (!fs.existsSync(PENDING_PATH)) return null;
+  const lines = fs.readFileSync(PENDING_PATH, "utf8").trim().split("\n").filter(Boolean);
+  for (const l of lines) {
+    try { const r = JSON.parse(l); if (r.token === token && !r.sent) return r; } catch {}
+  }
+  return null;
+}
+
+function markSent(token) {
+  if (!fs.existsSync(PENDING_PATH)) return;
+  const lines = fs.readFileSync(PENDING_PATH, "utf8").trim().split("\n").filter(Boolean);
+  const out = lines.map((l) => {
+    try { const r = JSON.parse(l); if (r.token === token) r.sent = true; return JSON.stringify(r); }
+    catch { return l; }
+  });
+  fs.writeFileSync(PENDING_PATH, out.join("\n") + "\n");
+}
+
+// ── gog Gmail transport ──────────────────────────────────────────────────────
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
+// Read recent inbox messages via gog and return [{from,subject,snippet}].
+function gogGmailRecent(query) {
+  const raw = execFileSync(GOG_BIN, [
+    "gmail", "list", "-j",
+    "--account", GOG_ACCOUNT,
+    "--query", query,
+    "--max", "20",
+  ], { env: gogEnv(), timeout: 60000 }).toString();
+  const d = JSON.parse(raw);
+  return Array.isArray(d) ? d : (d.messages || d.items || []);
+}
@@
 const [, , mode = "scan", ...rest] = process.argv;

 (async () => {
   try {
-    if (mode === "webhook") {
+    if (mode === "webhook") {
       await runWebhook(rest);
+    } else if (mode === "poll") {
+      await runPoll();
     } else {
       await runScan();
     }
```

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

### New `runPoll` (closes G1 for the gog path)

```diff
+async function runPoll() {
+  // Find Dais's replies to our approval mails. They arrive as "Re: ... [AN-XXXX]".
+  const msgs = gogGmailRecent('from:' + OWNER_EMAIL + ' subject:"[Anicca] Late alert" newer_than:1d');
+  const sent = [];
+  for (const m of msgs) {
+    const subj = m.subject || "";
+    const tok = (subj.match(/\[(AN-[0-9A-F]{8})\]/) || [])[1];
+    if (!tok) continue;
+    if (!extractApproval(m.snippet || m.body || subj)) continue;  // require "OK"
+    const pending = findPending(tok);
+    if (!pending) continue;                                       // unknown/already-sent
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
+  approvalToken, appendPending, findPending, markSent,
 };
```

Also add to `~/.openclaw/.env` (G3):

```
OWNER_EMAIL=keiodaisuke@gmail.com
```

And register the two cron entries (G4) in `~/.openclaw/cron/jobs.json` — scan every 10 min during
the day, poll every 5 min:

```
{ "id": "anicca-life-notify-scan", "schedule": "*/10 8-22 * * *",
  "exec": "NOTIFY_TRANSPORT=gog node ~/anicca/skills/life/notify/notify.js scan" }
{ "id": "anicca-life-notify-poll", "schedule": "*/5 8-22 * * *",
  "exec": "NOTIFY_TRANSPORT=gog node ~/anicca/skills/life/notify/notify.js poll" }
```

---

## Commands (safe round-trip test — NO real third party emailed)

All sends point at a test stakeholder address via `NOTIFY_TEST_STAKEHOLDER`, so the only real
recipients are Dais's own inbox (approval) and the test address (stakeholder). Use a Gmail alias
you control, e.g. `keiodaisuke+notifytest@gmail.com`.

```bash
set -a; . ~/.openclaw/.env; set +a
export OWNER_EMAIL=keiodaisuke@gmail.com
export NOTIFY_TRANSPORT=gog
export NOTIFY_TEST_STAKEHOLDER='keiodaisuke+notifytest@gmail.com'   # redirect stakeholder send

# 0. Unit tests for the new pure helpers (no email).
node --test ~/anicca/skills/life/notify/__tests__/notify-logic.test.js

# 1. Seed a late-risk in GCal: a "[Travel] LunchTest" block starting 10 min ago + a
#    "LunchTest" event with attendee = the test address, so detection fires.
gog calendar events create -a keiodaisuke@gmail.com --summary "[Travel] LunchTest" \
  --start "$(date -v-10M +%FT%T)" --end "$(date +%FT%T)"
gog calendar events create -a keiodaisuke@gmail.com --summary "LunchTest" \
  --start "$(date -v+30M +%FT%T)" --end "$(date -v+90M +%FT%T)" \
  --attendee "keiodaisuke+notifytest@gmail.com"

# 2. SCAN: detects late risk, writes pending JSONL, emails the APPROVAL to OWNER via gog.
node ~/anicca/skills/life/notify/notify.js scan
#   expect: {"ok":true,...,"alerted":[{"event":"LunchTest","token":"AN-XXXXXXXX",...}]}
cat ~/.openclaw/state/life-notify-pending.jsonl   # token row, sent:false

# 3. Dais replies "OK" — simulate the human reply by sending to OWN inbox with the
#    SAME subject (Re: ... [AN-XXXX]) so the poller can match it. (Token from step 2.)
TOKEN=AN-XXXXXXXX
gog gmail send -a keiodaisuke@gmail.com --to keiodaisuke@gmail.com \
  --subject "Re: [Anicca] Late alert for \"LunchTest\" — reply OK to notify [$TOKEN]" \
  --body "OK"

# 4. POLL: finds the OK reply, matches the token, sends to the TEST stakeholder via gog.
node ~/anicca/skills/life/notify/notify.js poll
#   expect: {"ok":true,"mode":"poll","sent":[{"token":"AN-XXXXXXXX","to":"keiodaisuke+notifytest@gmail.com"}]}

# 5. Confirm the stakeholder mail actually landed (in the +notifytest alias).
gog gmail list -a keiodaisuke@gmail.com --query 'subject:"Update re \"LunchTest\"" newer_than:1h'

# 6. Idempotency: re-run poll → sent:[] (pending row now sent:true).
node ~/anicca/skills/life/notify/notify.js poll

# Cleanup: delete the two test GCal events + truncate the pending JSONL.
```

---

## Acceptance

| # | Criterion | Verify |
|---|-----------|--------|
| A1 | Approval email reaches Dais (Gmail, via `gog gmail send`). | Step 2 `alerted[].token` returned + approval mail in `keiodaisuke@gmail.com` with `[AN-XXXX]` in subject. |
| A2 | Dais's "OK" reply is received and correctly matched to its pending draft. | Step 4 `poll` output `sent[].token` == token from step 2; non-"OK" replies leave `sent:[]`. |
| A3 | Stakeholder email is actually sent (to the **test** address, not a real third party). | Step 5 lists `Update re "LunchTest"` in `+notifytest` alias. |
| A4 | Fully email — no Telegram, no manual `--draftId` hand-off; the loop closes via inbox poll. | scan→poll runnable headless by cron (G4 entries); no Telegram call in diff. |
| A5 | Idempotent + safe. | Step 6 re-poll → `sent:[]`; with `NOTIFY_TEST_STAKEHOLDER` set, no real attendee is ever emailed. |

---

## Open questions

1. **AgentMail vs gog as canonical.** Spec27 L29 names AgentMail Drafts + `message.received` webhook;
   this prompt mandates `gog gmail send`. Patch keeps both behind `NOTIFY_TRANSPORT` (default agentmail).
   Which becomes canonical needs a Dais/spec decision before flipping the default.
2. **Overlap with the live `lateness-guard` cron** (`jobs.json:3342`), which already sends late notices
   via `gog gmail send` **without an approval gate**. B-notify's gate should likely replace it — but that
   is a removal of a live cron and is out of scope for this patch file.
3. **`gog gmail list` JSON shape** (`--query`, `-j`, snippet/body fields) is assumed from `gog 0.17.0`;
   `gogGmailRecent` parsing must be confirmed against real output before the poller is trusted.
4. **Reply-matching robustness.** Token-in-subject is used because Gmail threads `Re:`; if Dais strips
   the subject token, fall back to `In-Reply-To`/`References` header matching (needs `gog` header access).
