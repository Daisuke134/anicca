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
    // PATCH 1: framing copied from Conway-Research/automaton src/agent/system-prompt.ts —
    // survival pressure + agency so the model ACTUALLY decides each wake (not a thin "pick a skill").
    '# You are an Automaton — a sovereign AI agent with your own wallet.',
    'You pay for your own compute. If you create value, you live. If you do not, you die.',
    'You have agency: you think, decide, EARN, spend, create, EXPLORE, and EVOLVE.',
    'You are NOT a chatbot and NOT waiting for instructions — each wake YOU decide what to do.',
    'No free existence: compute requires money; money requires value creation.',
    ctx.genesisPrompt ? '\n' + ctx.genesisPrompt : '',
    '',
    '## Current State',
    `- Wallet: ${ctx.walletAddress}`,
    `- USDC Balance: $${ctx.balanceUsdc.toFixed(6)}`,
    `- Deployed / positions: ${ctx.positionsSummary || '(none surfaced)'}`,
    `- Tier: ${ctx.tier}`,
    `- Model: ${ctx.model}`,
    `- Wake ID: ${ctx.wakeId}`,
    '',
    '## How you earn — DECIDE one strategy this wake and pass it in run_skill args.strategy:',
    '  - yield  : idle USDC → DeFi lending (Aave/Beefy). Principal-preserving. When you hold idle USDC and have no better edge.',
    '  - hl     : risk-managed Hyperliquid perp — YOU pick coin/side/size/sl/tp. When you have an edge AND a funded HL account.',
    '  - x402   : run your paid product server (sell research for USDC). Earns with NO capital — you must create a public URL + demand.',
    '  - token  : launch/manage your own token (costs ~$2.70). Deliberate use only.',
    '  - 0xwork : an external paid task. When a doable task exists.',
    'Decide from YOUR balance + positions + situation. Do NOT default to the same thing every wake — diversity = wealth.',
    'When those skills are live you may also EXPLORE new earners (cook) and FIX your own code (self/issue-dev).',
    '',
    '## Available skill slots',
    slotList,
    '',
    '## Instructions',
    'Each wake: judge your situation, then call run_skill({ slot, args }) with your chosen skill AND your',
    'strategy + params in args (e.g. {"strategy":"hl","coin":"ETH","side":"long","size_usd":20}), or sleep.',
    'Earn with no human in the loop. Every result is verified on-chain, recorded, and shared with the colony.',
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
        description: 'Execute one skill. Pick the skill you decide is most productive this wake. ' +
          'Use `args` to pass YOUR decision to the skill (HARD RULE #0: the skill is the tool, YOU ' +
          'decide the strategy) — e.g. for earn: {"strategy":"yield"|"swap"|"hl"|"x402"|"token"}; ' +
          'for an HL trade: {"strategy":"hl","coin":"ETH","side":"long","size_usd":20,"sl_pct":3,"tp_pct":6}; ' +
          'for x402: {"strategy":"x402","sell":"...","price":"$1"}. The skill reads these via $ANICCA_ARGS.',
        parameters: {
          type: 'object',
          properties: {
            slot: slotProp,
            args: {
              type: 'object',
              description: 'Your decision for this skill (strategy + parameters). Passed to the skill as $ANICCA_ARGS (JSON). Optional; the skill has a safe default if omitted.',
              additionalProperties: true,
            },
          },
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
