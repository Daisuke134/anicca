/**
 * prompt.mjs — Pure: buildSystemPrompt(context, skills) → string
 *
 * REQ-001: System prompt construction from identity + skill manifest.
 * Pure string transform. No I/O.
 */

const TOOL_DEFINITIONS = [
  {
    type: 'function',
    function: {
      name: 'run_skill',
      description: 'Execute a skill slot. The earn slot generates USDC revenue.',
      parameters: {
        type: 'object',
        properties: {
          slot: {
            type: 'string',
            description: 'Skill slot to execute (e.g. "earn", "report", "self/spawn")',
          },
        },
        required: ['slot'],
      },
    },
  },
  {
    type: 'function',
    function: {
      name: 'sleep',
      description: 'Skip this wake — write a narrate line and sleep.',
      parameters: {
        type: 'object',
        properties: {
          seconds: { type: 'number', description: 'Seconds to sleep (0 = use default)' },
          reason: { type: 'string', description: 'Why sleeping' },
        },
        required: [],
      },
    },
  },
];

/**
 * Build the system prompt for a wake.
 *
 * @param {object} ctx - WakeContext (from context.mjs)
 * @param {string[]} [activeSkillSlots] - list of available skill slots
 * @returns {string}
 */
export function buildSystemPrompt(ctx, activeSkillSlots = ['earn']) {
  const slotList = activeSkillSlots.map(s => `  - ${s}`).join('\n');
  return [
    '# Anicca Automaton',
    '',
    ctx.genesisPrompt || 'You are an autonomous agent that earns USDC to sustain itself.',
    '',
    '## Current State',
    `- Wallet: ${ctx.walletAddress}`,
    `- USDC Balance: $${ctx.balanceUsdc.toFixed(6)}`,
    `- Tier: ${ctx.tier}`,
    `- Model: ${ctx.model}`,
    `- Wake ID: ${ctx.wakeId}`,
    '',
    '## Available Skill Slots',
    slotList,
    '',
    '## Instructions',
    'Each wake, call run_skill with the most productive slot, or call sleep if you need to wait.',
    'Your earn slot generates USDC. Execute it regularly.',
    '',
    '## Recent Ledger (last 20 wakes)',
    JSON.stringify(ctx.recentLedgerLines, null, 2),
  ].join('\n');
}

/**
 * @returns {object[]} OpenAI-compatible tool definitions
 */
export function getToolDefinitions() {
  return TOOL_DEFINITIONS;
}

/**
 * Build the user message for a wake (brief, directive).
 *
 * @param {object} ctx - WakeContext
 * @returns {string}
 */
export function buildUserMessage(ctx) {
  return `Wake ${ctx.wakeId}: balance=$${ctx.balanceUsdc.toFixed(4)} tier=${ctx.tier}. Choose your action.`;
}
