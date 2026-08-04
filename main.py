import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
import database as db
from utils import (
    COUNTRIES, SERVICES, OTP_TYPES,
    generate_otp, generate_virtual_number, build_message,
)

load_dotenv()
logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)

kb_back_main = [[InlineKeyboardButton("◀️ মেনু", callback_data="menu")]]

async def show_menu(update: Update, context):
    s = await db.all_settings()
    is_running = context.bot_data.get("auto_sending", False)
    status_text = "🟢 অটো-সেন্ড চালু আছে" if is_running else "🔴 অটো-সেন্ড বন্ধ আছে"

    text = (
        "🛠 *Admin Panel — OTP King Bot*\n\n"
        f"⚙️ স্ট্যাটাস: {status_text}\n"
        f"🧩 সার্ভিস   ›  {s.get('service','Facebook')}\n"
        f"🔢 OTP দৈর্ঘ্য ›  {s.get('otp_length','5')} সংখ্যা\n"
    )
    
    send_btn_text = "🔴 অটো-সেন্ড বন্ধ করুন" if is_running else "🚀 অটো-সেন্ড শুরু করুন"
    send_cb = "stop_auto" if is_running else "start_auto"

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(send_btn_text, callback_data=send_cb)],
        [InlineKeyboardButton("📤 একবার ওটিপি পাঠান", callback_data="send_once")],
    ])
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)

async def background_otp_sender(context):
    while context.bot_data.get("auto_sending", False):
        try:
            s      = await db.all_settings()
            groups = await db.get_groups()
            if groups:
                otp      = generate_otp(int(s.get("otp_length", "5")))
                num_info = generate_virtual_number(s.get("country", "ET"))
                text     = build_message(
                    masked  = num_info["masked"],
                    flag    = num_info["flag"],
                    country = num_info["country"],
                    otp     = otp,
                    service = s.get("service", "Facebook"),
                )
                buttons = []
                if s.get("number_bot_link"):
                    buttons.append(InlineKeyboardButton("📱 নাম্বার-বট",  url=s["number_bot_link"]))
                if s.get("main_channel_link"):
                    buttons.append(InlineKeyboardButton("📢 মেন চ্যানেল", url=s["main_channel_link"]))
                markup = InlineKeyboardMarkup([buttons]) if buttons else None

                for g in groups:
                    try:
                        await context.bot.send_message(g["id"], text, parse_mode="Markdown", reply_markup=markup)
                    except Exception as e:
                        logging.warning("Auto Send Error in Group %s: %s", g["id"], e)
        except Exception as err:
            logging.error("Background loop error: %s", err)
        
        await asyncio.sleep(10)

async def start_auto_callback(update: Update, context):
    await update.callback_query.answer()
    context.bot_data["auto_sending"] = True
    asyncio.create_task(background_otp_sender(context))
    await show_menu(update, context)

async def stop_auto_callback(update: Update, context):
    await update.callback_query.answer()
    context.bot_data["auto_sending"] = False
    await show_menu(update, context)

async def send_once_callback(update: Update, context):
    await update.callback_query.answer("পাঠানো হচ্ছে...")
    s      = await db.all_settings()
    groups = await db.get_groups()
    if not groups:
        await update.callback_query.edit_message_text("⚠️ কোনো গ্রুপ সেট করা নেই।", reply_markup=InlineKeyboardMarkup(kb_back_main))
        return

    otp      = generate_otp(int(s.get("otp_length", "5")))
    num_info = generate_virtual_number(s.get("country", "ET"))
    text     = build_message(
        masked  = num_info["masked"],
        flag    = num_info["flag"],
        country = num_info["country"],
        otp     = otp,
        service = s.get("service", "Facebook"),
    )
    
    sent = 0
    for g in groups:
        try:
            await context.bot.send_message(g["id"], text, parse_mode="Markdown")
            sent += 1
        except Exception as e:
            logging.warning("Group %s error: %s", g["id"], e)

    await update.callback_query.edit_message_text(
        f"✅ *{sent}টি গ্রুপে সফলভাবে OTP পাঠানো হয়েছে!*\n\n{text}", parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb_back_main),
    )

async def cmd_start(update: Update, context):
    text = "🔐 *OTP King Bot* 👑\n\nঅ্যাডমিন প্যানেল খুলতে নিচে ক্লিক করুন:"
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛠 Admin Panel", callback_data="menu")],
    ])
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise SystemExit("BOT_TOKEN পাওয়া যায়নি!")
    
    app = Application.builder().token(token).post_init(lambda a: db.init_db()).build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("admin", show_menu))
    app.add_handler(CallbackQueryHandler(show_menu, pattern="^menu$"))
    app.add_handler(CallbackQueryHandler(start_auto_callback, pattern="^start_auto$"))
    app.add_handler(CallbackQueryHandler(stop_auto_callback, pattern="^stop_auto$"))
    app.add_handler(CallbackQueryHandler(send_once_callback, pattern="^send_once$"))
    
    logging.info("বট রান হচ্ছে...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
