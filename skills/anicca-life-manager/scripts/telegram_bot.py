#!/usr/bin/env python3
"""
Anicca Telegram Location Bot — single bot, shared by every user.

What it does:
  /start  → reply with friendly instructions for sharing Live Location
  /where  → debug: tell the user what location Anicca currently knows
  /stop   → forget the user's location until they share again
  any user shares Live Location → save lat/lon every 1-5 sec to
      $ANICCA_HOME/state/location/<telegram_user_id>.json
      (lateness_check.get_location() reads it)

Copied from python-telegram-bot v21 official patterns (no reinvention).
ref: https://docs.python-telegram-bot.org/en/v21.9/telegram.location.html
ref: https://github.com/python-telegram-bot/python-telegram-bot

Setup (5 min, one-time):
  1. Telegram → @BotFather → /newbot
       Bot name:      Anicca <YourName>
       Bot username:  AniccaYourNameBot (must end in 'bot')
       → Copy the TOKEN
  2. Save it to ~/.openclaw/.env:
       TELEGRAM_BOT_TOKEN=1234567890:ABCDef...
  3. install.sh installs the launchd plist; otherwise run:
       python3 telegram_bot.py
"""
import json
import logging
import os
import time
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

ANICCA_HOME = Path(os.environ.get("ANICCA_HOME", str(Path.home() / ".openclaw")))
ENV_PATH = ANICCA_HOME / ".env"

# Load TELEGRAM_BOT_TOKEN from the env file
for line in ENV_PATH.read_text().splitlines() if ENV_PATH.exists() else []:
    if line.startswith("TELEGRAM_BOT_TOKEN="):
        os.environ["TELEGRAM_BOT_TOKEN"] = (
            line.split("=", 1)[1].strip().strip('"').strip("'")
        )
        break

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise SystemExit(
        f"TELEGRAM_BOT_TOKEN not in {ENV_PATH} — "
        "create a bot via @BotFather first."
    )

STATE_DIR = ANICCA_HOME / "state" / "location"
STATE_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("anicca-loc-bot")


# ─── handlers ─────────────────────────────────────────────────────────────


async def cmd_start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    """Friendly first touch."""
    user = update.effective_user
    msg = (
        f"Hi {user.first_name}! I'm Anicca.\n\n"
        "I'll lead your life from now on. First I need to know where you are "
        "in real time so I can call you when it's time to leave.\n\n"
        "To share your live location:\n"
        " 1. Tap the paperclip 📎 (bottom-left of this chat)\n"
        " 2. Tap 'Location'\n"
        " 3. Tap 'Share My Live Location for...'\n"
        " 4. Pick '8 hours' (or longer)\n\n"
        "That's it. You can stop sharing anytime by tapping the live "
        "location pin → Stop Sharing."
    )
    await update.message.reply_text(msg)


def save_location(user_id: int, location, msg_date) -> None:
    """Write the latest fix to disk. lateness_check reads from here."""
    record = {
        "user_id": user_id,
        "lat": location.latitude,
        "lon": location.longitude,
        "tst": int(msg_date.timestamp()) if msg_date else int(time.time()),
        "accuracy_m": location.horizontal_accuracy,
        "heading": location.heading,
        "live_period": location.live_period,
        "received_at": int(time.time()),
    }
    out = STATE_DIR / f"{user_id}.json"
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2))
    log.info(
        "saved location user=%s lat=%.5f lon=%.5f acc=%sm",
        user_id, record["lat"], record["lon"], record["accuracy_m"],
    )


async def on_location(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    """Save location silently. NEVER reply (no spam).
    'Until I turn off' mode sends every update as a new message, so the
    only safe option is to never reply here. /start, /where, /stop are
    the only commands that ever talk back.
    """
    msg = update.effective_message
    if not msg or not msg.location:
        return
    save_location(update.effective_user.id, msg.location, msg.date)


async def on_edited_location(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    """Live-location updates arrive as edited_message every 1-5 seconds."""
    msg = update.edited_message
    if not msg or not msg.location:
        return
    save_location(update.effective_user.id, msg.location, msg.edit_date or msg.date)


async def cmd_stop(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    """Manual override — user can ask to disconnect."""
    user_id = update.effective_user.id
    f = STATE_DIR / f"{user_id}.json"
    if f.exists():
        f.unlink()
    await update.message.reply_text(
        "Stopped. Your location file was deleted. To resume just share Live "
        "Location again."
    )


async def cmd_where(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    """Debug: show what Anicca currently knows."""
    user_id = update.effective_user.id
    f = STATE_DIR / f"{user_id}.json"
    if not f.exists():
        await update.message.reply_text(
            "I don't know where you are yet. Share your Live Location first."
        )
        return
    r = json.loads(f.read_text())
    age = int(time.time() - r["received_at"])
    await update.message.reply_text(
        f"Last fix:\n"
        f"  lat: {r['lat']:.5f}\n"
        f"  lon: {r['lon']:.5f}\n"
        f"  accuracy: {r['accuracy_m']}m\n"
        f"  age: {age} sec"
    )


# ─── main ─────────────────────────────────────────────────────────────────


def main() -> None:
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("where", cmd_where))
    app.add_handler(MessageHandler(filters.LOCATION, on_location))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, on_edited_location))

    log.info("Anicca location bot starting (long polling)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
