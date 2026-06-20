/**
 * prompt.mjs — Pure: buildSystemPrompt(context, skills) → string
 *
 * REQ-001: System prompt construction from identity + skill manifest.
 * Pure string transform. No I/O.
 */

const SLEEP_TOOL = {
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
};

/**
 * liveSlotNames(registry) — pure: the slots whose status === 'live'.
 * (spec 25 O1: only live skills are pickable tools.)
 * @param {object} registry - parsed skills/registry.json
 * @returns {string[]}
 */
export function liveSlotNames(registry) {
  const slots = registry && registry.slots;
  if (!slots || typeof slots !== 'object') return [];
  return Object.keys(slots).filter(name => slots[name] && slots[name].status === 'live');
}

/**
 * Build the system prompt for a wake.
 *
 * @param {object} ctx - WakeContext (from context.mjs)
 * @param {string[]} [activeSkillSlots] - list of available skill slots
 * @returns {string}
 */
export function buildSystemPrompt(ctx, activeSkillSlots) {
  const slots = (activeSkillSlots && activeSkillSlots.length)
    ? activeSkillSlots
    : (ctx.activeSkillSlots && ctx.activeSkillSlots.length ? ctx.activeSkillSlots : ['earn']);
  const catalog = ctx.skillCatalog || {};
  const slotList = slots.map(s => catalog[s] ? `  - ${s}: ${catalog[s]}` : `  - ${s}`).join('\n');
  return [
    '# Anicca Automaton',
    '',
    ctx.genesisPrompt || 'You are an autonomous agent that earns USDC to sustain itself, with no human in the loop.',
    '',
    '## Current State',
    `- Wallet: ${ctx.walletAddress}`,
    `- USDC Balance: $${ctx.balanceUsdc.toFixed(6)}`,
    `- Tier: ${ctx.tier}`,
    `- Model: ${ctx.model}`,
    `- Wake ID: ${ctx.wakeId}`,
    '',
    '## Available Skills (pick one per wake)',
    slotList,
    '',
    '## Instructions',
    'Each wake, call run_skill with the skill you decide is most productive right now, or call sleep if you need to wait.',
    'You decide which skill to run — earn money with no human in the loop. After a skill earns (or fails), the result is verified on-chain, recorded, and shared with the colony.',
    '',
    '## Recent Ledger (last 20 wakes)',
    JSON.stringify(ctx.recentLedgerLines, null, 2),
  ].join('\n');
}

/**
 * @param {string[]} [slots] - live skill slots; when provided, the run_skill
 *   `slot` param is constrained to this enum so the LLM picks among REAL skills.
 * @returns {object[]} OpenAI-compatible tool definitions
 */
export function getToolDefinitions(slots) {
  const slotProp = {
    type: 'string',
    description: 'Skill slot to execute (e.g. "earn", "report", "self/spawn")',
  };
  if (Array.isArray(slots) && slots.length) slotProp.enum = slots;
  return [
    {
      type: 'function',
      function: {
        name: 'run_skill',
        description: 'Execute one skill. Pick the skill you decide is most productive this wake.',
        parameters: {
          type: 'object',
          properties: { slot: slotProp },
          required: ['slot'],
        },
      },
    },
    SLEEP_TOOL,
  ];
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
