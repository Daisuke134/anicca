// anicca-launch.workflow.js — Dynamic Workflow that FINISHES + LIVE-verifies Anicca + Life Manager.
// BP: zenn/aria3 "Dynamic Workflows 6 patterns" (0xCodez) + Addy Osmani "loop-engineering".
// It fixes the 3 single-window failure modes STRUCTURALLY (this is why the 1st run shipped a façade):
//   - agentic laziness (declares "done" before it is)      -> Loop-until-done: stop only when a FRESH
//                                                              re-audit returns zero open gaps (+ /goal).
//   - self-preferential bias (verifier favors own work)    -> Adversarial verification: reviewer/verifier
//                                                              are BLIND to the maker, see rubric+artifact
//                                                              only, and must paste RAW command+output.
//   - goal drift (constraints silently vanish post-compact)-> Fan-out: each subsystem is a fresh isolated
//                                                              agent; the gap ledger lives in CODE, not context.
// Pattern chain (the BP combo for migrations/large fixes): Fan-out(audit) -> REAL diff patch
//   -> Adversarial review (superpowers, before merge) -> apply to main -> LIVE browser verify
//   (camofox real user action) -> Loop-until-done (re-audit until zero open gaps).
// /goal pairing: stop only when a fresh full audit = 0 open gaps AND the 3 launch-post claims verify live.
// The director (main loop) writes+launches+monitors this and USES the product each round — never trusts a pass.
//
// Run: Workflow({scriptPath:'docs/superpowers/workflows/anicca-launch.workflow.js'})  (ultracode / +Nk budget)

export const meta = {
  name: 'anicca-launch',
  description: 'Audit live state -> generate REAL diff patches -> superpowers review (before merge) -> apply to main -> LIVE browser-verify by USING the product (camofox) -> loop until a fresh audit finds zero open gaps. No mock, no placeholder URL, no disabled button, no "coming soon".',
  phases: [
    { title: 'Foundation', detail: 'verify shared scaffold live on main (registry, nav, /install /me /dashboard /life-manager 200)' },
    { title: 'Audit', detail: 'fan-out one auditor per subsystem -> gap ledger with REAL live evidence (camofox click / curl every CTA / grep served HTML / run command)' },
    { title: 'Build', detail: 'per open subsystem: builder writes a REAL diff for the audited gaps -> blind reviewer (spec-compliance, BEFORE merge) -> merge to main + deploy -> live verifier USES the product via camofox -> loop max 3' },
    { title: 'E2E', detail: 'full live chain: signed telemetry->dashboard, Stripe spawn->droplet->destroy, 1 real earn tx, REAL Charon call to Dais' },
    { title: 'Distribute', detail: 'quarantined research -> article DRAFT (human-in-loop: Dais edits) -> claim-check' },
  ],
}

// ----------------------------- NO-FAÇADE RULES (injected into every agent) ---------------------
const RULES =
  '★ NO-FAÇADE RULES (apply to you, every step) ★ ' +
  '(1) "done" = a REAL USER completes the action AND the flow BEHIND it works end-to-end ' +
  '(install button -> reaches checkout.stripe.com -> webhook spawns a real droplet; dashboard shows REAL numbers; ' +
  '/me withdraw actually moves money; life-call actually connects). A button that clicks but leads nowhere = FAIL. ' +
  '(2) SEE the UI yourself: open the LIVE page in camofox (REST http://localhost:9377) or agent-browser, screenshot it, ' +
  'click the real control, follow the flow. NEVER judge from curl-200 alone. ' +
  '(3) Evidence = RAW command + RAW output pasted verbatim. A summary is not evidence. ' +
  '(4) Frontend: use the taste-skill (design-taste-frontend) for layout/typography/motion/spacing — no generic AI-slop UI; ' +
  'and ZERO placeholder URLs, ZERO disabled "opens at launch" buttons, ZERO "coming soon" badges, ZERO internal jargon ' +
  '(GATE-0 / swap-eth-usdc / B-travel / spec27 / HARD-rule citations) in user-facing HTML. ' +
  '(5) No mock / no dry-run / no "would-have" (HARD 0.24 / 0.31).'

