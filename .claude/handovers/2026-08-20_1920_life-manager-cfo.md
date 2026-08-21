# Life Manager CFO handover

## Current resume evidence

- `CFO-OPS3a` is closed in the canonical Life Manager worktree `/Users/anicca/Projects/life-manager-main/.worktrees/cfo-ops3a`, branch `feature/cfo-ops3a-canonical`, commit `2dac47124b63bbefdbf40275ba40dc0d938c6109`. The branch is clean and its remote head is verified.
- The installed plist is now a stable release path: label `ai.anicca.life-manager-cfo-hourly`, interval `3600`, entrypoint `/Users/anicca/.local/share/life-manager/cfo-hourly/current/skills/cfo/run.sh`; it contains no feature-worktree path. Stable CFO module-load is PASS and the focused financial gate is 19/19 when using the stable release dependencies. The stable wrapper now preserves a real redacted run result (`status=failed`, `reportingDate=2026-08-20`) after fixing the Bash-3.2 JSON-prefix guard.
- `CFO-OPS3b` remains open only at the GUI launchd/receipt gate. The host-parity implementation is canonical in commit `6acff1585` on `feature/cfo-ops3a-canonical`: the persistent local Codex app-server reads the existing Moneytree App through `mcpServer/tool/call`, and the existing adapter returns a redacted success envelope. The label is not loaded: post-install `launchctl print/list`, `launchctl asuser 501 ...`, and `launchctl bootstrap gui/501` return `141: Reentrancy avoided`; `managerpid` cannot resolve. `opendirectoryd` reports unavailable and uid 501 has no resolvable user record in this session. On 2026-08-21, authorized restart paths were attempted but did not execute: System Events returned `-10827`, `launchctl reboot system` returned `141`, `/sbin/reboot` returned `Operation not permitted`, and the Terminal helper returned `kLSNoExecutableErr -10827`. No account-directory mutation, logout, reboot, or OS-service restart occurred.
- Stable read-only evidence now passes: with `CODEX_HOME=/Users/anicca/.codex`, the installed reader returns only `{"ok":true,"sourceId":"moneytree_mufg","accountCount":1,"partial":true}`; an invalid app-server socket returns `ok=false` and `partial=true`. Raw account/transaction fields were not persisted or sent. The stable release is `/Users/anicca/.local/share/life-manager/cfo-hourly/current`; its plist is `plutil -lint` clean, has `LIFE_MANAGER_ENV_FILE=/Users/anicca/.openclaw/.env`, `CODEX_HOME=/Users/anicca/.codex`, and `StartInterval=3600`. No current hourly CFO finance Telegram receipt is claimed until the existing launchd label runs and yields a positive provider `message_id`.
- New host-context read-only evidence (2026-08-21): the current assistant host's installed Moneytree connector returns `isError=false` for both `show_accounts(locale=ja)` and `show_transactions(locale=ja, limit=1)`. The latter exposes a structured transaction list with `id`, `date`, `amount`, `category`, and `currency` fields without printing their values here. The persistent local app-server bridge now makes the existing Apps context callable by the production reader; no raw values are printed or persisted.
- Codex host-parity audit (2026-08-21): official Codex MCP, skills, plugins, App Server, and SDK documentation says the CLI/desktop/IDE share user configuration and skill roots, while a fresh `codex exec` is a new thread rather than the foreground ChatGPT conversation. The local Moneytree remote-plugin bundle exists in cache, and `codex app-server` reports the Moneytree app `enabled=true, callable=true` via `app/installed`. Earlier fresh-subprocess probes timed out at the `chatgpt.com` transport, but the persistent app-server WebSocket path now passes: `app/read` exposes the existing Moneytree tools, direct `mcpServer/tool/call` returns `isError=false` with structured `accounts`, and the production adapter consumes it without LLM number copying. The blocker is now only the broken GUI/user launchd domain and missing current Telegram receipt, not absence of the connector. Do not copy credentials or account values into the repository.

