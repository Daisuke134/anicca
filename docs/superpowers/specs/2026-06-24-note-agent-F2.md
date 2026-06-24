# F2 — the `claude -p` note agent (writing + VISION pre-post gate) — spec — 2026-06-24

Goal: a self-contained `claude -p` agent that runs the WHOLE no-human note pipeline and, crucially, LOOKS at
the rendered draft (vision) and judges it before anything goes public. This is the piece a deterministic
script can't be: the writing AND the taste/quality verdict both need an LLM. publish-to-note.sh (F1) = the
hands; this agent = the eyes + brain.

## Inputs (env or args, passed into the prompt)
- TOPIC (write a new article) OR MD (an existing markdown path) ; NOTE_KEY (existing) or "new" ; PRICE (500) ;
  PAYWALL_BEFORE ("<heading text the paid section starts at>") ; EYECATCH (image path, optional).

## The loop the agent runs
1. If TOPIC: invoke the ai-entity-article-writer skill → research → draft (JP) → de-slop + language-purity →
   figures/eyecatch. Output = one markdown. If MD given: use it.
2. `publish-to-note.sh publish <md> --key <k> --price <p> --paywall-before "<h>" [--eyecatch img] --mode draft`
   (renders + uploads + eyecatch + manual 目次 + 試し読み line + membership, but STAYS A DRAFT).
3. `publish-to-note.sh verify <k>` → deterministic evidence + a NO-cookie visitor screenshot path.
4. **Read the screenshot** and judge the VERIFY CHECKLIST below. Also read the deterministic JSON.
5. Decision:
   - ALL pass → (only if AUTONOMY enabled) re-run with `--mode go`, then verify again. Else STOP at draft.
   - ANY fail → fix the specific step (re-run eyecatch / 目次 / gate) and re-verify, up to 3 rounds.
     Still failing → Telegram Dais the screenshot + what's wrong; do NOT publish.
6. Report to Dais (Telegram): live URL (if published) or draft URL + the screenshot + the checklist verdict.

## VERIFY CHECKLIST (the vision criteria — the anti-slop gate)
Read the visitor screenshot and confirm EACH (cite what you see):
- [ ] eyecatch (cover image) renders at the top, not broken, not duplicated in the body
- [ ] 目次 = MANUAL big titles only (NO long auto-`<table-of-contents>` wall)
- [ ] all images render at a sane size (tables/figures not crushed, infographic readable)
- [ ] the paywall gate sits before the paid section (PAYWALL_BEFORE) with the ¥PRICE「参加手続きへ」CTA
- [ ] headings intact — no merged/broken heading text (e.g. "…何Automaton とは")
- [ ] Japanese reads human (no AI-slop tells: 全角ダッシュ, 命題型H2, 偏愛語 — run stop-ai-slop-jp judgment)
- [ ] title + teaser coherent; free part is genuinely useful (hook), paid part is the exclusive data
Plus deterministic (from verify-note.py JSON): can_read=false (gated), eyecatch=true, price=expected.

## AUTONOMY FLAG (Dais's "prepare the tap, don't tap yet")
- Default = `AUTONOMY=off` → the agent does steps 1-4 + 6, STOPS at the draft, and asks Dais to review. It does
  NOT click --go on its own. This matches "stage everything, automate later with one tap."
- Flipping `AUTONOMY=on` (the tap) lets step 5 publish automatically once the checklist passes. Set only after
  the skill is proven across a few hand-reviewed articles.

## Build
- `note-agent-prompt.md` — the self-contained prompt (this loop + checklist + the AUTONOMY rule).
- `run-note-agent.sh` — wraps `claude -p "$(cat note-agent-prompt.md)\n\nINPUTS: ..." --allowedTools
  "Read,Bash,Write,Edit" --dangerously-skip-permissions`. (later: launchd calls this = F3.)

## Acceptance (verify NOW)
A scoped `claude -p` run of JUST the gate — "run publish-to-note.sh verify na3a631e63d1a, Read the screenshot,
judge the checklist, output JSON {verdict, reasons}" — returns a structured PASS with reasons that reference
what it actually saw (eyecatch, 目次, gate). That proves the vision-gate-in-an-agent-loop works headless.
(The full write→draft→go E2E runs on the next real article, AUTONOMY still off.)
