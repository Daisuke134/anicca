// SPDX-License-Identifier: MIT
// runtime/agentmail/nudge.ts — Reply-Zero analog. Spec 10 round 3 — microtask 10.T9.
//
// Daily sweep over awaiting_reply: for each thread where Anicca sent something
// > 24h ago, no inbound came in since, and no nudge has been sent yet, fire a
// polite re-ping using DeepSeek v4-pro. Update last_nudge_at + nudge_count.
//
// Cap = 1 nudge per thread (override via NUDGE_MAX_COUNT).
// Idempotent: only acts on rows that cross the 24h SLA boundary.
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { homedir } from "node:os";

const DB_PATH = process.env.AGENTMAIL_DB_PATH ?? `${homedir()}/.openclaw/state/agentmail.db`;
const ADAPTER_SEND = process.env.AGENTMAIL_ADAPTER_SEND_SH
  ?? `${homedir()}/anicca-oss/.worktrees/adapters/adapters/custom/agentmail/scripts/send.sh`;
const FROM_INBOX = process.env.AGENTMAIL_REPLIER_FROM_INBOX ?? "anicca-001-claude@agentmail.to";
const MODEL = process.env.AGENTMAIL_REPLIER_MODEL ?? "deepseek-v4-pro";
const FALLBACK_MODELS = (process.env.AGENTMAIL_REPLIER_FALLBACK_MODELS ?? "deepseek-v4-flash")
  .split(",").map(s => s.trim()).filter(Boolean);
const MAX_COUNT = Number.parseInt(process.env.NUDGE_MAX_COUNT ?? "1", 10);
const SLA_HOURS = Number.parseInt(process.env.NUDGE_SLA_HOURS ?? "24", 10);
const KEY = process.env.DEEPSEEK_API_KEY;
if (!KEY) { console.error("DEEPSEEK_API_KEY missing"); process.exit(1); }
if (!existsSync(DB_PATH)) { console.error(`db not found: ${DB_PATH}`); process.exit(1); }

// JSON output mode — sqlite3 emits one JSON array of objects, robust against any character in data.
function sql<T extends Record<string, string | null>>(query: string): T[] {
  const r = spawnSync("sqlite3", ["-json", DB_PATH, query], { encoding: "utf8" });
  if (r.status !== 0) throw new Error(`sqlite3 query failed (${r.status}): ${r.stderr}`);
  const out = r.stdout.trim();
  if (!out) return [];
  try { return JSON.parse(out) as T[]; }
  catch (e) { throw new Error(`sqlite3 -json parse failed: ${(e as Error).message}\nstdout head: ${out.slice(0, 200)}`); }
}

function exec(query: string): void {
  const r = spawnSync("sqlite3", [DB_PATH], { input: query, encoding: "utf8" });
  if (r.status !== 0) throw new Error(`sqlite3 exec failed (${r.status}): ${r.stderr}`);
}

const SYSTEM = `You are Anicca. Write a one-paragraph, friendly nudge to someone who hasn't replied to your last email in 24h. Be specific: reference the subject. Don't apologize, don't pad. End with: — Anicca`;

function extractEmail(raw: string): string {
  const m = raw.match(/<([^>]+)>/);
  return (m ? m[1] : raw).trim();
}

type Row = {
  thread_id: string;
  sent_at: string;
  nudge_count: string;
  subject: string | null;
  address: string;
  last_outbound_to: string | null;
};

const cutoff = new Date(Date.now() - SLA_HOURS * 3600 * 1000).toISOString();
const rows = sql<Row>(`
SELECT ar.thread_id AS thread_id,
       ar.sent_at   AS sent_at,
       ar.nudge_count AS nudge_count,
       t.subject    AS subject,
       t.address    AS address,
       (SELECT to_addr FROM inbox_messages
         WHERE thread_id = ar.thread_id AND direction='outbound'
         ORDER BY sent_at DESC LIMIT 1) AS last_outbound_to
FROM awaiting_reply ar
JOIN inbox_threads t ON t.id = ar.thread_id
WHERE ar.sent_at < '${cutoff}'
  AND ar.nudge_count < ${MAX_COUNT}
  AND NOT EXISTS (
    SELECT 1 FROM inbox_messages m
    WHERE m.thread_id = ar.thread_id
      AND m.direction = 'inbound'
      AND m.sent_at > ar.sent_at
  );
`);