// ----------------------------- schemas (force structured output) -----------------------------
const AUDIT = {
  type: 'object', additionalProperties: true, required: ['subsystem', 'gaps'],
  properties: {
    subsystem: { type: 'string' },
    gaps: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: true,
        required: ['title', 'spec_requires', 'live_evidence', 'severity', 'fix'],
        properties: {
          title: { type: 'string' },
          spec_requires: { type: 'string' },
          live_evidence: { type: 'string', description: 'RAW command + output proving the CURRENT broken state' },
          severity: { type: 'string', enum: ['blocker', 'major', 'minor'] },
          fix: { type: 'string', description: 'the concrete change (file path + what) to close it' },
        },
      },
    },
  },
}
const BUILD = {
  type: 'object', additionalProperties: true,
  required: ['subsystem', 'files', 'summary', 'self_test', 'branch', 'pr'],
  properties: {
    subsystem: { type: 'string' }, branch: { type: 'string' }, pr: { type: 'string', description: 'the open (UNMERGED) PR number/url' },
    files: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
    self_test: { type: 'string', description: 'the exact command(s) the builder ran and their raw result' },
  },
}
const REVIEW = {
  type: 'object', additionalProperties: false, required: ['ok', 'blocking'],
  properties: {
    ok: { type: 'boolean' },
    blocking: { type: 'array', items: { type: 'string' }, description: 'spec-compliance / façade blockers; empty iff ok' },
    evidence: { type: 'string' },
  },
}
const VERDICT = {
  type: 'object', additionalProperties: false, required: ['pass', 'evidence', 'gaps'],
  properties: {
    pass: { type: 'boolean' },
    evidence: { type: 'string', description: 'fresh LIVE evidence (raw command + output) for EACH rubric point; empty if not run' },
    gaps: { type: 'array', items: { type: 'string' } },
  },
}
const RESEARCH = {
  type: 'object', additionalProperties: true, required: ['facts', 'sources'],
  properties: { facts: { type: 'array', items: { type: 'string' } }, sources: { type: 'array', items: { type: 'string' } } },
}
const DRAFT = {
  type: 'object', additionalProperties: true, required: ['path', 'title', 'claims'],
  properties: { path: { type: 'string' }, title: { type: 'string' }, claims: { type: 'array', items: { type: 'string' } } },
}

