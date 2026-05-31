# Changelog

All notable changes to **anicca-oss** are tracked here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) ·
Versioning: [SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **CI security gate** — `.github/workflows/sec-scan.yml` runs gitleaks
  v8.30.1, TruffleHog (filesystem + git history, `--only-verified`),
  PII-grep (12 maintainer-specific literal substrings), Python `ast.parse`
  walk, and `bash -n` walk on every push to `main` and every PR.
- **Pipecat phone outbound regression suite** —
  `skills/anicca-phone/outbound/tests/test_prompts.py` — 7 pure-stdlib
  tests covering `{name}` / `{ctx}` substitution, empty-name fallback,
  maintainer PII absence, hard-rule preservation, route-trust block
  preservation, and prompt size budget (< 1200 / 2000 chars).
- **GitHub issue + PR templates** — `.github/ISSUE_TEMPLATE/{bug,feature}_request.md`
  and `.github/PULL_REQUEST_TEMPLATE.md`.
- **CODEOWNERS + Dependabot** — auto-assign maintainer to security-sensitive
  PRs; weekly GitHub-Actions + npm dependency updates.

### Changed

- **Pipecat outbound prompts trimmed 60%** — lateness 3109 → 1373 chars
  (-55.8 %), wakeup 2062 → 653 chars (-68.3 %). Smaller system prompt =
  lower Gemini Live first-token latency = shorter silence after Twilio
  answers the call.
- **Maintainer PII redacted from prompts** — all hardcoded
  "Daisuke Narita" / "成田大祐" / Tokyo-specific train-line examples
  removed; `{name}` placeholder is substituted at dispatch from
  `profile.identity.preferredName` (falling back to `"friend"`).
- **OwnTracks → Telegram Live Location** — `lateness_check.py` /
  `gcal_departures.py` / Pipecat `bot.py` now read location from
  `~/.openclaw/state/location/*.json` (Telegram bridge) instead of the
  retired OwnTracks daemon.

### Fixed

- **Wake-call `{name}` placeholder regression** — `pick_system_instruction`
  in `bot.py` was substituting `{ctx}` but not `{name}`, which would have
  caused Gemini Live to literally speak "{name}、おはよう" on the next 07:00
  JST wake call. Caught + fixed before delivery by a CI regression test.
- **"Anicca tells me to leave home for sleep at Shinagawa station"** — the
  lateness bot used to embed a hardcoded home assumption + scrape station
  names from gcal event summaries, which surfaced fabricated stations on
  actual calls. Now: location from Telegram only; destination from
  `event.location` only; sleep/wake routine events have
  `profile.identity.homeAddress` as the strict destination; explicit
  `HARD RULE — never say "家を出ろ" unless CONTEXT says start = home` in
  the prompt.

### Security

- Repo flipped from PRIVATE to PUBLIC. Verified clean with TruffleHog
  filesystem + git-history dual scan (no verified secrets), gitleaks
  v8.30.1 (no leaks), and the 12-pattern maintainer PII grep.
- All `gitleaks-action@v2` usage replaced with the upstream MIT-licensed
  binary (the action moved to a paid licensing model).

---

Starting from this changelog onwards, every merged PR should add a bullet
under `[Unreleased]`. Cut a versioned section on release.
