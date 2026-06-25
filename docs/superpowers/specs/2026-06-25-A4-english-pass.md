# A4 — English pass (translate + onboarding + de-slop) → EN platforms → skill — 2026-06-25

VSDD. Builder = me; gate = fresh vcsdd:vcsdd-adversary. Make the ai-entity-article-writer skill ship an English
version of any AI-entity article, cleanly, no human in loop. Source = the Automaton article.

## CONTRACT
Input = the JP article md. Output = a clean EN article published to dev.to (free) [+ X-EN, Substack-EN later].
1. TRANSLATE EVERYTHING (not just body): body prose + EVERY markdown table cell + EVERY ```mermaid node label +
   every heading + the cover/眉出し image text. Tables + mermaid are RE-RENDERED from the EN markdown (render-tables-
   autofit / kroki), so their EN content must live in the markdown. Cover/heading PNGs with baked text → regenerate EN.
2. DE-SLOP with the stop-slop skill (MIT, ~/.claude/skills/stop-slop): cut filler/adverbs, active voice, no em-dash,
   vary rhythm, be specific, score ≥35/50. EN playbook: write for a total beginner, define each term on first use,
   name real things (Conway, Base, USDC, ERC-8004), honest, no funnel/upsell link (free explainer).
3. ADD an ONBOARDING section ("Getting started", before the closing CTA): the process is EASY —
   (1) Buy USDC on Coinbase. (2) Send it to your Anicca instance's wallet address (shown on the dashboard).
   (3) No API key needed; fund the wallet and it uses better models. Matches the launch promise.
4. RENDER the EN visuals from the EN md (tables → clean HTML PNG; mermaid → kroki PNG; cover → EN).
5. PUBLISH to dev.to (publish-devto.sh, DEVTO_API_KEY set) as the first EN channel → verify the live render by eye.
6. SKILL: en-adapt step + en-agent-prompt.md (the claude -p loop: translate → de-slop → render EN → publish → verify)
   so ANY future article ships EN with one tap. Same verify-in-loop discipline as the JP per-platform agents.

## DONE = 4-D convergence
spec ✓ + EN md (all visuals' text translated + onboarding + de-slopped ≥35/50) ✓ + dev.to live + eye-verified ✓ +
fresh adversary PASS ✓. "It translated" ≠ done — every table/diagram must render in English and read human.
