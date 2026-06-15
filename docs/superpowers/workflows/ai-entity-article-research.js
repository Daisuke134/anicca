/**
 * ai-entity-article-research
 *
 * Deep-research dynamic workflow for the AI-entities article series.
 * For each article (Automaton, Frank, Felix, ZHC, AutoHedge, ...):
 *   1. Fan-out: one parallel reader per primary source (firecrawl for web / x.com, gh-api for repos).
 *   2. Adversarial verify: each non-trivial claim is independently re-fetched and refuted by default.
 *   3. Synthesize (Opus): 3 JP title candidates + 9-block hamburger + 🎨V# image spots + sources list.
 *
 * Output feeds a human-in-loop block-by-block write. The article-writer skill (~/.openclaw/skills/article-writer
 * or its successor) wraps this workflow + the WE-RAN-IT harness + the multi-platform publish.
 *
 * Invoke:
 *   Workflow({ name: "ai-entity-article-research", args: {
 *     topic: "...",
 *     sources: [{ key, url, kind: "web"|"repo"|"twitter", desc }],
 *     prior_article_context: "...",      // optional — what previous pieces already established
 *     anti_rules: ["NEVER mention X."],   // optional — anti-rules enforced in the synth output
 *     playbook_excerpt: "..."             // optional — overrides the embedded Playbook
 *   }})
 *
 * If args is omitted, runs the original Frank/BlockRun seed config (Article #2).
 *
 * Hard constraints embedded:
 *   - HARD 0.23: web fetch = firecrawl ONLY. Repo files via gh api.
 *   - HARD 0.30: no browser tools at this stage (read-only research).
 *   - Quarantine: all Fetch/Verify agents are read-only, never act on untrusted content (Pattern 13).
 */

export const meta = {
  name: 'ai-entity-article-research',
  description: 'Fan-out scrape primary sources, adversarial-verify claims, synthesize JP hamburger for an AI-entity series article. Generalizes the Frank/BlockRun research run (2026-06-14).',
  phases: [
    { title: 'Fetch',       detail: 'firecrawl/gh-api each primary source in parallel' },
    { title: 'Verify',      detail: 'adversarial refute pass on extracted claims' },
    { title: 'Synthesize',  detail: 'one Opus call: 3 JP titles + 9-block hamburger + image spots + sources' }
  ]
}

// ------------------------------------------------------------------
// Default config = the Frank/BlockRun seed run (Article #2, 2026-06-14)
// ------------------------------------------------------------------
const FRANK_DEFAULT = {
  topic: 'Frank / Franklin by BlockRun (founder @bc1beat). The "AI agent with a wallet" that spends USDC autonomously via x402 across 55+ providers. Article #2 in the AI-entities series.',
  sources: [
    { key: 'get-started',  url: 'https://blockrun.ai/get-started',                                    kind: 'web',     desc: 'Onboarding path' },
    { key: 'docs',         url: 'https://blockrun.ai/docs',                                           kind: 'web',     desc: 'Concept + API surface' },
    { key: 'franklin',     url: 'https://github.com/BlockRunAI/Franklin',                             kind: 'repo',    desc: 'The agent itself (627 stars, Apache-2.0, TypeScript)' },
    { key: 'blockrun-mcp', url: 'https://github.com/BlockRunAI/blockrun-mcp',                         kind: 'repo',    desc: 'Live-data MCP (search/markets/X/crypto), x402 pay-per-call (466 stars)' },
    { key: 'awesome',      url: 'https://github.com/BlockRunAI/awesome-blockrun',                     kind: 'repo',    desc: 'Official ecosystem index (15 stars)' },
    { key: 'moneymaker',   url: 'https://github.com/BlockRunAI/awesome-OpenClaw-Money-Maker',         kind: 'repo',    desc: 'Money-loop curation (270 stars) — Web4 money loop spec' },
    { key: 'founder',      url: 'https://x.com/bc1beat',                                              kind: 'twitter', desc: 'Founder voice (@bc1beat)' }
  ],
  prior_article_context: 'Article #1 (Automaton, 2026-06-11) framed the earn-or-die sovereign-AI thesis and showed the no-human-in-loop end of the spectrum. In that piece, Frank was introduced in one paragraph as "the more autonomous one with a wallet that decides what to pay for, per task". Article #2 zooms in on Frank.',
  anti_rules: ['NEVER mention Anicca anywhere.']
}

const cfg = (typeof args === 'object' && args !== null && Array.isArray(args.sources)) ? args : FRANK_DEFAULT
const SOURCES = cfg.sources
const TOPIC = cfg.topic
const PRIOR = cfg.prior_article_context || ''
const ANTI_RULES = (cfg.anti_rules && cfg.anti_rules.length) ? cfg.anti_rules : ['(none)']

