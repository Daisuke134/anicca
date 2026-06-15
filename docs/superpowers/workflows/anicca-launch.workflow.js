// anicca-launch.workflow.js — Dynamic Workflow body for the Anicca + Life Manager launch.
// Bible: "How to master Dynamic Workflows — 6 patterns, 14 steps" (Anthropic engineers).
// Patterns used: classify-and-act (per-agent model) · fan-out-and-synthesize · adversarial
// verification (builder≠verifier, separate context, rubric+artifact only) · loop-until-done
// (/goal: keep going until LIVE-green, max 3) · tournament (article hook taste) · quarantine
// (read-only researchers; actors never see raw scraped HTML) · explicit token budget.
// Spec: docs/superpowers/specs/anicca/27-launch-workflow-and-ubi.md  + 26-implementation-map.md
// SAVE THIS (bible §14): once green, persist to ~/.claude/workflows + ship as a Skill (template, not verbatim).
//
// NOTE: this is the orchestration HARNESS. Each agent() is a fresh, isolated subagent that does the
// real work (edits files, runs node --test, curls prod, places the real phone call) and reports back.
// The main loop (Claude) only writes/launches/monitors this — it is NOT inside the workflow.

export const meta = {
  name: 'anicca-launch',
  description: 'Build + LIVE-E2E-verify Anicca money-maker (/install) and Life Manager (/life-manager) with builder≠verifier loops, then research→draft(human-in-loop)→tournament→distribute the launch. No mock; loop until real evidence.',
  phases: [
    { title: 'Foundation', detail: 'shared scaffold (install.sh, landing layout/nav, ~/anicca skills registry) on the clean unified trunk — 1 builder + 1 verifier' },
    { title: 'Build', detail: 'A∥B subsystems, each: builder (worktree) → adversarial verifier (rubric+artifact only) → loop until LIVE-green (max 3)' },
    { title: 'E2E', detail: 'full live chain: signed telemetry→dashboard, Stripe spawn→droplet→cancel→destroy, 1 real earn tx, REAL Charon phone call to Dais' },
    { title: 'Distribute', detail: 'quarantined research → article DRAFT (human-in-loop: Dais edits) → tournament hook → demo video → multi-platform posts' },
  ],
}

// ----------------------------- schemas (force structured output) -----------------------------
const BUILD = {
  type: 'object', additionalProperties: true,
  required: ['subsystem', 'files', 'summary', 'self_test', 'branch'],
  properties: {
    subsystem: { type: 'string' }, branch: { type: 'string' },
    files: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
    self_test: { type: 'string', description: 'the exact command(s) the builder ran and their result' },
  },
}
const VERDICT = {
  type: 'object', additionalProperties: false,
  required: ['pass', 'evidence', 'gaps'],
  properties: {
    pass: { type: 'boolean' },
    evidence: { type: 'string', description: 'fresh live evidence for EACH rubric point (commands + outputs); empty if not run' },
    gaps: { type: 'array', items: { type: 'string' } },
  },
}
const RESEARCH = {
  type: 'object', additionalProperties: true,
  required: ['facts', 'sources'],
  properties: { facts: { type: 'array', items: { type: 'string' } }, sources: { type: 'array', items: { type: 'string' } } },
}
const DRAFT = {
  type: 'object', additionalProperties: true,
  required: ['path', 'title', 'claims'],
  properties: { path: { type: 'string' }, title: { type: 'string' }, claims: { type: 'array', items: { type: 'string' } } },
}