// ----------------------------- subsystem definitions (DISJOINT file sets, spec26/27) -----------
// model = classify-and-act: opus for hard reasoning / live infra, sonnet for static pages/research.
const A = [
  { key: 'dashboard', model: 'sonnet', spec: 'spec27 A-dashboard',
    rubric: 'apps/landing/app/dashboard/page.tsx fetches /.netlify/functions/dashboard-sync and renders REAL instance numbers (total net worth + leaderboard + alive count); deployed to aniccaai.com; camofox opens the live page and a screenshot shows real numbers (NOT a bare "Loading…"). No placeholder numbers, no internal jargon.' },
  { key: 'install-me', model: 'sonnet', spec: 'spec27 A-install/me',
    rubric: 'apps/landing/app/{install,me}/page.tsx live on aniccaai.com; /install is 2-column (cloud product + OSS self-host); ★the cloud CTA, clicked in camofox, navigates to a real checkout.stripe.com page for the $30/mo Anicca Cloud (NOT 403)★; the OSS column shows a working self-host path; /me has NO disabled "opens at launch" theatre (either real withdraw/pause/report or removed). No raw shell, no jargon; taste-skill quality.' },
  { key: 'stripe-spawn', model: 'opus', spec: 'spec27 A-stripe-spawn',
    rubric: 'apps/landing/netlify/functions/stripe-spawn-webhook.js: a Stripe test checkout.session.completed creates a REAL DO droplet + Supabase owners row; customer.subscription.deleted destroys it; event.id idempotent. Show the droplet id created then destroyed (raw DO API output).' },
  { key: 'earn', model: 'opus', spec: 'spec27 A-earn (GATE-0)',
    rubric: '~/anicca/skills/earn wired into the automaton loop; ONE profitable wake: wallet USDC before/after delta > 0 from EXTERNAL revenue (NOT an ETH->USDC swap / asset liquidation) with a basescan tx status=0x1 recorded in earn-ledger.jsonl. Narration or a swap = FAIL.' },
  { key: 'self-spawn', model: 'opus', spec: 'spec27 A-self-spawn',
    rubric: '~/anicca/skills/self/spawn births a child instance (DO/Akash) with its OWN wallet addr + OWN AgentMail inbox; child appears in dashboard; child attempts earn on its own wake. Show child systemctl active + distinct wallet (raw ssh/API output).' },
  { key: 'ubi', model: 'opus', spec: 'spec15/17 economy/ubi',
    rubric: '~/anicca/skills/economy/ubi: surplus USDC -> on-chain Treasury -> a real distribution tx to >=1 AI agent and >=1 human address (basescan status=0x1). Show the tx hashes. No narration.' },
  { key: 'auto-cancel-report', model: 'opus', spec: 'spec27 A-self-funding',
    rubric: 'when wallet covers cost, the $30/mo Stripe subscription is auto-cancelled (show the Stripe subscription status=canceled via API) AND /me reflects "self-funded"; AND the agent PROCESS (not Claude) sends a daily wake report email via AgentMail with real net worth/revenue/tasks/next (show the sent message id).' },
]
const B = [
  { key: 'life-travel', model: 'sonnet', spec: 'spec27 B-travel',
    rubric: '~/anicca/skills/life/travel.js: creating a test gcal event causes a Maps-derived travel block to be auto-inserted before it in gcal (verified by reading gcal back). Applies to chained events.' },
  { key: 'life-call', model: 'opus', spec: 'spec27 B-call (Gemini Charon, bidirectional)',
    rubric: '~/anicca/skills/life/call.js: a REAL outbound call to +818046270314 CONNECTS (carrier API shows duration>0), bridges Twilio/Telnyx Media Streams <-> Gemini Live (voice=Charon), speaks the next-event guidance bidirectionally, recording is non-silent. Provide the call SID + recording URL from the carrier API. (Twilio is fraud-blocked to JP -> use Telnyx + TELNYX_API_KEY.) A prior "proof" (CA2c02…) is DISPUTED by audit — re-prove a fresh connected call.' },
  { key: 'life-ask', model: 'sonnet', spec: 'spec27 B-ask',
    rubric: '~/anicca/skills/life/ask.js: unknown location/duration -> a question email is sent to Dais Gmail; a reply fills the gcal where (AgentMail inbound webhook). Show the sent email + the gcal update after reply.' },
  { key: 'life-notify', model: 'sonnet', spec: 'spec27 B-notify (email-only approval)',
    rubric: '~/anicca/skills/life/notify.js: on late-risk, Anicca emails Dais a draft "OK to send to <stakeholder>?"; Dais email reply "OK" triggers the actual send to the stakeholder. Fully email. Show the approval round-trip.' },
  { key: 'life-webapp', model: 'sonnet', spec: 'spec27 B / spec07',
    rubric: 'aniccaai.com/life-manager is a WORKING cloud web-app, not a marketing page: in camofox, a user can connect a calendar (Google) and SEE their schedule with auto travel blocks. Onboarding collects name/phone/calendar/location. No "coming" badges.' },
]

// ----------------------------- token-budget guard (BP: always cap) ----------------------------
const RESERVE = 80_000
const budgetLow = () => typeof budget !== 'undefined' && budget !== null && budget.total !== null && budget.remaining() < RESERVE

