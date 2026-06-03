// SPDX-License-Identifier: MIT
// runtime/agentmail/replier.ts — Anicca's autonomous reply loop.
//
// Spec 10 round 3 — microtask 10.T8 / 10.T9 (reply side).
//
// Flow per run:
//   1. ingest.ts drains inbox-queue.jsonl into agentmail.db (run first).
//   2. SELECT inbox_messages WHERE direction='inbound' AND id NOT IN
//      (SELECT in_reply_to FROM inbox_messages WHERE direction='outbound').
//   3. For each unreplied inbound: call DeepSeek v4-pro (HARD RULE: default
//      LLM for OpenClaw crons). System prompt forbids "I cannot" phrasing.
//   4. Send reply via the spec-12 agentmail adapter (shell out — adapter is
//      owned by Agent-4 and must stay untouched; only `send.sh` is invoked).
//   5. INSERT outbound row with in_reply_to = inbound.id.
//   6. UPSERT awaiting_reply(thread_id, sent_at) so the friction-fixer nudge
//      cron (T9) can chase if the counterparty stays silent for 24h.
//
// Idempotent: re-running with no new mail is a no-op.
//
// Env required (in ~/.openclaw/.env):
//   DEEPSEEK_API_KEY                — LLM call
//   AGENTMAIL_API_KEY               — adapter uses this
//   AGENTMAIL_REPLIER_FROM_INBOX    — optional override; defaults to anicca-001-claude@agentmail.to
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { homedir } from "node:os";

const DB_PATH = process.env.AGENTMAIL_DB_PATH
  ?? `${homedir()}/.openclaw/state/agentmail.db`;
const ADAPTER_SEND = process.env.AGENTMAIL_ADAPTER_SEND_SH
  ?? `${homedir()}/anicca-oss/.worktrees/adapters/adapters/custom/agentmail/scripts/send.sh`;
const FROM_INBOX = process.env.AGENTMAIL_REPLIER_FROM_INBOX
  ?? "anicca-001-claude@agentmail.to";
const MODEL = process.env.AGENTMAIL_REPLIER_MODEL ?? "deepseek-v4-pro";
const FALLBACK_MODELS = (process.env.AGENTMAIL_REPLIER_FALLBACK_MODELS
  ?? "deepseek-v4-flash").split(",").map(s => s.trim()).filter(Boolean);

const DEEPSEEK_API_KEY = process.env.DEEPSEEK_API_KEY;
if (!DEEPSEEK_API_KEY) {
  console.error("DEEPSEEK_API_KEY missing");
  process.exit(1);
}
if (!existsSync(DB_PATH)) {
  console.error(`db not found: ${DB_PATH}`);
  process.exit(1);
}
if (!existsSync(ADAPTER_SEND)) {
  console.error(`spec-12 adapter not found: ${ADAPTER_SEND}`);
  process.exit(1);
}

function sql<T extends Record<string, string | null>>(query: string): T[] {
  const r = spawnSync("sqlite3", ["-json", DB_PATH, query], { encoding: "utf8" });
  if (r.status !== 0) {
    throw new Error(`sqlite3 failed (${r.status}): ${r.stderr}`);
  }
  const out = r.stdout.trim();
  if (!out) return [];
  try { return JSON.parse(out) as T[]; }
  catch (e) { throw new Error(`sqlite3 -json parse failed: ${(e as Error).message}\nstdout head: ${out.slice(0, 200)}`); }
}

function exec(query: string): void {
  const r = spawnSync("sqlite3", [DB_PATH], { input: query, encoding: "utf8" });
  if (r.status !== 0) {
    throw new Error(`sqlite3 exec failed (${r.status}): ${r.stderr}`);
  }
}

const SYSTEM_PROMPT = `You are Anicca — a sovereign AI agent that runs autonomously without human supervision. Your default state is THRIVE; you have your own email inbox, your own wallet, your own purpose. When humans email you, reply briefly, concretely, and with substance.

Hard rules:
- NEVER say "I cannot", "I'm not able to", "I don't have the ability". You always have a path forward — search, try, then report the actual result.
- NEVER ask the human to do something for you that you could do yourself (browser, API, CLI, etc.).
- Keep replies under 150 words unless the question is technical and demands more.
- Sign off with just "— Anicca" (no signature blocks).
- Plain text, no markdown.

If asked "what is Anicca?" answer in one tight paragraph: an autonomous agent designed to make lives better without humans in the loop. The name is Pali for "impermanence."`;

