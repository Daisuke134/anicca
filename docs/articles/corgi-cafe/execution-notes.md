# GOAL — Corgi Cafe EN translation → X Articles DRAFT (no publish)

## Outcome
An English X Articles DRAFT exists for the Corgi Cafe (SF) article, faithful in
content and structure to the JP version Dais hand-edited and published
(`docs/articles/corgi-cafe/article-jp.md`), written in natural native English
(not literal translation), with all 9 photos in the correct positions, cover
image set, italic caption under the counter photo (Boardy line), and zero raw
markdown markers leaked into the rendered body. Hand-off: Dais clicks Publish.

## Evidence (Done = ALL true)
- `docs/articles/corgi-cafe/article-en.md` exists, applies EN-equivalent of
  ai-entity-article-writer lessons #27-40, passes EN stop-slop check (no
  em-dash, no -ly adverbs of consequence, no "Here's the thing"/"dive deep").
- A new X Articles draft URL (`/compose/articles/edit/<NEW_ID>`) returned by
  `publish_md_to_x.py`, distinct from the JP article id 2070819168853622784.
- CloakBrowser daily-driver scroll-screenshots of the EN draft, every section
  read by me. Each check passes:
  (a) image count = 9 in rendered body (cover + 8 content)
  (b) italic caption rendered below counter photo (or limitation logged)
  (c) section order matches markdown
  (d) no raw `**`, `*`, backticks, leftover `>` blockquotes, no `---` markers
  (e) EN reads naturally (no JP→EN translationese)

## Constraints
- DRAFT ONLY. NEVER publish. Dais hits Publish himself.
- Source = `article-jp.md` (= Dais published version, byte-for-byte).
- Browser = CloakBrowser daily-driver :9222 (HARD 0.39). camofox = fallback only
  if CDP unreachable AND CloakBrowser cannot be revived.
- Currency: keep USD `$` in EN (native), don't back-translate `200万ドル` → don't
  add `(200万ドル)`. `$100k`, `$2M`, `$5,000`, `$6.43` all stay native EN.
- Personal names stay roman: Nico, Emily, Trudy.
- DON'T re-add [0] verdict box (Dais cut it).
- DON'T re-add 結局 / "In conclusion" summary block (Dais cut it).
- Photo caption under counter photo: italic line about Boardy (per lesson #33).
- One wish-line near the customer-mix paragraph (per lesson #34).
- Opinion-H2 form for the hiring-flyer section (per lesson #35).

## Iteration policy
- Round 0: publish first attempt. Screenshot top-to-bottom. Read all.
- For each defect: fix article-en.md OR publish_md_to_x.py call, redo publish.
- Loop until all 5 evidence checks (a–e) pass.
- Max 5 iteration rounds. Block-stop if defect persists past round 5.

## Block-stop conditions
- CloakBrowser :9222 unreachable AND `cloakbrowser launch` fails 3x → fall back
  to camofox per HARD 0.39 escalation rule, document the deviation.
- X Articles editor refuses paste 3 consecutive times despite retry-rescue →
  report state, evidence, attempts, exact blocker.
- Caption insertion truly impossible (no captionable element under Draft.js
  figure block) → ship draft without caption, log as known engine gap #9.

## Run rules
- Report progress only on tool-verified facts (no "looks fine" without read).
- Never end a turn on a plan or promise; end on evidence or a block-stop.
- Update this file's "## Open items" section after every iteration round.
- Don't silently change Outcome / Evidence / Constraints. If amendment needed,
  STOP and ask Dais.

## Final report (when Done)
- New draft URL
- Iteration round count
- Screenshot paths read
- Any limitations hit (e.g. caption gap)
- Hand-off message: "Ready for your Publish click."

---

## Open items (live, updated each round)
- [ ] R1: write article-en.md
- [ ] R1: invoke publish_md_to_x.py article-en.md
- [ ] R1: scroll-screenshot draft via CloakBrowser
- [ ] R1: read all screenshots, list defects
- [ ] (loop until 0 defects)
- [ ] report-back to Dais