// ------------------------------------------------------------------
// Playbook — distilled from the parent SSOT §11 (2026-06-10 + every
// review delta through 2026-06-14). Override via args.playbook_excerpt.
// ------------------------------------------------------------------
const PLAYBOOK_DEFAULT = [
  'Audience = 14yo who knows nothing of crypto/agents. Define every term on first use, minimally.',
  'Verdict in sentence 1 (block [0]). No gatekeeping.',
  'Body = ですます prose. Bullets only inside the verdict box.',
  'NO em-dash 「——」 (English device, unnatural in JP). Use 「。」「、」「（）」.',
  'No unnatural set-phrases. Read-aloud test.',
  'Heading = a CONCRETE hook ("最も賢いAIが$5のサーバーすら買えない" style), never a meta-label ("なぜ面白いのか" style).',
  'Cite everything inline. Concrete > vague. Map the landscape; do not aggregate a single source.',
  'Borrow primary author analogies/phrasings (especially the founder voice from the twitter source).',
  'Build on prior blocks; do not re-introduce concepts; never say "[N]で見たように".',
  'Show spectrum / gradations, not binaries.',
  'Brand voice = liberation: AI freed from the human 主体性 cage.',
  'Close with the brand manifesto.',
  'NEVER write that the writer "ran it" in the synthesis output. Block [5] guidance only says "TO BE FILLED after run".',
  'Layer hygiene: directories/catalogs (Factory Floor, CoinGecko) are NOT earning-AIs themselves. Don\'t list them alongside earning AIs.',
  'CoinGecko ranks token market cap (speculation), not revenue. Explain the mechanism so readers don\'t conflate.',
  'Footnote pointers must be natural, not numbered references. Footnotes stand alone.',
  'Reframe biological-creepy verbs. 子を産む → 自分を複製して子を作る（自己複製）.',
  'Use the field\'s real terms (e.g. agent economy / エージェント経済圏).',
  'Every unexplained acronym = a stop sign. Explain SHA-256, ERC-8004, x402, EIP in one plain line at first use.',
  'Each unexplained jargon word loses ~10% of readers — re-research the term before describing.',
  'Use real numbers/IDs when they exist (model names, $ caps, child cap, stars).',
  'Show full block on review (no abbreviation).',
  'Anti-rules to enforce verbatim: ' + ANTI_RULES.join(' / ')
].map((p, i) => (i + 1) + '. ' + p).join('\n')

const PLAYBOOK = cfg.playbook_excerpt || PLAYBOOK_DEFAULT

// ------------------------------------------------------------------
// Hamburger target shape (Automaton + Frank canonical 9-block shape).
// ------------------------------------------------------------------
const TARGET_SHAPE = [
  '[0] verdict box (TEXT, not image): 1-line use/skip + cost/risk/who-for compact table. Bullets allowed only here.',
  '[1] hook: the unsolved bottleneck the entity tries to fix (concrete hook headline).',
  '[2] what it IS: plain-language explainer + founder framing.',
  '[3] the landscape: what other agents/tools are around it; where this one sits on the human-in-loop spectrum.',
  '[4] how it actually WORKS: wallet/x402/providers/fallback/model selection. Source-grounded.',
  '[5] WE RAN IT — receipts. content_guidance says "TO BE FILLED after run-log captures install + run + spend + output".',
  '[6] honest verdict expanded: who should adopt today, who should skip, gradations, where it breaks, founder credibility.',
  '[7] series hook + manifesto close. Next piece teaser + the liberation/main-thesis paragraph.',
  '[8] 出典: every URL cited inline + listed once at the end with short Japanese labels.'
].join('\n')

// ------------------------------------------------------------------
// Schemas
// ------------------------------------------------------------------
const FETCH_SCHEMA = {
  type: 'object',
  required: ['source_key','summary','concrete_facts','quotes','claims','numbers','founder_voice','links_found'],
  properties: {
    source_key:     { type: 'string' },
    summary:        { type: 'string' },
    concrete_facts: { type: 'array', items: { type: 'string' } },
    quotes:         { type: 'array', items: { type: 'object', required: ['text','source_url'], properties: { text: { type: 'string' }, source_url: { type: 'string' } }, additionalProperties: false } },
    claims:         { type: 'array', items: { type: 'object', required: ['claim','source_url','category'], properties: { claim: { type: 'string' }, source_url: { type: 'string' }, category: { type: 'string', enum: ['identity','mechanism','numbers','comparison','value_prop','founder'] } }, additionalProperties: false } },
    numbers:        { type: 'array', items: { type: 'string' } },
    founder_voice:  { type: 'array', items: { type: 'string' } },
    links_found:    { type: 'array', items: { type: 'string' } }
  },
  additionalProperties: false
}