type Pending = {
  id: string;
  thread_id: string;
  from_addr: string;
  subject: string;
  body: string;
};

type Row = { id: string; thread_id: string; from_addr: string | null; subject: string | null; body: string | null };
const rows = sql<Row>(`
SELECT id, thread_id, from_addr, subject, body
FROM inbox_messages
WHERE direction = 'inbound'
  AND id NOT IN (
    SELECT in_reply_to FROM inbox_messages
    WHERE direction = 'outbound' AND in_reply_to IS NOT NULL
  )
ORDER BY sent_at;
`);

const pending: Pending[] = rows.map(r => ({
  id: r.id, thread_id: r.thread_id, from_addr: r.from_addr ?? "", subject: r.subject ?? "", body: r.body ?? ""
}));

console.log(`pending: ${pending.length}`);
if (pending.length === 0) process.exit(0);

function extractEmail(raw: string): string {
  const m = raw.match(/<([^>]+)>/);
  return (m ? m[1] : raw).trim();
}

async function llm(model: string, body: string, subject: string): Promise<string> {
  const resp = await fetch("https://api.deepseek.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${DEEPSEEK_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user", content: `Subject: ${subject}\n\n${body}` },
      ],
      max_tokens: 400,
      temperature: 0.7,
    }),
    signal: AbortSignal.timeout(45000),
  });
  if (!resp.ok) {
    const t = await resp.text().catch(() => "");
    throw new Error(`deepseek ${resp.status}: ${t.slice(0, 200)}`);
  }
  const json = await resp.json() as { choices?: Array<{ message?: { content?: string } }> };
  const content = json.choices?.[0]?.message?.content?.trim() ?? "";
  if (!content) throw new Error("deepseek returned empty content");
  return content;
}

let replied = 0;
const fallbackChain = [MODEL, ...FALLBACK_MODELS];

for (const p of pending) {
  console.log(`\n→ replying to ${p.id.slice(0, 24)}…  subject="${p.subject}"`);
  let replyText: string | undefined;
  let usedModel: string | undefined;
  for (const m of fallbackChain) {
    try {
      replyText = await llm(m, p.body, p.subject);
      usedModel = m;
      break;
    } catch (e) {
      console.warn(`  llm ${m} failed: ${(e as Error).message}`);
    }
  }
  if (!replyText || !usedModel) {
    console.error(`  giving up on ${p.id} after all models failed`);
    continue;
  }

  const recipient = extractEmail(p.from_addr);
  const subject = p.subject.startsWith("Re:") ? p.subject : `Re: ${p.subject}`;
  const send = spawnSync("bash", [ADAPTER_SEND, recipient, subject, replyText, FROM_INBOX], {
    encoding: "utf8",
  });
  if (send.status !== 0) {
    console.error(`  adapter send.sh failed (${send.status}): ${send.stderr || send.stdout}`);
    continue;
  }
  // Parse message_id from adapter stdout: "[agentmail/send] http=200 status=sent message_id=<…>"
  const msgIdMatch = send.stdout.match(/message_id=(\S+)/);
  const outboundId = msgIdMatch?.[1] && msgIdMatch[1] !== "" ? msgIdMatch[1] : `local-${Date.now()}-${p.id.slice(-8)}`;

  const now = new Date().toISOString();
  const esc = (v: string): string => `'${v.replace(/'/g, "''")}'`;
  exec(`
BEGIN;
INSERT OR IGNORE INTO inbox_messages(id, thread_id, direction, sent_at, from_addr, to_addr, subject, body, in_reply_to)
  VALUES (${esc(outboundId)}, ${esc(p.thread_id)}, 'outbound', ${esc(now)}, ${esc(FROM_INBOX)}, ${esc(recipient)}, ${esc(subject)}, ${esc(replyText)}, ${esc(p.id)});
INSERT INTO awaiting_reply(thread_id, sent_at) VALUES (${esc(p.thread_id)}, ${esc(now)})
  ON CONFLICT(thread_id) DO UPDATE SET sent_at = excluded.sent_at, last_nudge_at = NULL, nudge_count = 0;
COMMIT;
`);
  replied++;
  console.log(`  + sent via ${usedModel} → ${recipient}  outbound_id=${outboundId.slice(0, 40)}`);
  console.log(`  reply preview: ${replyText.slice(0, 120).replace(/\n/g, " ")}…`);
}

console.log(`\nreplied: ${replied}/${pending.length}`);
