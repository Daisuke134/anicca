# Purity Boundary Audit — fable5-config-slimdown (Phase 5, Formal Hardening)

Per `specs/verification-architecture.md` §Purity boundary map, the entire verification surface
(`tests/verify.sh`) is declared **Pure (read-only)**; all effectful work (file edits, deletes,
moves, commits, pushes) belongs to the *implementation* step, which is out of scope for this
script. This audit mechanically confirms `tests/verify.sh` contains no write-capable command.

## Declared Boundaries

Declared in specs/verification-architecture.md purity boundary map: tests/verify.sh is read-only (pure observation); implementation (Phase 2b) is the only side-effect layer; NL judgment is delegated to fresh-context adversary.

## Method

Grepped `tests/verify.sh` (373 lines) for every shell token that can mutate filesystem state:
`>` / `>>` (redirection to a real file), `mv`, `cp`, `rm`, `sed -i`, executed `tee`, `mkdir`,
`touch`, `chmod`, `chown`. Every hit was manually classified as (a) a real write, (b) a
comparison/discard that touches no persistent file, or (c) a false positive (comment prose or a
string literal that is only ever *compared against*, never executed).

## Observed Boundaries

### Redirection (`>`, `>>`)

Grep for `>` not immediately followed by `/dev/null` and not part of `->` found 6 occurrences:

| Line | Content | Classification |
|---|---|---|
| 31 | `# report <PROP-ID> <PASS\|FAIL\|SKIP> <one-line description>` | Comment prose — `>` is a doc-comment angle bracket, not shell syntax |
| 88/96 | `# ... evidence log exists with >=27 lines` / `"... >=27 recorded grep runs ..."` | Comment prose / string literal — `>=` numeric-comparison English text, not shell redirection |
| 146/147 | `jq -c '... \| length > 0)) \| sort'` | `jq`'s own `>` numeric-comparison operator inside a jq filter string, not a shell redirect |
| 262 | `'claude -p "$PROMPT" --model opus --output-format text 2>&1 \| tee -a "$LOG"'` | This entire string is the **6th positional argument** (`expected_launch`) passed to the `p7a_one` function, which only ever does `sed -n "${curr_launch}p" "$abs"` and a string-equality comparison (`[ "$actual_launch" = "$expected_launch" ]`) against it — it is data being compared, never `eval`'d or executed by `verify.sh`. `verify.sh` never runs a `tee` command; it only checks whether *another file* (an already-implemented loop-CLI script) contains this literal text on a specific line. |

All `>/dev/null` occurrences (13 in the script, at lines 141, 151, 154, 181/182/183, 191/192,
230/231, 281/282, 285, 324-327) redirect only to the null device — this is a standard "run for
exit-code only" idiom, not a write to any real, persistent file.

**Conclusion**: zero shell redirections write to a real file anywhere in `tests/verify.sh`.

### `mv`, `cp`, `rm`, `sed -i`, `mkdir`, `touch`, `chmod`, `chown`

Grep for these tokens as standalone words: **0 occurrences** in the entire file. The script never
moves, copies, deletes, or creates a file, and never in-place-edits anything with `sed -i`.

### `sed -n` (read-only variant, used twice)

Lines 230-231 and 235:
```
diff <(git -C "$ANICCA_REPO" show "HEAD:skills/${relpath}" 2>/dev/null | sed -n "${start},${end}p") \
     <(sed -n "${start},${end}p" "$abs") >/dev/null 2>&1 || return 1
...
actual_launch=$(sed -n "${curr_launch}p" "$abs")
```
`sed -n '<range>p'` with no `-i` flag **prints** the selected lines to stdout; it does not modify
the input file. Both invocations here feed `sed`'s stdout into a `diff`/command-substitution —
read-only.

### `stat` (lines 303-304)

```
bt=$(stat -f %m "$backup" 2>/dev/null || stat -c %Y "$backup" 2>/dev/null)
ot=$(stat -f %m "$orig" 2>/dev/null || stat -c %Y "$orig" 2>/dev/null)
```
`stat` queries filesystem metadata (mtime); it is inherently read-only.

### `md5sum` / `md5` (lines 358-359)

Both are read-only hash computations over an existing file's content.

### `git ... show`, `git ... status`, `git ... log` (lines 194, 230)

All three are read-only git plumbing/porcelain invocations (`show` prints an object, `status
--porcelain` reports state, `log --oneline` lists commits) — none writes to the working tree,
index, or refs.

### Variable assignment to a file path (e.g. `MOVE_REF_LOG=`, `BACKUP_DIR=`, `ANICCA_REPO=`)

These are shell variable assignments holding path strings for later read-only use (`[ -f ... ]`,
`grep`, `diff`, `wc -l`) — no write occurs at the point of assignment or at any later use of these
variables within this script.

## Cross-check: script's own doc-comment claim vs. mechanical result

The script's header (lines 3-6) states:

> "Purity: this script is READ-ONLY. It never edits, deletes, moves, or creates any file under
> ~/.claude, ~/anicca, or the live checkout. It only reads (grep/jq/wc/diff/md5) and prints
> PASS/FAIL/SKIP lines."

This audit's mechanical grep-and-classify pass over every write-capable token confirms the claim
exactly: the only commands executed by `tests/verify.sh` are `grep`, `jq`, `wc -l`, `diff`,
`sed -n` (print mode), `stat`, `md5sum`/`md5`, `git show`/`status`/`log` (read-only forms), and
`bash -n` (syntax check, no execution) — every one of them read-only, plus `printf`/`echo` for
its own PASS/FAIL/SKIP report lines to stdout, which is not a file write either.

## Summary

**PASS.** `tests/verify.sh` performs zero filesystem write operations. All apparent `>` hits are
comments, jq comparison operators, or string literals under comparison rather than shell
redirection; all apparent mutation-capable tokens (`mv`/`cp`/`rm`/`sed -i`/`mkdir`/`touch`/
`chmod`/`chown`) are absent; the one `tee` token present in the file is inert data (a string being
compared, never executed). The script is read-only as declared in
`specs/verification-architecture.md`'s purity boundary map and in its own header comment.
