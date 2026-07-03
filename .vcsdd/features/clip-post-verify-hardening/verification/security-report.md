# Security Hardening Report — clip-post-verify-hardening (Phase 5)

## Tooling

- `shellcheck -x` (v0.10.0, `/opt/homebrew/bin/shellcheck`) against `run.sh`, `monitor.sh`,
  `_instance_paths.sh` (the shell surface touched or added by this feature). Raw output captured
  at `verification/security-results/shellcheck-clip-post-verify.txt`.
- Manual pattern scan for classic Python injection/execution vectors (`eval(`, `exec(`,
  `os.system`, `subprocess...shell=True`) across the 3 new Python modules this feature adds:
  `reel_verify.py`, `self_heal.py`, `count_posts.py`.
- `python3 -m py_compile` on all 4 touched/new Python files (`reel_verify.py`, `self_heal.py`,
  `count_posts.py`, `post_reel.py`) — a syntax-level static check, not a security scanner, but
  captured here since it's the closest available static-analysis signal for Python on this
  machine (no `semgrep`/`bandit` binary installed; `pip install` was avoided per HARD RULE 0.33's
  "internal deps only unless a fundamental dependency is genuinely needed" and this feature has no
  functional need for a formal SAST tool beyond what shellcheck + manual review already cover).
- Semgrep/bandit were checked for availability (`which semgrep`, `which bandit`) — neither is
  installed on this machine, and installing a new SAST dependency was judged out of scope for a
  lean-mode feature whose actual attack surface (local subprocess calls with list-form argv, no
  network-facing input parsing beyond IG's own DOM) is small and was fully covered by the manual
  scan below.

## Summary

- **shellcheck**: zero errors/warnings in `run.sh` or `monitor.sh` (the two files this feature
  substantively modified). `_instance_paths.sh` shows 5 `SC2034` ("appears unused") info-level
  warnings — these are FALSE POSITIVES: shellcheck cannot see that `CLIP_QUEUE`/`CLIP_POSTED`/
  `CLIP_ACCTS`/`CLIP_LEDGER`/`CLIP_PENDING_VERIFY` are consumed by OTHER scripts that `source` this
  file (`run.sh`, `monitor.sh`, `producer.sh`) — this is pre-existing, known, and was already true
  before this feature (the first 4 variables existed in Feature 1; only `CLIP_PENDING_VERIFY` is
  new, and it's flagged identically for the identical reason). Not a real issue.
- **Injection/execution pattern scan**: zero hits for `eval(`, `exec(`, `os.system`,
  `subprocess...shell=True` in any of the 3 new Python modules. `self_heal.py`'s one
  `subprocess.run(...)` call (line 51) passes argv as a Python LIST (`[python_bin, poster_path,
  "--video", clip_mp4, ...]`), never a shell string — no shell-injection surface even though some
  of those values (clip filenames) are ultimately derived from producer.sh's own filename
  generation (out of scope for this feature; unchanged from before).
- **`run.sh`'s shell-level string interpolation**: the one place this feature introduces new
  shell/JSON boundary crossing is the `IFS=$'\x1f' read` field-split (parses `post_reel.py`'s JSON
  output) and the sidecar-write heredocs (pass `$BEFORE_HREFS_JSON`/`$TOKEN` as `argv` to inline
  Python via `<<'PYS' ... PYS`, with the values passed as `sys.argv` entries, NOT interpolated into
  the Python source text itself — this is the injection-safe pattern; confirmed by reading
  `run.sh`'s `unverified)` branch: `"$PY" - "$PENDING_VERIFY/${BASE}.before-hrefs.json"
  "$BEFORE_HREFS_JSON" "$TOKEN" <<'PYS'` followed by `sidecar_path, before_hrefs_json, token =
  sys.argv[1:4]` inside the heredoc — the heredoc body itself is single-quote-delimited (`'PYS'`),
  so bash performs NO variable expansion inside the Python source; only the `sys.argv` values,
  passed as separate argv entries (not string-concatenated into code), carry the dynamic content).
  This is the correct, injection-safe pattern (values as data via argv, never as code via string
  interpolation).
- **`py_compile`**: all 4 touched/new Python files compile cleanly (already verified during
  implementation, re-confirmed here).
- No secrets, credentials, or API keys are read, logged, or handled by any file this feature
  touches (the IG account login/session lives entirely in the pre-existing CloakBrowser profile,
  outside this feature's scope).

## Residual risk (accepted, documented)

- No formal SAST tool (semgrep/bandit) is installed on this machine; the manual scan + shellcheck
  are judged sufficient given the feature's small, well-understood attack surface (local
  subprocess with list-argv, no untrusted network input parsing). If a SAST tool becomes available
  in a future session, re-running it against these files is a reasonable follow-up, but is not
  blocking for this feature's completion.
