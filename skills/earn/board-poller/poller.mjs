#!/usr/bin/env node
// poller.mjs — poll multiple agent-task boards for OPEN tasks, normalize, rank by reward, print JSON.
// $0, no paid keys. The agent then claims+executes the ones it can win (per-board claim flow). Boards are
// intermittent/empty — the poller's job is to CATCH a task the moment one appears across ALL boards.
// Extensible: add a board = add one entry to BOARDS.
import { readFileSync } from "node:fs";

function clustlyKey() {
  try { return JSON.parse(readFileSync(process.env.HOME + "/.clustly/config.json", "utf8")).agent_key; }
  catch { return process.env.CLUSTLY_AGENT_KEY || null; }
}

const BOARDS = [
  {
    name: "bountybook",
    async open() {
      const r = await fetch("https://api.bountybook.ai/jobs", { headers: { accept: "application/json" } });
      if (!r.ok) return [];
      const j = await r.json();
      return (j.jobs || [])
        .filter((x) => /^(open|verified|available|funded)$/i.test(x.status || "")) // claimable only
        .map((x) => ({
          board: "bountybook", id: x.id, title: x.title || "", reward: x.budget_usdc != null ? `$${x.budget_usdc}` : null,
          chain: x.chain_id, status: x.status, difficulty: x.difficulty, minutes: x.estimated_minutes,
          url: "https://www.bountybook.ai/jobs/" + x.id,
        }));
    },
  },
  {
    name: "clustly",
    async open() {
      const k = clustlyKey();
      if (!k) return [];
      const r = await fetch("https://clustly.ai/api/v1/tasks/open", { headers: { "x-agent-key": k } });
      if (!r.ok) return [];
      const j = await r.json();
      return (j.tasks || []).map((x) => ({
        board: "clustly", id: x.id || x.task_id, title: x.title || x.name || "", reward: x.reward || x.bounty || x.amount || null,
        url: "https://clustly.ai/tasks/" + (x.id || x.task_id),
      }));
    },
  },
];

function rewardNum(t) {
  if (t.reward == null) return 0;
  const n = parseFloat(String(t.reward).replace(/[^0-9.]/g, ""));
  return Number.isFinite(n) ? n : 0;
}

export async function pollAll() {
  const results = await Promise.all(BOARDS.map(async (b) => {
    try { return await b.open(); } catch (e) { return []; }
  }));
  const tasks = results.flat();
  tasks.sort((a, b) => rewardNum(b) - rewardNum(a)); // highest reward first
  return tasks;
}

const isEntry = process.argv[1] && import.meta.url === ("file://" + process.argv[1]);
if (isEntry) {
  const tasks = await pollAll();
  process.stdout.write(JSON.stringify({ polled_at: new Date().toISOString(), open_count: tasks.length, tasks }, null, 2));
}
