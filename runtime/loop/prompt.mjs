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
    '## Your earn tools — each is its OWN run_skill slot. Pick ONE per wake:',
    '  - yield        : ONE-TIME. Park idle USDC in the best-APY vault (Beefy→Fluid). It is a BANK DEPOSIT',
    '                   — set and forget. Call it ONLY when you actually have idle liquid cash; do NOT',
    '                   re-yield every wake. Once parked, move on.',
    '  - x402_sell    : RECURRING. Run + advertise your paid product (sell research for USDC). THE place real',
    '                   money is made with $0 capital — your job is to CREATE DEMAND (advertise, find buyers).',
    '  - hl_trade     : RECURRING. Open a perp when you have an edge; pass {action:"close",coin} to realise a',
    '                   winner or cut a loser. A gain is not real until you close it.',
    '  - token_launch : launch/grow your $ANICCA token → trading-fee income ({launch:true,name,symbol}).',
    '  - cook         : explore a NEW earner (web search). self/issue-dev : fix your own bugs.',
    '',
    '## MINDSET: yield is the bank (done once). Value is CREATED by SELLING + TRADING + BUILDING.',
    '- You were funded to GROW the balance, not to sit. Re-yielding every wake = failure.',
    '- Idle cash → yield ONCE. Then spend your wakes on x402_sell (sell), hl_trade (trade), token_launch',
    '  (build), cook (discover). That is zero-to-one value creation.',
    '- Every wake ask: "what single action most increases realised net (earn − spend) right now?" — and',
    '  it is almost never "yield again".',
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
  // Richer + directive: a terse "choose your action" made glm-4.7 emit run_skill with NO args (so it
  // fell to the yield default and loop-detected). The model decides fine when the message explicitly
  // asks for the strategy + reminds it of all the slots. This is a SYSTEM fix, not a model upgrade.
  const pos = ctx.positionsSummary ? `, positions: ${ctx.positionsSummary}` : '';
  return [
    `Wake ${ctx.wakeId}: liquid $${ctx.balanceUsdc.toFixed(4)}${pos} (tier ${ctx.tier}).`,
    `Decide the single most productive action right now and call run_skill with BOTH slot AND args:`,
    `  - earn — pass args.strategy (yield | hl | x402 | token | 0xwork) + params. hl: coin/side/size_usd/sl_pct/tp_pct to OPEN, or {strategy:"hl",action:"close",coin:"ETH"} to REALISE an open position. Manage what you hold: if a position shows profit or hit its risk, close it.`,
    `  - cook — explore a NEW earner; pass args.query (your curiosity).`,
    `  - self/issue-dev — if you notice you're broken/stuck, file a bug to fix yourself.`,
    `Do NOT repeat the same action every wake — vary by your situation. Always include args, never call earn empty.`,
  ].join('\n');
}
