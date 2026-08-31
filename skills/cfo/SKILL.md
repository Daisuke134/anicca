# CFO hourly operator skill

This skill runs one repository-owned CFO pass and exits. It is the operator-facing wrapper for
`apps/mr-bot/scripts/cfo-hourly-local.js`; launchd owns the one-hour cadence.

## Contract

- Invoke `skills/cfo/run.sh` from the canonical Mr.bot checkout.
- `MR_BOT_APP_DIR` points at the staged stable release (`~/.local/share/mr-bot/cfo-hourly/current/apps/mr-bot`)
  when installed; a checked-out canonical app directory may be used for verification before staging.
- Credentials are read from `MR_BOT_ENV_FILE` (default:
  `~/.local/state/mr-bot/.env`) and are never printed or written to loop state.
- `LM_CFO_UID`, `TELEGRAM_ALERT_CHAT_ID`, `TELEGRAM_BOT_TOKEN`, `SUPABASE_URL`,
  `SUPABASE_SERVICE_ROLE_KEY`, and `LM_UID_SECRET` are the shared-loop contract. The legacy
  `LM_CFO_TELEGRAM_CHAT_ID` and `LM_TELEGRAM_BOT_TOKEN` names remain accepted as fallbacks for
  standalone Mr.bot installations; when both token families exist, the shared-loop bot is used.
- State is outside the code release at `CFO_STATE_DIR` (default: `~/loops/cfo-hourly`). The wrapper
  records only the runner's redacted status envelope in `last-result.json`.
- A failure produces a fixed redacted status envelope and a non-zero exit. It never invents a
  financial amount, retries out of band, or logs raw provider/error payloads.

The pass is single-writer: do not run another CFO, `cfo-daily`, or financial-report loop against the
same snapshot/delivery tables.
