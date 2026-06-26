# SPEC — A3: de-Automaton the note publisher (VSDD behavioral contract)

Date: 2026-06-26 · Feature: `de-automaton-note-publisher` · Mode: lean · Language: python
Builder = main agent (me). Adversary = fresh `vcsdd:vcsdd-adversary` (zero builder context).

## GOAL
The note render+publish pipeline runs **ANY** AI-entity article, selected by env vars, with NO Automaton-specific
value hardcoded in the code path and NO `/tmp` writes. Default env (all unset) reproduces the current Automaton
behavior byte-for-byte so the live note cron is unchanged.

## FILES IN SCOPE (absolute)
- `/Users/anicca/.openclaw/skills/ai-entity-article-writer/scripts/note-stage1-render.py`  (render tables/mermaid → manifest)
- `/Users/anicca/.openclaw/skills/ai-entity-article-writer/scripts/note-stage2-publish.py`  (upload images + update_article DRAFT)
- `/Users/anicca/.openclaw/skills/ai-entity-article-writer/scripts/note-publish/rebuild-note-body.py`  (one-off restore; tags only)

## ENV CONTRACT (defaults in parentheses = current Automaton values)
| env | meaning | default |
|---|---|---|
| `NOTE_SRC` | source markdown path | `/Users/anicca/.cache/anicca-article-wt/docs/articles/2026-06-11-automaton-jp.md` |
| `NOTE_WORK` | temp work dir (replaces every `/tmp/...`) | `~/.cloak/note-work/note-stage` |
| `NOTE_NUM` | note internal article id | `166686292` |
| `NOTE_INFOG` | env OVERRIDE for the infographic. Default = the article's OWN infographic that stage1 captured into the manifest (`images/<NOTE_IMG_DIR>/what-is-*.png`, resolved vs the article dir). empty/missing ⇒ drop `@@INFOG@@`. NO Automaton fallback. | (none — stage1-captured) |
| `NOTE_TAGS` | comma-separated tags | `AI,AIエージェント,暗号資産,Automaton,自律AI` |
| `NOTE_IMG_DIR` | image subdir under `images/` used by the thumb/infographic strip | `automaton` |

Cookies path stays as the pipeline already wires it (extract-note-cookies → the same file stage2 reads); only the
`/tmp` *temp render* paths (tbls/figs/manifest) move under `NOTE_WORK`.

## INVARIANTS (must all hold = the test oracle)
- **INV-1 no-regression**: with NO env set, `note-stage1-render.py` on the default source prints the SAME
  `title` + `tables=N` + `mermaids=M` as the pre-change run, and writes the manifest under `NOTE_WORK`.
- **INV-2 no-Automaton-leak**: with `NOTE_SRC` = a non-Automaton test md + `NOTE_TAGS=foo,bar` + `NOTE_IMG_DIR=demo`,
  grep of the produced manifest + the script source's *runtime values* shows NO literal `automaton`, NO `166686292`,
  NO the JP md path baked into the output. (The code may keep them only as env DEFAULTS.)
- **INV-3 no-/tmp**: `grep -n "/tmp/" note-stage1-render.py note-stage2-publish.py` ⇒ 0 hits.
- **INV-4 draft-only**: `note-stage2-publish.py` still calls only `update_article` (draft_save), never `publish_article`.
- **INV-5 generic image strip**: the thumb/infographic regex matches `images/<NOTE_IMG_DIR>/...`, not a hardcoded `automaton`.

## EDGE CASES
- article with 0 tables / 0 mermaid / no infographic ref / no thumb ref → no crash, markers cleanly dropped.
- `NOTE_TAGS` empty → tags = [] (no crash).
- `NOTE_WORK` missing → created (`makedirs(exist_ok=True)`).

## ERROR
- missing `NOTE_SRC` file → fail loudly (FileNotFoundError is acceptable; not a silent empty render).

## DONE = 4-D convergence
spec ✓ (this file, committed) · test ✓ (RED→GREEN check of INV-1..5) · impl ✓ (params landed) ·
verification ✓ (fresh `vcsdd:vcsdd-adversary` binary PASS on all dimensions + NO-MOCK E2E: real stage1 run, INV-1 + INV-2).
