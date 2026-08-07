"""
Telegram Auto-Poster Bot with Admin Panel
==========================================

Features:
- Admin Panel via Inline Keyboard
- Auto-post to any channel/group at set intervals
- Dynamic variables: {otp}, {time}, {date}, {random_emoji}
- Copy-to-clipboard InlineKeyboardButton for OTP
- Custom inline buttons support
- JSON persistent config

Requirements:
 pip install python-telegram-bot>=22.0

Usage:
    export BOT_TOKEN="your_token_here"
    python bot.py
"""

import asyncio
import json
import os
import random
import secrets
from datetime import datetime
from typing import Any,cast
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CopyTextButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ─── Configuration ───
CONFIG_FILE = "config.json"
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Default configDEFAULT
default_CONFIG = {
    "admin_id": None,
    "target_channel": "", # e.g., "@mychannel" or "-100123..."
    "interval_seconds": 10,
    "is_running": False,
    "template": (
        "                    \n"
        "|| {random_emoji} Update #{otp} #EN\n"
        "                    "
    ),
    "otp_length": 6,
    "use_copy_button": True, # If true, adds a [OTP] copy button
    "custom_buttons": [] # List of rows, each row is list of dicts,
}

# Temporary state to know what setting the admin is currently typing
ADMIN_STATE = {}  # user_id -> "target_channel" | "interval" | "template" | "otp_length"

# ─── Config helpers ───
def load_config() -> dict[str, Any]:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return cast(dict[str, Any], json.load(f))
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: dict[str, Any]) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def is_admin(user_id: int, config: dict[str, Any]) -> bool:
    return config.get("admin_id") == user_id


# ─── Content generators ───
def generate_otp(length: int = 6) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(length))


EXPAND_EMOJIS = ["✨", "🔥", "⚡", "🚀", "💎", "🌟", "💡", "🔔"]


def expand_template(template: str, otp: str) -> str:
    return template.replace("{otp}", otp)\
                   .replace("{time}", datetime.now().strftime("%H:%M:%S"))\
                   .replace("{date}", datetime.now().strftime("%Y-%m-%d"))\
                   .replace("{random_emoji}", random.choice(EXPAND_EMOJIS))


# ─── Keyboard builders ───
def admin_panel(config: dict[str, Any]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("🎯 Set Channel", callback_data="set_target_channel"),
            InlineKeyboardButton("⏱ Interval", callback_data="set_interval"),
        ],
        [
            InlineKeyboardButton("📝 Edit Template", callback_data="set_template"),
            InlineKeyboardButton("🔢 OTP Length", callback_data="set_otp_length"),
        ],
        [
            InlineKeyboardButton("▶️ Start Posting", callback_data="start_posting"),
            InlineKeyboardButton("⏹ Stop Posting", callback_data="stop_posting"),
        ],
        [
            InlineKeyboardButton("👁 Preview", callback_data="preview"),
            InlineKeyboardButton("📋 Settings", callback_data="show_settings"),
        ],
        [
            InlineKeyboardButton("🔘 Toggle Copy Button", callback_data="toggle_copy"),
 ],
    ]
    return InlineKeyboardMarkup(rows)


# ─── Background auto-poster ───
async def auto_poster(app: Application, config_ref: dict[str, Any]):
    """Loop that posts messages while is_running is True."""
    while True:
        try:
            config = load_config()  # refresh from disk
            if not config.get("is_running"):
                await asyncio.sleep(1)
                continue

            channel = config.get("target_channel", "")
            interval = int(config.get("interval_seconds", 10))
            if not channel or not channel.strip():
                await asyncio.sleep(1)
                continue

            otp = generate_otp(int(config.get("otp_length", 6)))
            text = expand_template(config.get("template", ""), otp)

            keyboard_rows = []

 # Copy button (optional)
            if config.get("use_copy_button"):
                kb = InlineKeyboardButton(
                    text=f"[ {otp} ]",
                    copy_text=CopyTextButton(text=otp),
                )
                keyboard_rows.append([kb])

            # Custom admin buttons
            custom = config.get("custom_buttons", [])
            for row in custom:
                button_row = []
                for btn in row:
                    if "url" in btn:
                        button_row.append(
                            InlineKeyboardButton(text=btn["text"], url=btn["url"])
 )
                    elif "callback_data" in btn:
                        button_row.append(
                            InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"])
                        )
                if button_row:
                    keyboard_rows.append(button_row)

            markup = InlineKeyboardMarkup(keyboard_rows) if keyboard_rows else None

            await app.bot.send_message(
                chat_id=channel,
                text=text,
                reply_markup=markup,
                parse_mode=None,  # plain text keeps formatting exact
            )

            await asyncio.sleep(max(5, interval))  # minimum 5s safety

        except Exception as e:
            print(f"[AutoPoster] Error: {e}")
            await asyncio.sleep(5)