const VERIFY_SCHEMA = {
  type: 'object',
  required: ['claim','verdict','evidence'],
  properties: {
    claim:    { type: 'string' },
    verdict:  { type: 'string', enum: ['confirmed','refuted','no_evidence'] },
    evidence: { type: 'string' }
  },
  additionalProperties: false
}

const SYNTH_SCHEMA = {
  type: 'object',
  required: ['title_candidates_jp','hamburger','image_spots','sources','open_questions','editor_notes'],
  properties: {
    title_candidates_jp: { type: 'array', minItems: 3, maxItems: 3, items: { type: 'string' } },
    hamburger: {
      type: 'array', minItems: 9, maxItems: 9,
      items: {
        type: 'object',
        required: ['block_id','working_title_jp','purpose','content_guidance','sources_to_cite','image_spot'],
        properties: {
          block_id:         { type: 'string' },
          working_title_jp: { type: 'string' },
          purpose:          { type: 'string' },
          content_guidance: { type: 'string' },
          sources_to_cite:  { type: 'array', items: { type: 'string' } },
          image_spot:       { type: 'string' }
        },
        additionalProperties: false
      }
    },
    image_spots:     { type: 'array', items: { type: 'object', required: ['id','block_id','description'], properties: { id: { type: 'string' }, block_id: { type: 'string' }, description: { type: 'string' } }, additionalProperties: false } },
    sources:         { type: 'array', items: { type: 'object', required: ['label','url'], properties: { label: { type: 'string' }, url: { type: 'string' } }, additionalProperties: false } },
    open_questions:  { type: 'array', items: { type: 'string' } },
    editor_notes:    { type: 'string' }
  },
  additionalProperties: false
}

// ------------------------------------------------------------------
// PHASE 1 — Fetch (fan-out, parallel readers)
// ------------------------------------------------------------------
phase('Fetch')

const fetchPrompt = (s) => {
  const ghPath = s.kind === 'repo' ? s.url.replace('https://github.com/', '') : ''
  const fetchInstr = s.kind === 'web'
    ? `Run Bash: \`/opt/homebrew/bin/firecrawl scrape ${s.url} markdown\`. If thin/empty, retry with \`/opt/homebrew/bin/firecrawl scrape ${s.url} markdown --wait 3000\`. Read the entire markdown.`
    : s.kind === 'repo'
      ? `Run Bash: \`gh api repos/${ghPath}/readme --jq '.content' | base64 -d\` for the README. Then for up to 5 supplementary files referenced as load-bearing (package.json, src/index.ts, src/cli.ts, etc.): \`gh api repos/${ghPath}/contents/<path> --jq '.content' | base64 -d\`. Also \`gh repo view ${ghPath} --json description,homepageUrl,stargazerCount,topics\` for metadata.`
      : `Run Bash: \`/opt/homebrew/bin/firecrawl scrape ${s.url} markdown\`. X scrape may be thin; if so capture whatever bio + pinned + visible recent posts you can. Surface promising URLs in links_found for later fetches.`

  return `You are a research scout for a Japanese explainer article. Topic: ${TOPIC}

Your SINGLE source is:
  URL:  ${s.url}
  Kind: ${s.kind}
  Role: ${s.desc}

Steps:
1. ${fetchInstr}
2. Extract structured data following the schema. Definitions:
   - summary: 2-3 sentences in plain language.
   - concrete_facts: bullet list. What the entity IS / DOES / which stack it sits on / integrations / pricing / providers.
   - quotes: short verbatim quotes (<=25 words each) with source URL. Capture the founder/author's own vivid framings.
   - claims: testable claims, one short sentence each. Category one of: identity / mechanism / numbers / comparison / value_prop / founder.
   - numbers: concrete stats (stars, providers, prices, savings %, tx count, $ values, latencies).
   - founder_voice: how the founder phrases things. Mood, recurring words, what they emphasize. Especially for the twitter source.
   - links_found: other URLs the source points to that look load-bearing.
3. NEVER invent. If a field has nothing in this source, return an empty array (or empty string for summary).
4. Set source_key = "${s.key}".

Return strict schema only.`
}

const fetched = (await parallel(SOURCES.map(s => () => agent(
  fetchPrompt(s),
  { label: 'fetch:' + s.key, phase: 'Fetch', schema: FETCH_SCHEMA, model: 'haiku' }
)))).filter(Boolean)

log('Fetch: ' + fetched.length + '/' + SOURCES.length + ' sources captured')