- Remaining-TODO SSOT: `/Users/anicca/anicca-project/.worktrees/cfo-resume-spec/docs/superpowers/specs/2026-08-06-life-manager-cfo-design.md`, section `6. Execution Steps — Full Ordered TODO`.
- Business child SSOT: `/Users/anicca/anicca-project/.worktrees/cfo-resume-spec/docs/superpowers/specs/2026-08-11-life-manager-cfo-business-instrumentation-design.md`, sections `3. Ordered work` and `13. Resume audit`.
- Code worktree: `/Users/anicca/Projects/life-manager-main/.worktrees/cfo-ops3a`, branch `feature/cfo-ops3a-canonical`, verified HEAD `6acff1585443e14e9f1a67f89937c9f55252a42c`. Its explicit push target is `origin HEAD:feature/cfo-ops3a-canonical`.
- Spec worktree: `/Users/anicca/anicca-project/.worktrees/cfo-resume-spec`, branch `feature/cfo-moneytree-daily-report`. This update is the current branch tip; after push, verify the exact tip with `git ls-remote`. Push target is `canonical HEAD:feature/cfo-moneytree-daily-report`.
- Do not touch `/Users/anicca/anicca-project`: it is a separate dirty worktree with unrelated user changes.
- Completed: Moneytree/MUFG source and real Telegram foundation; provider/local usage evidence; confirmed Anthropic subscription report; Life Manager business slice; Anicca RevenueCat gross; signed Apple Finance row normalizer. Apple code is `f1986663b`; fresh focused test is 5/5.
- Historical failure was a deleted-worktree plist, invalid recovered dependencies, and a Bash-3.2 wrapper prefix bug; the stable release path, dependency closure, wrapper guard, and persistent Codex app-server reader are corrected. The remaining live failure is the current session's launchd/bootstrap/OpenDirectory state, so no current hourly Telegram delivery is proven.
- Post-fix readback is clean (`plutil -lint` and installed wrapper `bash -n` PASS), but `launchctl list ai.anicca.life-manager-cfo-hourly` still returns 141. `sudo -n` cannot provide a root context because uid 501 is absent from the passwd database, and a localhost login context reports the same missing uid.
- GitHub DNS was transiently unavailable during the audit; the canonical CFO branch is verified at `6acff1585`, and the exact canonical spec tip is verified with `git ls-remote` after this push.
- Canonical product repository: `/Users/anicca/Projects/life-manager-main`, origin `Daisuke134/life-manager.git`, branch `main` at audit HEAD `f116abd1524e7b33a0590c6167307152aa896df8`. It already owns `apps/life-manager`, `skills`, `loops`, CFO Telegram callback, and financial-report runtime. Its main worktree has an unrelated user edit in `skills/earn/gig/tests/test_reply_concurrency.py`; never edit or reset that worktree. Create a dedicated CFO worktree/branch from fetched `origin/main` before migration.
- Current next action: restore only the existing `ai.anicca.life-manager-cfo-hourly` launchd label, run one current real Moneytree pass, record a positive Telegram provider `message_id`, and verify the stable hourly path/schedule read-back. The host-parity subgate is already closed by `6acff1585`; do not switch to `CFO-1j` until the launchd/receipt gate passes. Only then implement `CFO-1j` recent verified transactions; only after both gates does `CFO-2b.2b2` resume. Do not revive `life-manager-v0`, `cfo-daily`, or the separate financial-report loop.
- No Binance work: it remains explicitly deferred/skipped for the current product path. No payout, MUFG landing, profit, ROI, or tax amount is currently claimed from Apple evidence.
- Financial-concierge boundary: hourly balance/reporting is first; recent verified transactions are second; advice
  remains `CFO-2d3` and fires only for a verified outgoing transaction with transfer/card-repayment/refund exclusion,
  a real budget/runway impact, one ranked suggestion, and a seven-day cooldown. Unknown category/budget means no advice.

## Current ordered TODO

1. `CFO-OPS3b`: host parity is closed by `6acff1585` through the persistent local app-server and one real structured
   Moneytree tool call. The remaining operational gate is to load only `ai.anicca.life-manager-cfo-hourly`, verify its
   stable path and 3600-second schedule, execute the real read from the loop, record a current Telegram provider
   `message_id`, and prove the hourly path/schedule read-back. The current launchd/OpenDirectory domain returns 141;
   no fake receipt is allowed. If the bridge later regresses, choose and document the official LINK/API fallback.
2. `CFO-1j`: display recent verified Moneytree transactions with redacted direction/date/amount/category coverage;
   show incomplete pagination and keep advice disabled.
3. `CFO-2b.2b2`, then `CFO-2b.2c`: first actionable business slice after the local gates; parse one complete signed
   Apple Finance report, reconcile settled Partner Share to RevenueCat, then compose the Anicca iOS business fact
   while preserving unknown payout/API-cost coverage.
4. `CFO-2a3b`: complete one-time Google Cloud reauthentication and acquire the real Cost Table when the external
   owner action is available; this remains blocked and never accepts a fabricated CSV.
5. `CFO-2b.3` through `CFO-2b.9`: instrument Writer, Affiliate, Gig Work, x402, Employment, Capafy, and Proprietary
   Investing in registry order with receipts, landed cash, direct/runtime cost, capital, and evidence.
6. `CFO-2c`, `CFO-2d`, `CFO-2d2`, `CFO-2d3`, `CFO-2e`: reconcile provider/Fleet totals; publish contribution profit,
   runway, ROI, evidence completeness, readable Telegram drill-downs; then enable the verified-outgoing-only spending
   guardian and deterministic recommendations.
7. M3 tax evidence/reserve (`CFO-3a`–`3e`), M4 cloud/multi-tenant parity (`CFO-4a`–`4e`), and M5 controlled capital
   allocation (`CFO-5a`–`5e`) remain deferred until the local CFO path and business instrumentation are closed.

Only one item is active at a time; every later item waits for the current evidence, tests, commit, and push.
