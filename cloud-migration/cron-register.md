# Gateway cron registration

The live OpenClaw Gateway cron store is the source of truth. Do not edit
`~/.openclaw/cron/jobs.json` (or any other `jobs.json`) by hand.

Run these commands on the Mac Mini as user `anicca`:

```bash
# Confirm gateway health and inspect existing jobs before adding anything.
openclaw cron status
openclaw cron list

# Register the sync every 30 minutes. Fable runs this command; this document does not.
openclaw cron add \
  --name cloud-mobile-auto-sync \
  --description "Commit and push measured live assets for phone-only operations" \
  --every 30m \
  --session isolated \
  --no-deliver \
  --message "Run bash /Users/anicca/anicca-project/cloud-migration/auto-sync.sh exactly once. Return its single JSON output line unchanged."

# Verify the gateway's live state after registration.
openclaw cron list
openclaw cron status
```

If a job with the same name already exists, do not create a duplicate. Inspect it
with `openclaw cron list`, then use `openclaw cron show <job-id>` and
`openclaw cron edit <job-id> --every 30m` as needed.