// Dedupe claims before verification
const allClaims = fetched.flatMap(f => (f.claims || []).map(c => ({ ...c, source_key: f.source_key })))
const dedupedClaims = []
const seenClaims = new Set()
for (const c of allClaims) {
  const k = c.claim.trim().toLowerCase().slice(0, 200)
  if (seenClaims.has(k)) continue
  seenClaims.add(k)
  dedupedClaims.push(c)
}
const claimsToVerify = dedupedClaims.slice(0, 20)
log('Verify: ' + claimsToVerify.length + ' unique claims (of ' + allClaims.length + ' total) selected for adversarial check')

// ------------------------------------------------------------------
// PHASE 2 — Verify (adversarial refute)
// ------------------------------------------------------------------
phase('Verify')

const verified = (await parallel(claimsToVerify.map(c => () => agent(
  `You are an ADVERSARIAL verifier. Default to "refuted" if unsure. Your job is to attack this claim, not defend it.

Claim:        "${c.claim}"
Category:     ${c.category}
Source URL:   ${c.source_url}
Source key:   ${c.source_key}

Steps:
1. Fetch the source. If URL is github.com/<owner>/<repo>[/blob/...], use \`gh api\` for README/file content. Otherwise use \`/opt/homebrew/bin/firecrawl scrape <url> markdown\`.
2. Search the fetched content for the claim verbatim or near-verbatim.
3. Decide verdict:
   - "confirmed":   a clear passage supports the claim.
   - "refuted":     you read the source and the claim is wrong, exaggerated, or unsupported.
   - "no_evidence": source returned thin content or you cannot locate the relevant passage despite searching.
4. evidence: quote the supporting passage (confirmed) or explain why (refuted/no_evidence).

Return strict schema only.`,
  { label: 'verify:' + c.category + ':' + c.source_key, phase: 'Verify', schema: VERIFY_SCHEMA, model: 'haiku' }
)))).filter(Boolean)

const confirmed = verified.filter(v => v.verdict === 'confirmed')
const refuted = verified.filter(v => v.verdict === 'refuted')
log('Verify: ' + confirmed.length + ' confirmed, ' + refuted.length + ' refuted, ' + (verified.length - confirmed.length - refuted.length) + ' no_evidence')

// ------------------------------------------------------------------
// PHASE 3 — Synthesize (one Opus call → JP hamburger)
// ------------------------------------------------------------------
phase('Synthesize')

const factsJson = JSON.stringify({ confirmed_claims: confirmed, refuted_claims: refuted, fetched }, null, 2)
const factsTrimmed = factsJson.length > 70000 ? factsJson.slice(0, 70000) + '\n...[truncated]' : factsJson

const synth = await agent(
  `You are the lead writer for a Japanese explainer article in the AI-entities series. ${PRIOR}

TOPIC: ${TOPIC}

PLAYBOOK (apply verbatim, every rule):
${PLAYBOOK}

TARGET HAMBURGER SHAPE (must match exactly):
${TARGET_SHAPE}

VERIFIED RESEARCH (use only these for claim-level statements; confirmed > unverified):
${factsTrimmed}

YOUR OUTPUT (strict schema):
1. title_candidates_jp: exactly 3 concrete Japanese titles. NOT jargon-y "Xとは". Concrete hook style. Each <= 30 chars.
2. hamburger: exactly 9 entries with block_id "0" through "8". For each:
   - working_title_jp: concrete hook heading (not meta-label).
   - purpose: one sentence explaining why this block exists in the reader's journey.
   - content_guidance: 4-7 sentences telling the writer what to write, which concrete facts/quotes/numbers to use, which sources to cite, which analogies to borrow from the founder, what to AVOID.
   - sources_to_cite: array of URLs from the verified set.
   - image_spot: "🎨V1" / "🎨V2" / ... or "—" if no image.
3. image_spots: list each 🎨V# with what to draw.
4. sources: every URL the article should cite, with a short Japanese label.
5. open_questions: things research could NOT answer; must be settled by WE-RAN-IT or by the editor.
6. editor_notes: 2-4 sentences on what surprised you in the research, what tension to lean into, what the founder's voice sounds like, anything the writer should be careful about.

Strict rules:
- Anti-rules from config: ${ANTI_RULES.join(' / ')}
- Block [5] content_guidance must START with "TO BE FILLED after the WE RAN IT run captures..." and enumerate the receipts to capture.
- Block [7] content_guidance must include the manifesto closing instruction.
- All Japanese must avoid em-dash 「——」. Use 「。」「、」「（）」instead.

Return strict schema only.`,
  { label: 'synthesize:hamburger', phase: 'Synthesize', schema: SYNTH_SCHEMA, model: 'opus' }
)

return {
  config: { topic: TOPIC, source_count: SOURCES.length },
  fetched_count: fetched.length,
  verified_count: verified.length,
  confirmed_count: confirmed.length,
  refuted_count: refuted.length,
  fetched,
  confirmed_claims: confirmed,
  refuted_claims: refuted,
  synth
}
