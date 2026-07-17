# F4a — publish-to-zenn (draft → verify → publish) — spec (VSDD) — 2026-06-24

Zenn is FUNDAMENTALLY different from note: it is GIT-based, not browser-based. Existing assets (found):
- Content repo: `~/.openclaw/workspace/zenn-articles/` → GitHub `Daisuke134/zenn-articles` → Zenn auto-renders
  every `articles/*.md`. (Dais already connected this; Zenn publishes on push.)
- Existing script: `~/.openclaw/skills/article-writer/scripts/post-zenn.py` (copies a draft → articles/<slug>.md,
  commit + push; frontmatter must have published:true).
- Local preview: `~/.openclaw/external/zenn-editor` (zenn-cli) → `npx zenn preview` renders locally.

## How Zenn publishing works (the mental model — git, declarative)
- An article = `articles/<slug>.md` with frontmatter: `title, emoji, type(tech|idea), topics[], published`.
- `published: false` = DRAFT — pushed to GitHub but Zenn shows it ONLY to the author (not public).
- `published: true` = LIVE — public on zenn.dev.
- Publishing = a git commit + push. There is NO browser, NO eyecatch upload, NO paywall. Mermaid renders
  NATIVELY (```mermaid), so NO PNG conversion (unlike note). Images = repo-relative or URLs.
- Monetization on Zenn = バッジ (readers tip) on a FREE article. No paywall. So the Zenn article is the FREE
  reach/SEO piece that LINKS to the paid note (for the experiment logs). (Zenn Books = paid, out of scope.)

## The pipeline (draft → verify → publish) — mirrors note's discipline, git-native
1. ADAPT the markdown for Zenn: Zenn frontmatter; keep ```mermaid native (drop the note PNG figures); drop
   note-only bits (eyecatch slot, membership/paywall, the auto-目次 — Zenn auto-renders a 目次 from headings,
   and our heading rule already keeps it short: section titles = ## , sub-points = bold). End with a link to
   the paid note. Write `articles/<slug>.md` with `published: false`.
2. ★ VERIFY (vision, BEFORE public) ★: `npx zenn preview` (zenn-cli, localhost) → open it in cloakbrowser →
   screenshot → Read it → judge: layout, mermaid renders, images, headings/目次, Japanese not slop, the
   note link present. Deterministic: the md has `published: false` at this point. (No GitHub login needed —
   local preview.)
3. PUBLISH: only after the vision check passes → set `published: true` → git commit + push → Zenn live.
   Verify the live URL (HTTP 200, renders).

## Safety gate (the Zenn analogue of note's publish_guard)
- DRAFT-SAFE BY DEFAULT: a script/agent writes `published: false`. Going public = flipping ONE flag to true +
  push. The scheduled/unattended path NEVER flips to true (same idea as NOTE_FORCE_DRAFT) — it leaves drafts.
- Deterministic gate: `publish-to-zenn.sh publish` refuses to set `published: true` / push-as-published unless
  NOTE_MODE=go AND a fresh sentinel (reuse the F3 publish_guard pattern), so an unattended agent can only draft.
- ★ SECURITY (VSDD finding, pre-spec): the repo remote embeds a GitHub PAT in the URL (https://ghp_...@github).
  FIX in build: rotate the token + move it to a git credential helper / SSH (post-zenn.py already references an
  SSH key — make the remote SSH and drop the inline PAT). Do not commit/echo the token. ★

## Build plan (NOT this turn — Dais reviews the flow first)
- `publish-to-zenn.sh draft <md> --slug <s>` → adapt + write articles/<slug>.md (published:false), commit+push.
- `publish-to-zenn.sh verify <slug>` → npx zenn preview + cloakbrowser screenshot → evidence for the agent vision.
- `publish-to-zenn.sh publish <slug>` → (gated) set published:true + commit + push; then live-URL check.
- Reuse F2's claude -p agent loop (write → draft → vision verify → publish-when-go) with the Zenn scripts.
- VSDD: spec (this) → adversary review of the spec → build → adversary review of the build → converge.

## Acceptance
A draft pushed with published:false is NOT public; `zenn preview` + screenshot lets the agent judge; flipping to
published:true + push makes it live (verified by HTTP 200). Unattended path can only ever draft. PAT rotated.

## ZENN/X CONTENT + MONETIZATION STRATEGY (Dais 2026-06-24, locked)
- ZENN ARTICLE = EXPLAINER ONLY: include up to「Automatonは「どう動いて」生きているのか」+ the 結論(conclusion)
  final block. DO NOT include the setup / run steps / results / logs (those are the paid note content).
- ZENN TITLE must NOT lie: the current note title「…実際に動かして検証してみた」claims we ran it — but Zenn omits
  the running. So the Zenn title = 「人間なしで"自分で稼ぐ"AI『Automaton』を徹底解説」(徹底解説 = thorough explainer).
- ZENN MONETIZE = ①バッジ/投げ銭 on the free article ②every 5–10 articles, compile a PAID Zenn BOOK containing the
  FULL thing we sell on note (setup+results+logs); if quality is high, a print/hardback too. Books = the Zenn revenue.
- X = made Premium (DM + Subscriptions). Model = free article preview; SUBSCRIBE to see the FULL article. Same
  free-hook → paid-full shape as note.
- note PAYWALL MOVE (Dais 2026-06-24): the subscribe line moves EARLIER to 「実際に動かす（手順と、起きたこと）」—
  specifically before「Automatonをゼロから動かす手順を、実際に出た結果とともに記録します。同じコマンドをそのまま
  なぞれば再現できます。」 → from there down = paid. Free = [0]–[4] + the 実際に動かす heading + that intro line.

## VSDD SPEC ITERATION 1 — FIXES (supersede anything above that conflicts) — 2026-06-24
Adversary iteration-1 = FAIL (8 findings, all real). Resolutions:

FIND-001/007 SECURITY (PAT leak in zenn-articles/.git/config, https-PAT remote, SSH inert):
- Concrete fix (do FIRST in build): (1) rotate the leaked `ghp_…` token in GitHub → Settings → Developer settings →
  PATs → revoke + reissue (or delete if a deploy key is used). (2) `git -C ~/.openclaw/workspace/zenn-articles
  remote set-url origin git@github.com:Daisuke134/zenn-articles.git` (SSH, uses ~/.ssh/id_ed25519). (3) verify
  `GIT_SSH_COMMAND="ssh -i ~/.ssh/id_ed25519" git -C … push` works (add the pubkey as a repo deploy key if not).
  (4) NEVER echo/commit the remote URL; scrub any tokenized URL from ~/.openclaw/logs/article-writer/*. Secrets
  move via SSH/credential-helper, never inline. (memory: feedback_never_echo_secrets_rotate_on_leak.)

FIND-002/003 SAFETY GATE (git-native, NOT the browser publish_guard which is a mismatch):
- BRANCH MODEL: Zenn watches `main` only. ALL unattended/draft work commits to a `draft` branch that Zenn does
  NOT render. Publishing = a GATED, deliberate merge `draft → main` (the only thing that can make content public).
- So the deterministic gate = the scheduled/unattended path can ONLY push to `draft` (never `main`, never merge) →
  it can NEVER publish, regardless of the `published:` flag. publish-to-zenn.sh `publish` (merge to main) requires
  the same enable-sentinel + NOTE_MODE=go as note (publish-to-note.sh enable-publish). post-zenn.py's unconditional
  `git push origin HEAD` is REPLACED by this gated, branch-aware pusher.
- Belt-and-suspenders: drafts also carry `published:false`; publishing flips to `published:true` AND merges to main.

FIND-004 CONTENT / NO-LIE (the 結論 cites results — $17 burned / $0.17 profit — which Zenn omits):
- Zenn article = EXPLAINER ONLY: blocks 1–5 (Automaton とは → どう動いて). EXCLUDE 実際に動かす AND で、稼げたのか
  AND the original 結論 (it cites the run results = would be a lie in a no-run explainer).
- Replace with a SHORT, HONEST Zenn-specific closing = a genuine takeaway about what Automaton means / who it
  is for, with NO result numbers and ★ NO "read the rest on the paid note" upsell link ★ (Dais 2026-06-24:
  "we don't need a note 誘導 link — that is very bad. we are sincere; we get paid but never do unethical stuff").
  The Zenn article is a COMPLETE, standalone, honest free explainer. Title 徹底解説 is honest (pure explainer).
- Zenn monetization is therefore ONLY バッジ/投げ銭 (organic tips) + a future paid Zenn Book — never a paywall
  link or clickbait. The 最後に block = the genuine anicca/author closing (no upsell).

FIND-005 IDEMPOTENCY (slugify date+title → creates NEW articles every run; JP slugs invalid):
- Use a STABLE, valid Zenn slug (a-z0-9 + hyphen, 12–50 chars): `automaton-jido-kasegu-ai-kaisetsu`. The publisher
  OVERWRITES `articles/automaton-jido-kasegu-ai-kaisetsu.md` if it exists (never date-prefixed, never create-new).

FIND-006 IMAGES + VERIFY (relative PNGs not in the zenn repo → 404 live; local preview ≠ production):
- Images: COPY the needed PNGs (the explainer figs only — Web4.0, 全体像, どう動いて diagrams; NO infographic, NO
  paid-section tables/fund shots) INTO the zenn-articles repo under `images/automaton/` and reference them
  repo-relative, so they resolve on zenn.dev. Mermaid stays native (```mermaid). 
- VERIFY = TWO gates: (a) local `npx zenn preview` + screenshot (fast first look), AND (b) the LIVE gate after a
  draft push: confirm the article is NOT in Zenn's public list/API (still draft) AND the author preview on
  zenn.dev renders every mermaid + every image with NO 404. "HTTP 200" alone is insufficient.

FIND-008 ASSERTABLE ACCEPTANCE (was prose):
1. draft push → `GET https://zenn.dev/api/articles?username=…` does NOT list the slug (still non-public).
2. after gated publish (merge to main, published:true) → the public URL returns 200 AND the page contains the
   title text AND renders ≥1 mermaid + ≥1 image (no 404 on image requests).
3. the Zenn md contains NONE of: 「17ドル」「0.17ドル」「実際に動かす」「で、稼げたのか」「検証は3段階」 (no paid/results text).
4. slug == `automaton-jido-kasegu-ai-kaisetsu` (a-z0-9-), and re-running draft does NOT create a 2nd file.
5. `git -C zenn-articles remote -v` shows an SSH remote (no `ghp_` token anywhere).

## VSDD SPEC ITERATION 2 — FIXES — 2026-06-24
Iter-2 = FAIL (FIND-009..012). Iter-1 fixes mostly landed; these close the residuals. All verified on disk.

FIND-009 (content leak inside kept block 1): block 1「Automaton とは」 itself has a 結果： sub-block at SOURCE
  LINES 19–24 of the article md that cites `$0 / $17 / +$0.17 / 約80分`. The Zenn adapter MUST DELETE source
  lines 19–24 (the 結果 bullets) as well — keep only the non-results framing of「Automaton とは」. So the Zenn
  cut = remove: lines 19–24 (block-1 結果 bullets) + everything from `## 実際に動かす` (line 448) to the article
  end (実際に動かす + で、稼げたのか + 結論). The Zenn body = blocks 1–5 minus the block-1 結果 bullets, + an
  honest no-numbers closing (no upsell, no note link).

FIND-010 (tautological grep): acceptance criterion 3 banned kanji-yen「17ドル」「0.17ドル」 but the source uses
  the `$`-form. CORRECTED ban-list (the Zenn md must contain NONE of these EXACT strings):
  `$17`  `$0.17`  `＋$0.17`  `+$0.17`  `0.17`  `80分`  `数十円`  `実際に動かす`  `で、稼げたのか`  `検証は3段階`
  `17ドル`  `0.17ドル`. (grep -F each; any hit = FAIL.)

FIND-011 (gate premise unverified): the "Zenn watches main only" claim MUST be verified in the build, not
  assumed. BUILD STEP: confirm the Zenn deploy branch (Zenn dashboard → repo settings, or the GitHub-App config)
  == `main` and is NOT "all branches". If Zenn renders all branches, the draft-branch gate is VOID → fall back to
  `published:false` as the only gate and DO NOT rely on a draft branch. The pusher MUST push to the EXPLICIT
  draft branch (`git push origin draft`), never `git push origin HEAD`/`main` — replacing post-zenn.py:100.
  Acceptance: a draft push leaves nothing new on `main` (git rev-parse origin/main unchanged).

FIND-012 (PAT scrub incomplete): besides ~/.openclaw/logs/article-writer/*, scrub the token from
  `~/.openclaw/workspace/zenn-articles/.git/logs/` (reflogs may hold the tokenized URL) and from shell history
  (`~/.zsh_history`, `~/.bash_history`). ACCEPTANCE ASSERTION (not just an instruction): the old token is REVOKED
  — `curl -s -o /dev/null -w '%{http_code}' -H "Authorization: token ghp_…" https://api.github.com/user` returns
  `401`. "Done" cannot be claimed while the token still authenticates.

## VSDD SPEC ITERATION 3 — FIXES — 2026-06-24
Iter-3 = FAIL on 2 (4/6 dims PASS; all iter-2 findings RESOLVED). The content-cut was still incomplete — run-
promise / next-chapter sentences survive in the kept blocks and would make the 徹底解説 (no-run) explainer claim
it ran Automaton and point at deleted chapters (same lie-class as FIND-004/009).

FIND-013 (content — run-promises in kept blocks 1–5): the Zenn adapter MUST also remove/rewrite these source
lines (of /Users/anicca/.cache/anicca-article-wt/docs/articles/2026-06-11-automaton-jp.md):
  - L44 「…実際の動かし方と、動かしてみた結果をお伝えします」 → cut the run-promise clause (keep only the explainer
    intent, e.g. 「Automatonを分かりやすく解説します」).
  - L391 / L406 / L422 forward-refs 「次の章で…動かす / 動かしてみる」 → rewrite to remove the forward reference to
    the deleted chapters (state the concept without "次の章で動かす").
  Net Zenn cut = remove: L19–24 (block-1 結果) + L44 run-promise + L391/L406/L422 next-chapter refs + L448→end
  (実際に動かす + で稼げたのか + 結論). Result = a pure explainer that never claims a run and never dangles a
  deleted section. Honest no-numbers closing, no upsell/note link.

FIND-014 (acceptance — numeric blacklist misses phrase-lies): ADD a PHRASE ban to acceptance criterion 3 — the
  Zenn md must contain NONE of: `次の章` `動かしてみた結果` `動かしてみたら` `実際の動かし方` `動かして検証`
  (grep -F each; any hit = FAIL), in addition to the numeric ban-list. Plus a positive check: the Zenn title is
  `…徹底解説` and the body contains no first-person run claim.

## VSDD SPEC ITERATION 4 — FIXES — 2026-06-24
Iter-4 = FAIL on 2 residual run-claims (4/6 dims PASS; all prior findings RESOLVED, no regression). Final cuts:

FIND-015: the 「やったこと：」 block at source L15–17 is a first-person run+test claim (「実際にお金を入れて動かし、
  本当に稼げるのかを検証」「ClawRouterで頭脳をつないで動かしました」). ADD L15–17 to the Zenn cut list (remove, or
  rewrite to non-run framing). So the COMPLETE Zenn cut = remove source lines: L6 (see FIND-016) + L15–17 (やった
  こと) + L19–24 (結果) + L44 (run-promise) + L391/L406/L422 (next-chapter refs) + L448→end (paid sections).
  After this, blocks 1–5 contain NO first-person run/test claim and NO reference to a deleted section.

FIND-016: the thumbnail alt-text at source L6 「人間ゼロで自分で稼ぐAI Automaton を動かしてみた」 is a run-claim that
  would render on the live Zenn page. For Zenn we DROP thumb.png entirely (Zenn uses emoji + auto-OG, not an
  in-body cover) → remove the L6 image ref. ALSO add to the FIND-014 phrase-ban: `動かしてみた` `動かしました`
  `動かして` (grep -F each; any hit in the Zenn md = FAIL). Net acceptance no-lie gate = numeric ban-list +
  phrase ban {次の章, 動かしてみた結果, 動かしてみたら, 実際の動かし方, 動かして検証, 動かしてみた, 動かしました,
  動かして} + title==…徹底解説 + no first-person run claim.

## VSDD SPEC ITERATION 5 — FIX — 2026-06-24
Iter-5 = 5/6 PASS. Content/no-lie now PASSES (cut complete, zero surviving run-claims). One residual:

FIND-017 (acceptance grep over-broad — false-positives a CORRECT article): the bare token `動かして` in the
  phrase-ban is a substring of legitimate KEPT prose (source L189 「heartbeat だけを常時動かして見張る」, L107
  「AIエージェントが動かしているお金は…$50M」) — both third-person descriptions, NOT run-claims. A no-lie gate
  that fails a truthful artifact is wrong. FIX: REMOVE the bare `動かして` from the ban-list and ANCHOR to the
  actual run-claim strings instead. Final acceptance no-lie phrase-ban (grep -F each; any hit = FAIL):
    `次の章`  `動かしてみた`  `動かしてみた結果`  `動かしてみたら`  `動かしました`  `実際の動かし方`  `動かして検証`
    `を動かしてみた`  `実際にお金を入れて動かし`  `頭脳をつないで動かしました`
  (all of these are fully inside the cut lines L6/L15-17/L44/L391/406/422 — they cannot appear in a correct Zenn
  body; none is a substring of the kept third-person prose at L107/L189.) Plus the numeric ban-list + title
  ==「…徹底解説」 + the positive "no やったこと block, no first-person 私たち…動かし/検証 sentence" check.
