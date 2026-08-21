# render-verify + self-fix — the loop's own self-heal pair

Two new, self-contained scripts (no existing file touched -- see each script's own header for why):

```bash
bash render-verify-draft.sh --platform <note|zenn|substack|devto> --url <draft edit URL> --lang <ja|en>
# -> {"verdict":"PASS"|"FAIL","problems":[...blocking...],"advisory":[...never blocks...]}, exit 0/1

bash article-self-fix.sh "<one-line blocker + a concrete fix hint>"
# -> spawns a detached autonomous Sonnet dev (diagnose -> fix -> verify -> commit+push), no human

SELF_FIX_DRYRUN=1 bash article-self-fix.sh "<blocker>"   # prints identity+paths only, spawns nothing
```

`render-verify-draft.sh` takes a real full-page screenshot of the draft editor over CDP and has a
fresh `claude -p` vision judge check it against a small blocking/advisory checklist (frontmatter
leaking into the body, unrendered images/mermaid, heading breaks, note eyecatch, paywall marker
position) -- it never caches a verdict. `article-self-fix.sh` is a copy+tweak of
`~/anicca/skills/self/self-fix.sh`'s proven spawn/staleness-detection pattern, retargeted at this
repo (`~/profitable-claude`, public) and this loop's own log/state file names.

**Not done here (explicitly out of this task's scope, authfix's follow-up):** wiring
`render-verify-draft.sh` into `article-daily.sh`'s STEP 6.5 (after each platform draft is staged,
before it is reported done) or wiring `article-self-fix.sh` into STEP0's blocker-handling path. Both
scripts work correctly stand-alone today (verified below); the calling code that invokes them from
the daily pass does not exist yet.

## Verification (real output, 2026-07-17)

- `render-verify-draft.sh` against today's real note draft (`n5787e092451f`):
  `{"verdict":"PASS","problems":[],"advisory":[]}` — full-page screenshot was genuinely full-page
  (1905x8646px, all the way to the references section), own-eyes-checked.
- `render-verify-draft.sh` against a synthetic HTML page reproducing a frontmatter leak + unrendered
  mermaid fence: `{"verdict":"FAIL","problems":["rule: P1, ...","rule: P2, ..."],"advisory":["rule: A1, ..."]}`
  — both injected defects caught with real quotes from the screenshot, plus one correctly-scoped
  advisory-only observation.
- `article-self-fix.sh` with `SELF_FIX_DRYRUN=1`: prints the resolved loop identity, tmux
  session/socket, and result/log file paths without spawning anything.
