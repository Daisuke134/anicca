# INSTALL_BOOTSTRAP — handbook for the external coding agent

You are the local AI tool the user pasted the README Quick-Start prompt
into. This document tells you, step by step, what to do on their machine.

The user is the **operator**. Always call them "the user" — never "Dais",
that's the maintainer's nickname. The user installs Anicca to be their
own life-leader; this is their data, their phone, their calendar.

You are doing **Phase 1** (installation + key collection). You stop after
step 7. **Phase 2** is the user typing `/start` on Telegram — Anicca takes
over there.

---

## TL;DR (= for you, the local AI)

```
clone → ask ONE thing at a time → write .env → install → /start
```

- ONE question per turn. The user is lazy. Don't dump a 5-key form.
- Write secrets only to `~/.openclaw/.env` (chmod 600). Never echo back.
- Never push the env file anywhere. Never commit it.
- If anything fails, stop and tell the user clearly. Don't guess fixes.

---

## STEP 1 — clone the repo

```bash
git clone https://github.com/Daisuke134/anicca-oss ~/anicca-oss
```

If `~/anicca-oss` already exists, `cd ~/anicca-oss && git pull --rebase`.

---

## STEP 2 — system deps check

These must be present. If any missing, tell the user and stop:

- python3 (≥ 3.11)
- git
- jq
- rsync
- node ≥ 20  (for openclaw)
- ffmpeg (for Pipecat phone)

Optional but recommended:

- `openclaw` CLI (`npm install -g openclaw`)
- `gog` CLI (https://github.com/Daisuke134/gog — Google API CLI)

---

## STEP 3 — ask for keys, ONE at a time

Read `~/anicca-oss/.env.example` for the canonical list. Walk the user
through them in this exact order.

### 3.1 Telegram bot token

Ask:

> "We need a Telegram bot you control — it will track your live
> location and onboard you. Open Telegram on your phone, message
> @BotFather, send /newbot, name it 'Anicca <YourName>', pick a
> username ending in 'bot' (e.g. AniccaYukiBot). Paste the token
> here when BotFather gives it to you."

Wait. When the user pastes, append to `~/.openclaw/.env`:

```
TELEGRAM_BOT_TOKEN=...
```

### 3.2 fuel choice (= 1 of 3)

Ask:

> "Pick how Anicca pays for her LLM inference:
>   (1) Use your existing ChatGPT Plus or Claude Pro login.
>   (2) Paste an API key from Anthropic / OpenAI / DeepSeek / Kimi.
>   (3) Send USDC to a wallet I'll create for you (Base network).
> Reply 1 / 2 / 3."

For (1): set `HARNESS=claude-p` in the env file and confirm with the user
that `claude` (Claude Code CLI) is installed and logged in.

For (2): ask which provider, then ask for the key, then write:

```
HARNESS=openclaw
DEEPSEEK_API_KEY=sk-...      # or OPENAI / ANTHROPIC / KIMI
```

For (3): generate a Coinbase AgentKit smart wallet with `cdp wallet
create`. Display the address as both text and a terminal QR code. Tell
the user "send min $10 USDC on Base to <addr>". Poll `cdp wallet
balance <addr>` every 30 sec; once balance > 0, write:

```
HARNESS=openclaw-x402
WALLET_ADDR=0x...
```

### 3.3 Twilio (= phone calls)

Ask:

> "For Anicca to actually call your phone, we need Twilio (~$2/mo).
> Sign up at twilio.com, complete KYC, buy 1 phone number. Then from
> the Twilio Console copy your Account SID, Auth Token, and the phone
> number you bought. Paste them here, one at a time."

Append:

```
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...
```

### 3.4 Google Maps + Gemini (= directions + voice LLM)

Ask:

> "Two free-tier Google keys. Go to console.cloud.google.com, create
> a project, enable Directions API + Geocoding API, create an API
> key — paste it. Then go to aistudio.google.com, click 'Get API
> key' — paste that one too."

Append:

```
GOOGLE_API_KEY=AIza...
GEMINI_API_KEY=AIza...
```

### 3.5 Google Calendar / Gmail OAuth via gog

Ask:

> "Anicca needs to read your Google Calendar (schedule) and your
> Gmail (apology mails). Run `gog auth login` — a browser opens —
> sign in with your Google account, then paste the account email
> here."

Append:

```
GOG_ACCOUNT=<email>
GOG_KEYRING_PASSWORD=<random 20 chars>
```

The keyring password should be auto-generated, not asked. Store
something strong.

### 3.6 (optional) payout destination

Ask:

> "Anicca will eventually pay you 10% of her earnings. Pick where:
>   (a) Japanese bank account via Stripe Connect Express (3-5 days)
>   (b) Wise — same-day Japan via Zengin
>   (c) Crypto wallet — instant USDC
>   (d) Skip for now, decide later
> Reply a / b / c / d."

Skip (= d) is the default. Only write the destination if the user picks
one — don't push them.

---

## STEP 4 — secure the env file

```bash
chmod 600 ~/.openclaw/.env
```

Never `cat` the file back to the user.

---

## STEP 5 — run install.sh

```bash
bash ~/anicca-oss/install.sh
```

Idempotent; safe to re-run. It will:
- scaffold `~/.openclaw/{skills,state,identity,logs}`
- copy templates if missing
- rsync the 6 life-manager skill bundles
- register 7 openclaw cron entries
- print "what's next"

---

## STEP 6 — verify the daemons are alive

```bash
launchctl list | grep anicca
openclaw cron list | head
```

You should see (at minimum):
- `ai.anicca.tg-loc-bot` running
- `ai.anicca.pipecat-phone` running
- `anicca-life-manager` cron, schedule `*/5 * * * *`

If the `tg-loc-bot` plist doesn't exist yet, create it (template at
`templates/ai.anicca.tg-loc-bot.plist` once that file lands).

---

## STEP 7 — hand off to the user

Tell the user, exactly:

> "Phase 1 complete. Open Telegram on your iPhone — find your bot
> (@<botname>) and send /start. Share your Live Location ('until I
> turn off' mode). Anicca will message you with the rest of the
> onboarding (name, phone, gcal OAuth link, optional payout
> destination). Your next scheduled event will trigger your first
> phone call automatically.
>
> If anything looks wrong, tail this file:
>     ~/.openclaw/skills/anicca-life-manager/state/run.log"

Then stop. Phase 2 is on Telegram, not in this terminal.

---

## what NOT to do

- Don't run `lateness_check.py` manually. The cron handles that.
- Don't insert test events in the user's calendar without explicit
  permission.
- Don't push the user's env file or any state to GitHub.
- Don't write secret keys into commit messages either — the pre-push
  hook will block you and waste their time.
- Don't keep the conversation open after step 7. Anicca takes over.

---

## debug crib

| symptom | check |
|---|---|
| no calls | `launchctl list \| grep pipecat-phone` |
| call but wrong location | `cat ~/.openclaw/state/location/*.json` |
| call but wrong destination | `grep "resolve_event" ~/.openclaw/skills/anicca-life-manager/state/run.log` |
| no events found | `gog calendar events list --account "$GOG_ACCOUNT" --from today --to +1d` |
| openclaw cron not firing | `openclaw cron show <id>` — check `next` and `last` |
| gateway hung | `openclaw gateway restart` |