// ----------------------------- subsystem definitions (DISJOINT file sets, spec26/27) -----------
// model = classify-and-act: opus for hard reasoning / live infra, sonnet for static pages/research.
const A = [
  { key: 'dashboard', model: 'sonnet', spec: 'spec27 A-dashboard',
    rubric: 'apps/landing/app/dashboard/page.tsx fetches /.netlify/functions/dashboard-sync and renders REAL instances numbers; deployed to aniccaai.com (curl 200) and camofox screenshot shows live total_net_worth + leaderboard. No placeholder numbers.' },
  { key: 'install-me', model: 'sonnet', spec: 'spec27 A-install/me',
    rubric: 'apps/landing/app/{install,me}/page.tsx live on aniccaai.com (curl 200); /install is 2-column (cloud product + OSS self-host), shows no raw shell; copy matches spec13/20; camofox visual confirms.' },
  { key: 'stripe-spawn', model: 'opus', spec: 'spec27 A-stripe-spawn',
    rubric: 'apps/landing/netlify/functions/stripe-spawn-webhook.js: a Stripe test checkout.session.completed creates a real DO droplet + Supabase owners row; customer.subscription.deleted destroys it; event.id idempotent. Show the droplet id created then destroyed.' },
  { key: 'earn', model: 'opus', spec: 'spec27 A-earn (GATE-0)',
    rubric: '~/anicca/skills/earn wired into the automaton loop; ONE profitable wake: wallet USDC before/after delta > 0 with a basescan tx status=0x1 recorded in earn-ledger.jsonl. Narration without an on-chain tx = FAIL.' },
  { key: 'self-spawn', model: 'opus', spec: 'spec27 A-self-spawn',
    rubric: '~/anicca/skills/self/spawn births a child instance (DO/Akash) with its OWN wallet addr + OWN AgentMail inbox; child appears in dashboard; child attempts earn on its own wake. Show child systemctl active + distinct wallet.' },
]
const B = [
  { key: 'life-travel', model: 'sonnet', spec: 'spec27 B-travel',
    rubric: '~/anicca/skills/life/travel.js: creating a test gcal event causes a Maps-derived travel block to be auto-inserted before it in gcal (verified by reading gcal back). Applies to chained events.' },
  { key: 'life-call', model: 'opus', spec: 'spec27 B-call (Gemini Charon, bidirectional)',
    rubric: '~/anicca/skills/life/call.js bridges Twilio Media Streams <-> Gemini Live (voice=Charon, male). A REAL outbound call to +818046270314 connects, speaks the next-event guidance, is BIDIRECTIONAL, recording is good, Dais answers. This is a REAL call, not a mock (HARD 0.31/0.24). Provide the recording/transcript + call SID.' },
  { key: 'life-ask', model: 'sonnet', spec: 'spec27 B-ask',
    rubric: '~/anicca/skills/life/ask.js: when an event location/duration is unknown, a question email is sent to Dais Gmail; a reply fills the gcal where (AgentMail inbound webhook). Show the sent email + the gcal update after reply.' },
  { key: 'life-notify', model: 'sonnet', spec: 'spec27 B-notify (email-only approval, Telegram optional)',
    rubric: '~/anicca/skills/life/notify.js: on late-risk, Anicca emails Dais a draft "OK to send to <stakeholder>? reply to approve" (held as AgentMail Draft); Dais email reply "OK" triggers the actual send to the stakeholder. Fully email — NO Telegram required. Show the approval round-trip.' },
]

// ----------------------------- loop-until-LIVE-green helper (/goal) ---------------------------
// builder (worktree) -> SEPARATE adversarial verifier (rubric+artifact only) -> loop, max 3.
async function buildAndVerify(s) {
  let feedback = ''
  for (let i = 0; i < 3; i++) {
    const build = await agent(
      `You are the BUILDER for subsystem "${s.key}" (track ${s.track}). Spec section: ${s.spec} ` +
      `(read docs/superpowers/specs/anicca/27 + 26 + the telemetry plan as the proven template). ` +
      (feedback ? `The adversarial verifier REJECTED the prior attempt — fix exactly these gaps: ${feedback}. ` : '') +
      `Follow SDD + TDD + every CLAUDE.md HARD RULE. Branch off main, implement, write/run tests, commit, ` +
      `and for web/functions deploy via PR->main (main has the --functions GHA). Run a real self_test and report it. ` +
      `Touch ONLY this subsystem's files (disjoint set); never edit install.sh / landing nav / skills registry (Foundation owns those).`,
      { label: `build:${s.key}`, phase: 'Build', schema: BUILD, model: s.model, isolation: 'worktree' }
    )
    if (!build) { feedback = 'builder died'; log(`${s.key}: builder died (iter ${i + 1})`); continue }
    const v = await agent(
      `You are an ADVERSARIAL VERIFIER. You did NOT write this and must not trust the builder. ` +
      `Rubric — EVERY point must hold with FRESH LIVE evidence you gather yourself (no mock, HARD RULE 0.31): ${s.rubric} ` +
      `Artifact: branch=${build.branch}, files=${JSON.stringify(build.files)}, builder_self_test=${build.self_test}. ` +
      `Actively try to REFUTE that it works. Return pass=true ONLY if you personally reproduced live evidence for every rubric point; ` +
      `otherwise pass=false and list concrete gaps.`,
      { label: `verify:${s.key}`, phase: 'Build', schema: VERDICT, model: 'opus' }
    )
    if (v && v.pass) { log(`${s.key}: LIVE-green (iter ${i + 1})`); return { subsystem: s.key, track: s.track, pass: true, evidence: v.evidence } }
    feedback = v ? v.gaps.join('; ') : 'verifier died'
    log(`${s.key}: not green iter ${i + 1} — ${feedback}`)
  }
  return { subsystem: s.key, track: s.track, pass: false, feedback }
}

