# DEPRECATED

This skill (`roundcube-webmail-skill`) is **deprecated** as of 2026-05-07.

## Use instead

`~/.openclaw/skills/naist-onboarding/SKILL.md` — the **Gmail-MCP edition**.

{{profile.education.institution}} mail is now read by:

1. The user setting up a Sieve filter in Roundcube *once*, manually, in their {{profile.lateness.stakeholders.channel}}, that forwards all mail to their personal Gmail account.
2. Anicca reading mail through the **Gmail MCP** (`mcp__aedf48e3-*__search_threads`, `__get_thread`, `__create_draft`).
3. Optionally, the user setting up Gmail "Send mail as" so Anicca can reply *as* the @naist.jp address through Gmail SMTP.

## Why this changed

The previous flow drove Roundcube directly via Playwright after solving SAML + TOTP. That required:

- Storing the user's {{profile.education.institution}} password in macOS Keychain (`WEBMAIL_PASSWORD`)
- Storing the TOTP secret in macOS Keychain (`WEBMAIL_TOTP_SECRET`)
- `zbarimg` to decode QR screenshots, plus a custom `decode_totp_qr.py`
- Maintaining a brittle Playwright script against an Roundcube/IdP UI that changes
- Multi-user support meant a Keychain entry per user

The new flow drops all of the above. The user's {{profile.education.institution}} credentials never leave their {{profile.lateness.stakeholders.channel}}, and the agent reads via a stable Gmail API. The Sieve filter is set up once and stays put.

## When this skill might still be useful

- **Testing** SAML/TOTP automation against another Roundcube instance.
- **Emergency**: Gmail forwarding fails for some reason (e.g. {{profile.education.institution}} changes mail filters and silently drops the forward) and the user temporarily needs Anicca to fall back to direct Roundcube login.

If neither applies, do not invoke. Triggering scoring on this skill has been deprioritized via the `[DEPRECATED]` prefix in `SKILL.md`'s `description` frontmatter.

## Files preserved

```
SKILL.md         — frontmatter prefixed with [DEPRECATED]
SKILL.md.bak.*   — pre-deprecation backup
scripts/         — read-mail.js, decode_totp_qr.py, setup-keychain.sh (still functional, just not invoked by routine flows)
```

## Migration cron

5 {{profile.education.institution}}-related cron jobs were added to `~/.openclaw/cron/jobs.json` on 2026-05-07 to run on top of the new Gmail-MCP flow:

- `naist-mail-digest`        (`0 7,18 * * *`)
- `naist-papers-daily`       (`0 8 * * *`)
- `naist-funds-weekly`       (`0 9 * * 1`)
- `naist-events-weekly`      (`0 10 * * 1`)
- `naist-deadline-reminder`  (`0 18 * * *`)

Each cron checks `~/.openclaw/state/naist/<slug>/` and aborts cleanly to `#metrics` (`{{profile.channels.reportChannel}}`) with a one-line "naist not yet onboarded" message until the onboarding wizard has been run.

(The 6th planned cron — an edu-portal Playwright scraper at `0 6 * * *` — is intentionally deferred. It needs a separate user-in-the-loop Playwright codegen session.)