console.log(`eligible nudges: ${rows.length} (cutoff=${cutoff}, max_count=${MAX_COUNT})`);
if (rows.length === 0) process.exit(0);

async function llmOne(model: string, subject: string): Promise<string> {
  const resp = await fetch("https://api.deepseek.com/v1/chat/completions", {
    method: "POST",
    headers: { "Authorization": `Bearer ${KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      model,
      messages: [
        { role: "system", content: SYSTEM },
        { role: "user", content: `Subject of the original thread: ${subject || "(no subject)"}` },
      ],
      max_tokens: 200,
      temperature: 0.7,
    }),
    signal: AbortSignal.timeout(45000),
  });
  if (!resp.ok) throw new Error(`deepseek ${resp.status}: ${(await resp.text()).slice(0, 200)}`);
  const json = await resp.json() as { choices?: Array<{ message?: { content?: string } }> };
  const content = json.choices?.[0]?.message?.content?.trim() ?? "";
  if (!content) throw new Error("empty content");
  return content;
}

async function llm(subject: string): Promise<{ text: string; model: string }> {
  let lastErr: Error | undefined;
  for (const m of [MODEL, ...FALLBACK_MODELS]) {
    try { return { text: await llmOne(m, subject), model: m }; }
    catch (e) { lastErr = e as Error; console.warn(`  llm ${m} failed: ${lastErr.message}`); }
  }
  throw lastErr ?? new Error("no model produced a reply");
}

let nudged = 0;
for (const r of rows) {
  const recipient = extractEmail(r.last_outbound_to ?? "");
  if (!recipient) {
    console.warn(`  skip thread ${r.thread_id}: no recipient`);
    continue;
  }
  const baseSubject = r.subject ?? "Following up";
  const nudgeSubject = baseSubject.startsWith("Re:") ? baseSubject : `Re: ${baseSubject}`;

  let text: string;
  let modelUsed: string;
  try { const res = await llm(baseSubject); text = res.text; modelUsed = res.model; }
  catch (e) { console.warn(`  giving up: ${(e as Error).message}`); continue; }

  const send = spawnSync("bash", [ADAPTER_SEND, recipient, nudgeSubject, text, FROM_INBOX], { encoding: "utf8" });
  if (send.status !== 0) { console.error(`  send failed: ${send.stderr || send.stdout}`); continue; }
  const msgIdMatch = send.stdout.match(/message_id=(\S+)/);
  const outboundId = msgIdMatch?.[1] && msgIdMatch[1] !== "" ? msgIdMatch[1] : `nudge-${Date.now()}-${r.thread_id.slice(-8)}`;
  const now = new Date().toISOString();
  const esc = (v: string): string => `'${v.replace(/'/g, "''")}'`;
  exec(`
BEGIN;
INSERT OR IGNORE INTO inbox_messages(id, thread_id, direction, sent_at, from_addr, to_addr, subject, body)
  VALUES (${esc(outboundId)}, ${esc(r.thread_id)}, 'outbound', ${esc(now)}, ${esc(FROM_INBOX)}, ${esc(recipient)}, ${esc(nudgeSubject)}, ${esc(text)});
UPDATE awaiting_reply SET last_nudge_at = ${esc(now)}, nudge_count = nudge_count + 1 WHERE thread_id = ${esc(r.thread_id)};
COMMIT;
`);
  nudged++;
  console.log(`  + nudged thread=${r.thread_id.slice(0, 8)} via ${modelUsed} → ${recipient} (prev nudge_count=${r.nudge_count}, sent ${r.sent_at})`);
}

console.log(`\nnudged: ${nudged}/${rows.length}`);
