# telegram-user — read + post Telegram AS A USER (Telethon/MTProto)

A bot token can only send + read NEW incoming; it CANNOT read chat history or its own
outgoing messages (core.telegram.org/bots/api, docs.telethon.dev botapi-vs-mtproto).
To read Dais's chat (incl. loop reports the bot posted) + post as the user, use this.

## Deps (self-declared)
`~/.cache/telegram-user-venv` with `telethon` (`python3 -m venv ...; pip install telethon`).

## One-time setup
1. Get `api_id` + `api_hash` from https://my.telegram.org → API development tools.
2. Put them in `~/.cloak/telegram-user.json`: `{"api_id":123,"api_hash":"abc..."}`
3. `~/.cache/telegram-user-venv/bin/python tg_user.py login`  (prompts phone + 5-digit code, +2FA)
   → saves a reusable StringSession into the same file. After this: zero human input.

## Use
- `tg_user.py dialogs [N]`          list conversations (find the right entity)
- `tg_user.py read <entity> [N]`    read history (entity = me | @user | chat_id)
- `tg_user.py send <entity> <text>` post
