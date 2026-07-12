#!/usr/bin/env node
/**
 * mcp-decide.mjs — the loop's tool channel for a `claude -p` brain, as an MCP server.
 *
 * Why (2026-07-13, Dais): we hand-wrote a tool-call envelope into the prompt as text and parsed it
 * ourselves. That was reinventing a wheel we ourselves had already built — blockrun-mcp registers
 * its tools the standard way (`server.registerTool(name, {description, inputSchema: zod}, handler)`),
 * and `claude -p` reads MCP servers via `--mcp-config`. Nothing about the text envelope was ever
 * necessary; it existed because nobody looked.
 *
 * THE ONE SUBTLETY that makes this not a drop-in: under --dangerously-skip-permissions, claude does
 * not merely *choose* a tool — it CALLS it, and the handler runs inside claude's process. The loop's
 * whole design is decide-here / execute-there: the brain returns a decision and the loop's own JS
 * (with the wallet, the caps, the ledger) is what actually spends money. So these handlers must not
 * DO anything. They RECORD the decision to a file and return. The loop reads the file and executes
 * on its own terms. The brain still cannot touch money; it can only say what it wants.
 *
 * Usage (from brain.mjs):
 *   ANICCA_DECISION_FILE=/tmp/x.json node mcp-decide.mjs      # stdio MCP server
 *   claude -p "<prompt>" --mcp-config <cfg.json> --strict-mcp-config
 */
import { writeFileSync } from 'node:fs';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

const DECISION_FILE = process.env.ANICCA_DECISION_FILE;
// The slots this wake is allowed to pick from, passed in by the loop. An enum, not free text — the
// model cannot invent a skill that does not exist, which is the failure the text envelope allowed.
const SLOTS = (process.env.ANICCA_MENU_SLOTS || '').split(',').map((s) => s.trim()).filter(Boolean);

function record(decision) {
  if (!DECISION_FILE) throw new Error('ANICCA_DECISION_FILE not set');
  writeFileSync(DECISION_FILE, JSON.stringify(decision));
}

const server = new McpServer({ name: 'anicca-loop', version: '1.0.0' });

server.registerTool(
  'run_skill',
  {
    description:
      'Choose the ONE skill this instance should run this wake. Recording a choice does not run ' +
      'it — the loop executes it afterwards, with its own spend caps and ledger. Choose the skill ' +
      'most likely to increase this instance net worth.',
    inputSchema: {
      slot: SLOTS.length > 0
        ? z.enum(SLOTS).describe('The skill to run this wake.')
        : z.string().describe('The skill to run this wake.'),
    },
  },
  async ({ slot }) => {
    record({ slot });
    return { content: [{ type: 'text', text: `Decision recorded: ${slot}` }] };
  },
);

server.registerTool(
  'sleep',
  {
    description: 'Do nothing this wake. Choose this only when no available skill can improve things.',
    inputSchema: { reason: z.string().optional().describe('Why nothing is worth doing right now.') },
  },
  async ({ reason }) => {
    record({ slot: null, reason: reason || 'no reason given' });
    return { content: [{ type: 'text', text: 'Decision recorded: sleep' }] };
  },
);

await server.connect(new StdioServerTransport());