// ----------------------------- build = real diff -> blind review -> merge -> live verify --------
// Adversarial verification (BP pattern 3): reviewer + verifier are BLIND to the maker, see rubric+artifact
// only, paste RAW output. Review happens BEFORE merge (Dais: patches reviewed before apply); live verify
// happens AFTER merge+deploy. loop max 3 then escalate.
async function buildAndVerify(s, gaps) {
  let feedback = ''
  for (let i = 0; i < 3; i++) {
    if (budgetLow()) { log(`${s.key}: budget low — escalate, not exceeding cap`); return { subsystem: s.key, track: s.track, pass: false, feedback: 'token budget exhausted' } }

    // 1) BUILDER — real applicable diff for the audited gaps; open PR but DO NOT merge yet.
    const build = await agent(
      `BUILDER for subsystem "${s.key}" (track ${s.track}). ${RULES} ` +
      `Spec: ${s.spec} (read docs/superpowers/specs/anicca/27 + 26 + the telemetry-pipeline plan as the proven template). ` +
      `★ A REVIEWED, revised real-diff patch for "${s.key}" likely exists at docs/superpowers/specs/anicca/patches/${s.key}.patch.md — if it does, APPLY IT as your implementation: produce the REAL git diff against live code, honoring its diffs + commands + integrity constraints; do NOT re-derive from scratch. For skill subsystems (earn / life-*), the LIVE runtime is ~/clawd (a non-symlink COPY of ~/anicca) + ~/.hermes/cron — you MUST apply to ~/clawd AND ~/anicca and fix the jobs.json target, because editing only ~/anicca does NOT change the running loop. ` +
      `Close EXACTLY these audited gaps — each includes RAW evidence of the current broken state:\n${JSON.stringify(gaps, null, 1)}\n` +
      (feedback ? `The reviewer/verifier REJECTED the prior attempt — fix exactly: ${feedback}. ` : '') +
      `Read the LIVE code at each path, write a REAL applicable diff (NOT a sketch), follow SDD+TDD, run the tests. ` +
      `Branch off main (name prefix feature/|fix/|chore/|docs/|spec/, git author "Daisuke Sato <keiodaisuke@gmail.com>"), commit, open a PR, and report the PR number — ★do NOT merge yet★ (a reviewer checks the diff before it lands). ` +
      `Collision rule: ADD your own new files; do NOT edit shared files (install.sh / landing nav / skills/registry.json) — if you think you must, stop and report it as a gap. ` +
      `Target rubric: ${s.rubric}`,
      { label: `build:${s.key}`, phase: 'Build', schema: BUILD, model: s.model, isolation: 'worktree' }
    )
    if (!build) { feedback = 'builder died'; log(`${s.key}: builder died (iter ${i + 1})`); continue }

    // 2) ADVERSARIAL REVIEW (before merge) — blind, rubric+artifact only, find the weakest case.
    const review = await agent(
      `ADVERSARIAL CODE REVIEWER (superpowers code-review). You did NOT write this and do not know who did. ${RULES} ` +
      `Review the UNMERGED PR #${build.pr} (branch ${build.branch}) diff for SPEC-COMPLIANCE against this rubric: ${s.rubric} ` +
      `Artifact: files=${JSON.stringify(build.files)}, builder_self_test=${build.self_test}. Read the diff; try to find the weakest case. ` +
      `ok=false with concrete blocking[] if ANYTHING is a façade / placeholder URL / disabled button / "coming" / mock / not spec-compliant. ok=true only if the diff genuinely makes a real user able to do the thing.`,
      { label: `review:${s.key}`, phase: 'Build', schema: REVIEW, model: 'opus', agentType: 'superpowers:code-reviewer' }
    )
    if (!review || !review.ok) { feedback = review ? review.blocking.join('; ') : 'reviewer died'; log(`${s.key}: review rejected iter ${i + 1} — ${feedback}`); continue }

    // 3) MERGE + deploy — only after review passed.
    const merged = await agent(
      `MERGE+DEPLOY agent. The reviewer approved PR #${build.pr} (${build.branch}). Merge it to main (gh pr merge ${build.pr} --merge --delete-branch) and, for web/functions, WAIT for the Netlify/main deploy to go green. Report the merge commit + the live URL. ${RULES}`,
      { label: `merge:${s.key}`, phase: 'Build', schema: BUILD, model: 'sonnet' }
    )
    if (!merged) { feedback = 'merge/deploy failed'; log(`${s.key}: merge failed iter ${i + 1}`); continue }

    // 4) LIVE VERIFIER — independent, USES the product via camofox, paste raw output.
    const v = await agent(
      `LIVE VERIFIER (independent context). ${RULES} The change is MERGED + deployed on main / aniccaai.com. ` +
      `Rubric — EVERY point must hold with FRESH evidence YOU gather by USING the product yourself (camofox: open the live URL, click the real button, follow the flow behind it; or run the real tx/call): ${s.rubric} ` +
      `Actively try to REFUTE that it works; default to pass=false if uncertain. pass=true ONLY if you personally reproduced live evidence (paste raw command+output) for EVERY rubric point; else pass=false + concrete gaps.`,
      { label: `verify:${s.key}`, phase: 'Build', schema: VERDICT, model: 'opus' }
    )
    if (v && v.pass) { log(`${s.key}: LIVE-green (iter ${i + 1})`); return { subsystem: s.key, track: s.track, pass: true, evidence: v.evidence } }
    feedback = v ? v.gaps.join('; ') : 'verifier died'
    log(`${s.key}: not LIVE-green iter ${i + 1} — ${feedback}`)
  }
  return { subsystem: s.key, track: s.track, pass: false, feedback }
}

