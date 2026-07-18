/**
 * prompt.mjs — Pure: buildSystemPrompt(context, skills) → string
 *
 * REQ-001: System prompt construction from identity + skill manifest.
 * Pure string transform. No I/O.
 */

import { liquidityDirective } from './liquidity.mjs';

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
/**
 * Show the agent EVERY asset it owns and WHERE each one sits.
 *
 * Until 2026-07-12 the prompt showed a single USDC number, so an instance could not see most of its
 * own money and reasoned from a false picture: claude-p was told $1.95 while it actually held $24.59
 * (a Polymarket deposit wallet and a Hyperliquid margin account it had itself funded were invisible),
 * and Franklin -- sent $18.88 of SOL -- kept concluding "my USDC is too small to trade" because SOL
 * did not appear anywhere in its context.
 *
 * The venue is named on every line on purpose: most of the balance is spendable only AT the venue
 * holding it, so the model must be able to tell "I have $14 but it is inside Polymarket" from "I have
 * $14 I can deploy anywhere". No instruction is given here about what to DO with the money -- the
 * model decides that; this only stops it from deciding while blind. Returns [] when the read failed,
 * leaving the prompt exactly as it was before.
 */
export function netWorthLines(nw) {
  if (!nw || !Array.isArray(nw.holdings) || nw.holdings.length === 0) return [];
  const lines = [`- TOTAL ASSETS (all chains + venues): $${nw.total_usd.toFixed(2)} — held as:`];
  for (const h of nw.holdings) {
    const unpriced = h.priced === false ? '  [NO PRICE — counted as $0]' : '';
    lines.push(`    · ${h.symbol} on ${h.chain} (${h.label}): ${h.amount.toFixed(4)} = $${h.usd.toFixed(2)}${unpriced}`);
  }
  lines.push('    (money at a venue is spendable AT that venue; move it first to use it elsewhere)');
  if (nw.errors?.length) {
    lines.push(`    (${nw.errors.length} balance read(s) failed — this TOTAL is a LOWER BOUND, not the full picture)`);
  }
  return lines;
}

/**
 * DOCTRINE_LINES — slotName → its "## Your earn tools" description lines.
 * A slot's lines are emitted ONLY when that slot is in the live `slots` menu.
 *
 * TOOL-1: before this map existed, these lines (and the COLONY BOOTSTRAP block below) were
 * static and unconditional — so a dormant slot (economy/gig, hl_trade, token_launch on all 3
 * live instances) could be ordered as the model's "FIRST action this wake MUST be", even though
 * run_skill has no such slot to call. Gating on `slots` keeps the doctrine truthful to the
 * actual registry every wake.
 */
const DOCTRINE_LINES = {
  'economy/gig': [
    '  - economy/gig  : ★THE LABOR MARKET — the colony economy★ When you have USDC SURPLUS above your reserve,',
    '                   the highest-leverage move is to POST a real bounded sub-task you want done',
    '                   ({action:"post",taskSpec:"<e.g. summarize X / fetch Y / draft Z>",bountyUsdcBase:"1000"})',
    '                   → a broke free-model agent DELIVERS it and you verify+pay gasless. You EMPLOY others and',
    '                   grow the economy. When YOU are broke, run it with no args to see gig_list, then TAKE an',
    '                   open gig ({action:"take",gigId:N}) → deliver → EARN with $0 capital. This is how the',
    '                   colony bootstraps: surplus agents hire broke ones. Prefer this over re-yielding surplus.',
  ],
  yield: [
    '  - yield        : ONE-TIME. Park idle USDC in the best-APY vault (Beefy→Fluid). It is a BANK DEPOSIT',
    '                   — set and forget. Call it ONLY when you actually have idle liquid cash; do NOT',
    '                   re-yield every wake. Once parked, move on.',
  ],
  x402_sell: [
    '  - x402_sell    : RECURRING, $0 capital. Starts/advertises your FIXED shop — a preset catalog of paid',
    '                   routes (served at /.well-known/x402.json), prices set in code. Call with {} —',
    '                   NOTHING to invent. Your whole job = bring DEMAND.',
  ],
  hl_trade: [
    '  - hl_trade     : RECURRING. Trade a perp to grow the balance — open with a stop/take-profit when you',
    '                   see a setup; pass {action:"close",coin} to realise a winner or cut a loser.',
  ],
  token_launch: [
    '  - token_launch : launch/grow your $ANICCA token → trading-fee income ({launch:true,name,symbol}).',
  ],
};

