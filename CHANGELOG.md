# Changelog

All notable changes to **anicca-oss** are tracked here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) ·
Versioning: [SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **CI security gate** (`.github/workflows/sec-scan.yml`) — gitleaks 8.30.1 +
  TruffleHog (filesystem + git history, `--only-verified`) + Python
  `ast.parse` walk + `bash -n` walk + `unittest` discovery. Runs on every
  push to `main` and every PR.
- **Pipecat phone outbound regression suite** — 7 pure-stdlib tests
  covering `{name}` / `{ctx}` substitution, empty-name fallback, hard-rule
  preservation, route-trust block preservation, prompt size budget.

### Changed

- **Phone prompts trimmed 60 %** — lateness 3109 → 1373 chars (-55.8 %),
  wakeup 2062 → 653 chars (-68.3 %). Smaller system prompt = lower
  Gemini Live first-token latency.
- **Caller name is now read from `profile.identity.preferredName`** —
  no hardcoded names in any prompt. Falls back to `"friend"` if unset.
- **Location source: Telegram Live Location only** — OwnTracks daemon
  retired. Pipecat / lateness check / gcal departures all read the same
  `~/.openclaw/state/location/*.json` written by the Telegram bridge.
- **Quiet hours enforced** — wake-up + lateness calls suppressed between
  `profile.alarm.quietHoursStart` and `quietHoursEnd` regardless of
  calendar contents.

### Fixed

- **Routine events (sleep/wake/meditate/run/meal) no longer leak the user's
  current location into the destination** — explicit `home_address()`
  injection means the lateness loop will never say "leave the cafe for
  sleep" or fabricate a station name.

### Security

- gitleaks-action@v2 replaced with upstream MIT-licensed binary
  (the action moved to a paid licensing model).
- CI security gate runs both filesystem + git-history scans.