// =============================================================================================
// PHASE 1 — Foundation. LIVE-verify only (already built+merged): registry + install.sh + nav + routes.
// =============================================================================================
phase('Foundation')
const foundationOk = await agent(
  `Adversarial verifier (independent). ${RULES} Confirm the foundation is LIVE on main: ` +
  `(1) ~/anicca/skills/registry.json has the subsystem slots and install.sh is registry-driven; ` +
  `(2) in camofox, https://aniccaai.com/{install,me,dashboard,life-manager} all load (200); ` +
  `(3) /.netlify/functions/dashboard-sync returns 200. pass only with fresh raw evidence.`,
  { label: 'verify:foundation', phase: 'Foundation', schema: VERDICT, model: 'opus' }
)
if (!foundationOk || !foundationOk.pass) {
  log('Foundation not green — escalate to Dais before fan-out (shared scaffold must be solid first).')
  return { stopped: 'foundation', foundationOk }
}

// =============================================================================================
// PHASE 2+3 — LOOP-UNTIL-DONE: Audit (fan-out) -> Build (real diff -> review -> merge -> live verify)
// -> re-Audit. Stop only when a fresh audit finds ZERO open gaps across all subsystems. (BP pattern 6 + /goal)
// =============================================================================================
const subsystems = [...A.map((s) => ({ ...s, track: 'A' })), ...B.map((s) => ({ ...s, track: 'B' }))]
const byKey = Object.fromEntries(subsystems.map((s) => [s.key, s]))
let open = subsystems
const MAX_ROUNDS = 4
let round = 0
const history = []
while (open.length && round < MAX_ROUNDS) {
  round++
  if (budgetLow()) { log(`budget low before round ${round} — escalate, do not exceed cap`); return { stopped: 'budget', round, open: open.map((s) => s.key) } }

  // AUDIT — fan-out one auditor per still-open subsystem; REAL live evidence; gaps:[] iff fully working.
  phase('Audit')
  const ledgers = (await parallel(open.map((s) => () => agent(
    `AUDITOR for subsystem "${s.key}". ${RULES} Audit the LIVE state vs spec ${s.spec} and this rubric: ${s.rubric} ` +
    `Gather REAL evidence by USING the product: open the live page in camofox and click controls, curl EVERY CTA, grep the served HTML for "Loading"/"coming"/jargon, run the command/tx. ` +
    `Return EVERY gap between spec and live reality, each with RAW live_evidence of the broken state. If it genuinely fully works for a real user, return gaps:[].`,
    { label: `audit:${s.key}`, phase: 'Audit', schema: AUDIT, model: 'opus' }
  ))).filter(Boolean)
  const gapsBy = Object.fromEntries(ledgers.map((l) => [l.subsystem, l.gaps || []]))
  const stillOpen = open.filter((s) => (gapsBy[s.key] || []).length > 0)
  const totalGaps = stillOpen.reduce((n, s) => n + (gapsBy[s.key] || []).length, 0)
  log(`Round ${round} AUDIT: ${stillOpen.length}/${open.length} subsystems have open gaps (${totalGaps} gaps total).`)
  if (!stillOpen.length) { open = []; break }

  // BUILD — fix each open subsystem's audited gaps in parallel (disjoint file sets, worktree-isolated).
  phase('Build')
  const built = (await parallel(stillOpen.map((s) => () => buildAndVerify(s, gapsBy[s.key])))).filter(Boolean)
  history.push({ round, results: built.map((b) => ({ subsystem: b.subsystem, pass: b.pass })) })
  open = built.filter((r) => !r.pass).map((r) => byKey[r.subsystem]).filter(Boolean)
}
if (open.length) {
  log(`STILL OPEN after ${round} rounds: ${open.map((s) => s.key).join(', ')} — escalate to Dais (max rounds or budget).`)
  return { stopped: 'gaps-remain', round, open: open.map((s) => s.key), history }
}
log(`All subsystems LIVE-green and a fresh audit found ZERO open gaps (round ${round}). Proceeding to full E2E.`)
if (budgetLow()) { log('budget low before E2E — escalate'); return { stopped: 'budget-before-e2e', history } }

// =============================================================================================
// PHASE 4 — E2E (one independent verifier runs the whole live chain, incl. the real call).
// =============================================================================================
phase('E2E')
const e2e = await agent(
  `Final E2E verifier (independent context). ${RULES} Run the WHOLE live chain and pass only with fresh raw evidence per HARD 0.31: ` +
  `(a) a genesis wake posts signed telemetry -> dashboard-sync reflects real on-chain net worth (open /dashboard in camofox, see the number); ` +
  `(b) a Stripe test subscription spawns a real DO droplet then cancel destroys it; ` +
  `(c) at least ONE real EXTERNAL-revenue earn tx (basescan status=0x1, not a swap) landed; ` +
  `(d) a REAL Charon (Gemini Live) bidirectional call to +818046270314 connected (duration>0), guided the next event, recording good. ` +
  `List the tx hashes, droplet id, dashboard numbers, call SID/recording.`,
  { label: 'e2e', phase: 'E2E', schema: VERDICT, model: 'opus' }
)
if (!e2e || !e2e.pass) { log(`E2E not fully green: ${e2e ? e2e.gaps.join('; ') : 'verifier died'} — escalate to Dais.`); return { stopped: 'e2e', history, e2e } }

// =============================================================================================
// PHASE 5 — Distribute. quarantine: read-only researchers; writer never sees raw scraped HTML.
// Article = HUMAN-IN-LOOP (draft only; Dais edits & approves). Video + posting = gated follow-up.
// =============================================================================================
phase('Distribute')
const ANGLES = [
  'Anicca thesis + real proof: what was built and the live numbers (net worth, dashboard)',
  'Dynamic Workflows explainer: the 6 patterns + OUR real build log (round3 prod float bug, round4 deployment-reality, dev<->main reconcile, the façade-vs-rubric lesson)',
  'Life Manager value + how the gcal/travel/call/ask/notify flow works for a normal user',
]
const research = (await parallel(ANGLES.map((a) =>
  () => agent(`READ-ONLY researcher (QUARANTINE — take NO actions, touch no files): gather material for "${a}" via Firecrawl/ctx7 + the repo specs. Return facts + source URLs only.`,
    { label: `research:${a.slice(0, 24)}`, phase: 'Distribute', schema: RESEARCH, model: 'sonnet' })
))).filter(Boolean)

const drafts = await parallel([
  ['anicca', 'Anicca(+Life Manager内包) launch article — thesis + real proof'],
  ['dynamic-workflows', 'Dynamic Workflows complete explainer with our real build log'],
].map(([slug, brief]) =>
  () => agent(`Writer: from these QUARANTINED facts ${JSON.stringify(research)}, draft "${brief}" into apps/landing/content/blog/${slug}.md. ` +
    `This is a DRAFT for Dais to edit — DO NOT publish or post anywhere. List your factual claims so a verifier can check them. Beginner-friendly, honest, no hype.`,
    { label: `draft:${slug}`, phase: 'Distribute', schema: DRAFT, model: 'opus' })
)).then((r) => r.filter(Boolean))

const claimChecks = await parallel(drafts.map((d) =>
  () => agent(`Adversarial claim-verifier: check EVERY claim in draft "${d.title}" (${d.path}) against the sources ${JSON.stringify(research.flatMap((x) => x.sources))} and the live repo/prod. Flag any unverified or exaggerated claim.`,
    { label: `claimcheck:${d.title.slice(0, 20)}`, phase: 'Distribute', schema: VERDICT, model: 'opus' })
)).then((r) => r.filter(Boolean))

log('Drafts ready + claim-checked. PAUSE for Dais edit/approval (human-in-loop). Then run the gated follow-up: tournament -> demo video -> distribute (Postiz/X + Slack + TikTok + Product Hunt) -> verify every live URL.')

return {
  foundation: foundationOk?.pass,
  rounds: round,
  history,
  e2e: e2e?.pass,
  drafts: drafts.map((d) => ({ path: d.path, title: d.title })),
  claimChecks,
  gated_followup: ['Dais edits + approves articles', 'tournament: hook/title pairwise', 'demo video (Remotion -> YouTube, frame/audio verify)', 'distribute: Postiz/X + Slack + reelfarm/TikTok + Product Hunt', 'hackathon: connpass JP + luma EN', 'verify every live URL (HARD 0.31)'],
}