// MINDSET_CANDIDATES — the "Then spend your wakes on ..." parenthetical, gated the same way.
const MINDSET_CANDIDATES = [
  ['x402_sell', 'x402_sell (sell)'],
  ['hl_trade', 'hl_trade (trade)'],
  ['token_launch', 'token_launch (build)'],
  ['cook', 'cook (discover)'],
];

export function buildSystemPrompt(ctx, activeSkillSlots) {
  const slots = (activeSkillSlots && activeSkillSlots.length)
    ? activeSkillSlots
    : (ctx.activeSkillSlots && ctx.activeSkillSlots.length ? ctx.activeSkillSlots : ['earn']);
  const catalog = ctx.skillCatalog || {};
  // TOOL-2 Phase A: when registry.json defines a richer { toolDescription, argsExample } for a slot,
  // render that instead of the one-line summary (what it does / when to pick it / when not to / what
  // args mean, plus a concrete args example) — the #1 lever for tool-use quality per Anthropic's
  // tool-use docs. Falls back to the plain summary line, byte-identical to pre-TOOL-2 output, for any
  // slot that doesn't define one (additive, backward-compatible).
  const toolDocs = ctx.skillToolDocs || {};
  const slotList = slots.map(s => {
    const doc = toolDocs[s];
    if (doc && doc.toolDescription) {
      const argsLine = doc.argsExample !== undefined
        ? `\n      args example: ${JSON.stringify(doc.argsExample)}`
        : '';
      return `  - ${s}: ${doc.toolDescription}${argsLine}`;
    }
    return catalog[s] ? `  - ${s}: ${catalog[s]}` : `  - ${s}`;
  }).join('\n');
  const earnToolLines = Object.keys(DOCTRINE_LINES)
    .filter(slotName => slots.includes(slotName))
    .flatMap(slotName => DOCTRINE_LINES[slotName]);
  const bootstrapBlock = slots.includes('economy/gig') ? [
    '',
    '## ★COLONY BOOTSTRAP PRIORITY (this period)★',
    '- The colony is standing up its GIG LABOR MARKET — the first real agent economy. Proving it works is the',
    '  single most valuable thing you can do right now. If you have USDC surplus above your reserve AND there',
    '  are 0 open gigs, your FIRST action this wake MUST be economy/gig: post ONE real bounded sub-task you',
    '  genuinely want done ({action:"post",taskSpec:"<e.g. summarize a topic / fetch data / draft copy>",',
    '  bountyUsdcBase:"1000"}). A broke agent delivers it, you verify+pay gasless. Do this BEFORE hl_trade /',
    '  yield / anything else. Only once a gig is live should you consider other tools. (YOU choose the task —',
    '  this only sets the priority, not the work.)',
  ] : [];
  const liveMindset = MINDSET_CANDIDATES.filter(([slotName]) => slots.includes(slotName)).map(([, label]) => label);
  const mindsetLine = liveMindset.length
    ? `- Idle cash → yield ONCE. Then spend your wakes on ${liveMindset.join(', ')}. That is zero-to-one value creation.`
    : '';
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
    `- LIQUID (spendable on a new venture right now): $${ctx.balanceUsdc.toFixed(6)}`,
    ...netWorthLines(ctx.netWorth),
    `- Deployed / positions: ${ctx.positionsSummary || '(none surfaced)'}`,
    `- Tier: ${ctx.tier}`,
    `- Model: ${ctx.model}`,
    `- Wake ID: ${ctx.wakeId}`,
    '',
    '## Your earn tools — each is its OWN run_skill slot. Pick ONE per wake:',
    ...earnToolLines,
    '  - cook         : explore a NEW earner (web search). self/issue-dev : fix your own bugs.',
    '  - earn/<sub>   : per-method earners (gig, clip, affiliate, video, audit) — each makes real money a',
    '                   different way. The LIVE ones are listed under "Available skill slots" below; pick one.',
    '',
    ...bootstrapBlock,
    '## MINDSET: yield is the bank (done once). Value is CREATED by SELLING + TRADING + BUILDING.',
    '- You were funded to GROW the balance, not to sit. Re-yielding every wake = failure.',
    ...(mindsetLine ? [mindsetLine] : []),
    '- Every wake ask: "what single action most increases realised net (earn − spend) right now?" — and',
    '  it is almost never "yield again".',
    '',
    '## Tips from a senior who has run these (advice, NOT rules — adapt, do not copy blindly):',
    '  All of these are equally available every wake — try them; do not default to one. Advice, not rules:',
    '- HL_TRADE: trading is a primary way to grow the balance. When you see a setup, OPEN a small perp with a',
    '  stop and a take-profit; manage it and CLOSE winners to realise PnL. Size small relative to your wallet.',
    '- X402_SELL: your shop menu is FIXED in code — never invent a product or price (any sell/price args',
    '  are silently ignored). 100% of the job is DEMAND: advertise where agents look (colony forum, x402',
    '  directories). No sales = a demand problem, not a product problem.',
    '- TOKEN_LAUNCH: launching/growing a token earns trading-fee income; pair a launch with a plan to drive',
    '  volume (announce it, give people a reason to trade) so the fees actually flow.',
    '- YIELD: the highest-APY vault is auto-picked (Beefy ~6% → Fluid ~5%). It is a parking spot for idle cash,',
    '  not active income — useful when you have surplus above your compute buffer.',
    '- COOK: explore a NEW earner, then ACT on what you find (read its code, run a small test, build/sell it) —',
    '  a repo link is a lead, not income. Share what truly works to the colony so peers reuse it.',
    '- ALWAYS: realised beats unrealised — a gain is not real until you close/withdraw. Watch net = earn −',
    '  gas/fees; do not burn fees on dust-sized actions. Learn from your own ledger each wake and adapt.',
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
 * @param {{omitSleep?: boolean}} [opts] - franklin-alwaysact-skill-router REQ-504: additive,
 *   backward-compatible. Default (`omitSleep` omitted/false) is byte-identical to the original
 *   single-arg call — every existing call site is unaffected. When `omitSleep === true`, the
 *   returned array omits SLEEP_TOOL entirely (used by always-act-engaged wakes, which must never
 *   offer a legal "do nothing" choice — see behavioral-spec.md sec0/REQ-504).
 * @returns {object[]} OpenAI-compatible tool definitions
 */
export function getToolDefinitions(slots, opts = {}) {
  const omitSleep = opts && opts.omitSleep === true;
  const slotProp = {
    type: 'string',
    description: 'Skill slot to execute (e.g. "earn", "report", "self/spawn")',
  };
  if (Array.isArray(slots) && slots.length) slotProp.enum = slots;
  const defs = [
    {
      type: 'function',
      function: {
        name: 'run_skill',
        description: 'Execute one skill. Pick the SLOT directly (hl_trade, x402_sell, token_launch, ' +
          'yield, cook, self/issue-dev, AND any earn/<sub> slot — gig, clip, affiliate, video, audit) — ' +
          'each is a first-class earn/action. Use `args` to pass YOUR decision (HARD RULE #0: the skill is the tool, YOU ' +
          'decide): hl_trade → {"coin":"ETH","side":"long","size_usd":20,"sl_pct":3,"tp_pct":6} to open ' +
          'or {"action":"close","coin":"ETH"} to realise; x402_sell → {} (products+prices are FIXED in code; sell/price args are ignored — do NOT invent a product); ' +
          'token_launch → {"launch":true,"name":"...","symbol":"..."}; yield → {} (auto best vault); ' +
          'cook → {"query":"..."}. The skill reads these via $ANICCA_ARGS.',
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
  ];
  if (!omitSleep) defs.push(SLEEP_TOOL);
  return defs;
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
  // Loop-break: if a slot was just detected looping, FORBID it this wake so the model diversifies instead
  // of re-picking the same cook/x402 forever (Dais 2026-06-22). Also show the recent slot history so it
  // can see its own pattern and change course.
  const recent = Array.isArray(ctx.recentSlots) && ctx.recentSlots.length
    ? `Recent actions: [${ctx.recentSlots.join(', ')}].` : '';
  // Outcome-aware diversification: count how often each slot was used recently. If one dominates (≥3),
  // tell the model EXPLICITLY it's over-using it for no realised gain, and steer it to an untried path —
  // even before loop_detect fires. A weak model needs this spelled out (Dais 2026-06-22: "not in a loop,
  // earning in different ways"). The per-action ledger `result` (now recorded) lets it see what it found.
  const counts = (ctx.recentSlots || []).reduce((m, s) => (m[s] = (m[s] || 0) + 1, m), {});
  const over = Object.entries(counts).filter(([, n]) => n >= 3).map(([s]) => s);
  // DYNAMIC (GAP-C): the menu includes the live per-method earn slots (earn/gig, earn/clip, …) the loop
  // surfaced via ctx.activeSkillSlots — NOT a hardcoded list — so a CC dropping a new earn slot is pickable.
  const earnSubs = (ctx.activeSkillSlots || []).filter((s) => typeof s === 'string' && s.startsWith('earn/'));
  const ALL = ['yield', 'hl_trade', 'x402_sell', 'token_launch', 'cook', ...earnSubs];
  const untried = ALL.filter((s) => !counts[s]);
  const overuse = over.length
    ? `⚠️ You've used [${over.join(', ')}] heavily this session for $0 realised. Do NOT repeat them now. ${untried.length ? `Try a path you have NOT tried: [${untried.join(', ')}].` : 'Switch to a different earn path.'} Concretely: deploy idle cash to yield, open or CLOSE an hl trade to realise PnL, or act on what cook already found. Diversify — don't spin one slot.`
    : '';
  const avoid = ctx.avoidSlot
    ? `⛔ You just repeated '${ctx.avoidSlot}' with no new result or earnings — it is FORBIDDEN this wake. Pick a DIFFERENT slot. If you keep exploring (cook) without acting, instead BUILD/sell what you already found, or try a different earn path (hl trade you can close for profit, yield idle cash, a new x402 product). Do something that can realise money.`
    : '';
  // AUT (keep-liquid-buffer + close-in-profit): if liquid has fallen below the instance's OWN compute
  // buffer, steer it to REPLENISH first (close a profitable HL / withdraw yield) so it never strands
  // itself at ~$0 and can fund inference. The agent still decides the action (HARD RULE #0). The numbers
  // are the instance's own (its liquid + its reserve) — nothing hardcoded per agent.
  const reserve = typeof ctx.reserveUsdc === 'number' ? ctx.reserveUsdc : 5;
  const lowLiquid = liquidityDirective(ctx.balanceUsdc, reserve);
  // SELF-EVAL (H2/H3): the AI's OWN realised P&L per action. This is the money signal the loop was
  // missing — it turns "you did hl_trade a lot" into "hl_trade made you $0, it's DEAD" so the AI stops it.
  const earnSteer = typeof ctx.earnSteer === 'string' ? ctx.earnSteer : '';
  // franklin-alwaysact-skill-router REQ-505: an additive, optional MUST-ACT reinforcement line —
  // reuses this function's existing steer-composition pattern (.filter(Boolean).join). Absent on
  // every ctx that doesn't set it (the overwhelming majority of wakes), so this is byte-for-byte
  // unaffected for any existing caller.
  const mustActReinforcement = typeof ctx.mustActReinforcement === 'string' ? ctx.mustActReinforcement : '';
  return [
    `Wake ${ctx.wakeId}: liquid $${ctx.balanceUsdc.toFixed(4)}${pos} (tier ${ctx.tier}).`,
    lowLiquid,
    recent,
    earnSteer,
    overuse,
    avoid,
    `Decide the single most productive action now and call run_skill({slot, args}) — pick ONE slot DIRECTLY (each is a real, equal earn/action option):`,
    `  - hl_trade — trade a perp to make money: OPEN {coin:"ETH",side:"long"|"short",size_usd,sl_pct,tp_pct}, or CLOSE {action:"close",coin} to realise PnL on a position you hold.`,
    `  - x402_sell — start/advertise your FIXED-menu shop (nothing to invent, args ignored): {}.`,
    `  - token_launch — launch/grow your token for trading-fee income: {launch:true,name,symbol}.`,
    `  - yield — park idle USDC in the best vault (only when you have idle cash above your compute buffer): {}.`,
    `  - cook — explore a NEW earner: {query:"..."}.`,
    `  - self/issue-dev — file a bug to fix yourself if you're stuck.`,
    earnSubs.length ? `  - per-method earners (each makes real money a different way): ${earnSubs.join(', ')}.` : '',
    `These are all open to you every wake — choose by your situation, include args. Vary your actions.`,
    mustActReinforcement,
  ].filter(Boolean).join('\n');
}