# ─── Handlers ───
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    config = load_config()

    if config.get("admin_id") is None:
        config["admin_id"] = user_id
        save_config(config)
        await update.message.reply_text(
            "✅ You have been set as the Admin!\n\nUse /admin to open the control panel.",
        )
 return

    if is_admin(user_id, config):
        await update.message.reply_text(
            "Welcome back! Use /admin to open the control panel."
 )
    else:
        await update.message.reply_text("⛔ You are not authorized to use this bot.")


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    config = load_config()

    if not is_admin(user_id, config):
        await update.message.reply_text("⛔ Unauthorized.")
        return

    await update.message.reply_text(
        "🔧 Admin Panel\n\nConfigure the bot below:",
        reply_markup=admin_panel(config),
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    config = load_config()

    if not is_admin(user_id, config):
        await query.edit_message_text("⛔ Unauthorized.")
        return

    data = query.data

    if data == "show_settings":
        ch = config.get("target_channel") or "(not set)"
        iv = config.get("interval_seconds")
        tmpl = config.get("template", "")[:60] + "..."
        otp_len = config.get("otp_length")
        copy_on = "ON" if config.get("use_copy_button") else "OFF"
        await query.edit_message_text(
            f"📋 Current Settings\n\n"
 f"Channel: {ch}\n"
            f"Interval: {iv}s\n"
            f"OTP Length: {otp_len}\n"
            f"Copy Button: {copy_on}\n\n"
            f"Template preview:\n<pre>{tmpl}</pre>",
            reply_markup=admin_panel(config),
            parse_mode="HTML",
        )
        return

    if data == "toggle_copy":
        config["use_copy_button"] = not config.get("use_copy_button", True)
        save_config(config)
        await query.edit_message_text(
            "🔘 Copy button toggled.\nUse /admin to return.",
 reply_markup=admin_panel(config),
        )
        return

    if data == "start_posting":
        if not config.get("target_channel"):
            await query.answer("❌ Set a target channel first!", show_alert=True)
            return
        config["is_running"] = True
        save_config(config)
        await query.edit_message_text(
            "▶️ Auto-posting started!",
            reply_markup=admin_panel(config),
        )
        return

    if data == "stop_posting":
        config["is_running"] = False
        save_config(config)
        await query.edit_message_text(
            "⏹ Auto-posting stopped.",
            reply_markup=admin_panel(config),
        )
        return

    if data == "preview":
        otp = generate_otp(int(config.get("otp_length", 6)))
        preview_text = expand_template(config.get("template", ""), otp)
        await query.edit_message_text(
            f"👁 Preview:\n\n{preview_text}\n\nUse /admin to return.",
            reply_markup=admin_panel(config),
        )
        return

    # For settings that require text input
    prompts = {
        "set_target_channel": "📨 Send me the Target Channel ID or username (e.g., @mychannel or -1001234567890):",
        "set_interval": "⏱ Send interval in seconds (minimum 5):",
        "set_template": (
            "📝 Send your message template.\n"
            "Variables: {otp}, {time}, {date}, {random_emoji}"
        ),
        "set_otp_length": "🔢 Send OTP digit count (e.g., 5 or 6):",
    }

    if data in prompts:
        ADMIN_STATE[user_id] = data
        await query.edit_message_text(prompts[data])
        return


async def text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in ADMIN_STATE:
        return

    setting = ADMIN_STATE.pop(user_id)
    config = load_config()

    if not is_admin(user_id, config):
        return

    if setting == "set_target_channel":
        config["target_channel"] = text
        save_config(config)
        await update.message.reply_text(f"✅ Target channel set to: {text}\n\n/admin", reply_markup=admin_panel(config))

    elif setting == "set_interval":
        try:
            sec = max(5, int(text))
            config["interval_seconds"] = sec
            save_config(config)
            await update.message.reply_text(f"✅ Interval set to {sec}s.\n\n/admin", reply_markup=admin_panel(config))
        except ValueError:
            await update.message.reply_text("❌ Please send a valid number.")

 elif setting == "set_template":
        config["template"] = text
        save_config(config)
        await update.message.reply_text("✅ Template updated!\n\n/admin", reply_markup=admin_panel(config))

    elif setting == "set_otp_length":
        try:
            length = max(3, min(12, int(text)))
            config["otp_length"] = length
            save_config(config)
            await update.message.reply_text(f"✅ OTP length set to {length}.\n\n/admin", reply_markup=admin_panel(config))
        except ValueError:
            await update.message.reply_text("❌ Please send a valid number.")


def main() -> None:
    if BOT_TOKEN in ("YOUR_BOT_TOKEN_HERE", ""):
        raise ValueError("❌ Please set the BOT_TOKEN environment variable!")

    application = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_input))

    # Start background poster loop
    config = load_config()
    asyncio.get_event_loop().create_task(auto_poster(application, config))

    print("🤖 Bot started. Use /start and then /admin.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