// =============================================================================================
// PHASE 1 — Foundation (sequential, 1 builder + 1 verifier). Trunk is already reconciled/clean.
// =============================================================================================
phase('Foundation')
const foundation = await agent(
  `Foundation builder: on the unified clean trunk (main), establish the SHARED scaffold both tracks depend on, ` +
  `so the parallel subsystem agents never collide: (1) ~/anicca/install.sh skeleton + skills registry (skills-lock.json) ` +
  `with EARN/SELF/LIFE/REPORT slots, (2) apps/landing app layout + nav linking /install /me /dashboard /life-manager, ` +
  `(3) confirm telemetry+dashboard-sync are live. Branch off main, commit, PR->main. Report files + self_test.`,
  { label: 'foundation', phase: 'Foundation', schema: BUILD, model: 'opus', isolation: 'worktree' }
)
const foundationOk = await agent(
  `Adversarial verifier (you did not build it): confirm install.sh skeleton + skills registry exist with the 4 slots, ` +
  `landing nav links the 4 routes, and aniccaai.com/.netlify/functions/dashboard-sync returns 200. Files=${foundation ? JSON.stringify(foundation.files) : 'none'}. ` +
  `pass only with fresh evidence.`,
  { label: 'verify:foundation', phase: 'Foundation', schema: VERDICT, model: 'opus' }
)
if (!foundationOk || !foundationOk.pass) {
  log('Foundation not green — escalate to Dais before fan-out (shared scaffold must be solid first).')
  return { stopped: 'foundation', foundation, foundationOk }
}

// =============================================================================================
// PHASE 2 — Build A ∥ B. parallel() = barrier: we want ALL subsystems LIVE-green before E2E.
// Each item runs its own builder→verifier loop on a DISJOINT file set (worktree-isolated).
// =============================================================================================
phase('Build')
const subsystems = [...A.map((s) => ({ ...s, track: 'A' })), ...B.map((s) => ({ ...s, track: 'B' }))]
const built = (await parallel(subsystems.map((s) => () => buildAndVerify(s)))).filter(Boolean)
const failed = built.filter((r) => !r.pass)
if (failed.length) {
  log(`BLOCKED subsystems (not LIVE-green after 3 iters): ${failed.map((f) => `${f.subsystem} [${f.feedback}]`).join(' | ')}. Escalating to Dais.`)
  return { stopped: 'build', built, failed }
}
log(`All ${built.length} subsystems LIVE-green. Proceeding to full E2E.`)

// =============================================================================================
// PHASE 3 — E2E (one opus verifier runs the whole live chain end-to-end, incl. the real call).
// =============================================================================================
phase('E2E')
const e2e = await agent(
  `Final E2E verifier (independent context). Run the WHOLE live chain and return pass only with fresh evidence per HARD 0.31: ` +
  `(a) a genesis wake posts signed telemetry -> dashboard-sync reflects real on-chain net worth; ` +
  `(b) a Stripe test subscription spawns a real DO droplet then cancel destroys it; ` +
  `(c) at least ONE real earn tx (basescan status=0x1) landed in a wallet; ` +
  `(d) a REAL Charon (Gemini Live) bidirectional phone call to +818046270314 connected, guided the next event, recording good, Dais answered. ` +
  `List the tx hashes, droplet id, dashboard numbers, and call SID/recording.`,
  { label: 'e2e', phase: 'E2E', schema: VERDICT, model: 'opus' }
)
if (!e2e || !e2e.pass) { log(`E2E not fully green: ${e2e ? e2e.gaps.join('; ') : 'verifier died'} — escalate to Dais.`); return { stopped: 'e2e', built, e2e } }

// =============================================================================================
// PHASE 4 — Distribute. quarantine: read-only researchers; the writer/distributor never see raw
// scraped HTML, only structured facts. Article = HUMAN-IN-LOOP (draft only; Dais edits & approves).
// =============================================================================================
phase('Distribute')
const ANGLES = [
  'Anicca thesis + real proof: what was built and the live numbers (net worth, dashboard)',
  'Dynamic Workflows explainer: the 6 patterns + OUR real build log (round3 prod float bug, round4 deployment-reality, dev<->main reconcile, injection guard)',
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

// adversarial claim-check each draft (separate context; sources only)
const claimChecks = await parallel(drafts.map((d) =>
  () => agent(`Adversarial claim-verifier: check EVERY claim in draft "${d.title}" (${d.path}) against the sources ${JSON.stringify(research.flatMap((x) => x.sources))} and the live repo/prod. Flag any unverified or exaggerated claim.`,
    { label: `claimcheck:${d.title.slice(0, 20)}`, phase: 'Distribute', schema: VERDICT, model: 'opus' })
)).then((r) => r.filter(Boolean))

// HUMAN-IN-LOOP gate: the workflow STOPS here with the drafts. Dais edits/approves OUTSIDE the WF,
// then a separate (gated) distribute step posts to Postiz(X)/Slack/TikTok(reelfarm)/Product Hunt +
// builds the demo video (skills/video, Remotion). We do NOT auto-publish unreviewed copy.
log('Drafts ready + claim-checked. PAUSE for Dais edit/approval before any publish (human-in-loop). Distribution + demo video run as a gated follow-up once approved.')

return {
  foundation: foundationOk?.pass,
  built: built.map((b) => ({ subsystem: b.subsystem, pass: b.pass })),
  e2e: e2e?.pass,
  drafts: drafts.map((d) => ({ path: d.path, title: d.title })),
  claimChecks,
  next: 'Dais edits articles -> approve -> gated distribute (Postiz/Slack/TikTok/PH) + demo video',
}
