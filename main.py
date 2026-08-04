import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
)
import database as db
from utils import (
    COUNTRIES, SERVICES,
    generate_otp, generate_virtual_number, build_message,
)

load_dotenv()
logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)

# ১. সাধারণ বাটন (Reply Keyboard - মূল মেনু)
def get_main_keyboard(is_running: bool):
    send_btn_text = "🔴 অটো-সেন্ড বন্ধ করুন" if is_running else "🚀 অটো-সেন্ড শুরু করুন"
    return ReplyKeyboardMarkup([
        [KeyboardButton("🛠 অ্যাডমিন প্যানেল"), KeyboardButton(send_btn_text)],
        [KeyboardButton("📤 একবার ওটিপি পাঠান"), KeyboardButton("👥 গ্রুপ ম্যানেজ")],
        [KeyboardButton("🌍 দেশ পরিবর্তন"), KeyboardButton("🧩 সার্ভিস পরিবর্তন")],
        [KeyboardButton("🔢 OTP দৈর্ঘ্য"), KeyboardButton("🔗 নাম্বার বট / চ্যানেল")],
    ], resize_keyboard=True)

async def cmd_start(update: Update, context):
    is_running = context.bot_data.get("auto_sending", False)
    text = "🔐 *OTP King Bot* 👑\n\nনিচের বাটনগুলো ব্যবহার করে বট নিয়ন্ত্রণ করুন:"
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=get_main_keyboard(is_running))

async def show_menu(update: Update, context):
    s = await db.all_settings()
    ci = COUNTRIES.get(s.get("country", "ET"), COUNTRIES["ET"])
    is_running = context.bot_data.get("auto_sending", False)
    status_text = "🟢 অটো-সেন্ড চালু আছে" if is_running else "🔴 অটো-সেন্ড বন্ধ আছে"

    text = (
        "🛠 *Admin Panel — OTP King Bot*\n\n"
        f"⚙️ স্ট্যাটাস: {status_text}\n"
        f"🌍 দেশ       ›  {ci[0]} {ci[1]}\n"
        f"🧩 সার্ভিস   ›  {s.get('service','Facebook')}\n"
        f"🔢 OTP দৈর্ঘ্য ›  {s.get('otp_length','5')} সংখ্যা\n"
        f"🔗 নাম্বার বট ›  {s.get('number_bot_link') or '—'}\n"
        f"📢 চ্যানেল   ›  {s.get('main_channel_link') or '—'}\n"
    )
    
    # ২. ইনলাইন বাটন (লাইন বাটন / Inline Keyboard) প্যানেলের ভেতরে যুক্ত করা হলো
    inline_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 রিফ্রেশ প্যানেল", callback_data="refresh_admin"),
         InlineKeyboardButton("⚙️ সেটিংস পরিবর্তন", callback_data="settings_help")]
    ])

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=inline_markup)

async def send_otp_to_groups_and_admin(context, admin_chat_id=None):
    s      = await db.all_settings()
    groups = await db.get_groups()
    if not groups:
        return 0, None

    otp          = generate_otp(int(s.get("otp_length", "5")))
    country_code = s.get("country", "ET")
    num_info     = generate_virtual_number(country_code)
    service_name = s.get("service", "Facebook")

    text = build_message(
        masked  = num_info["masked"],
        flag    = num_info["flag"],
        country = num_info["country"],
        otp     = otp,
        service = service_name,
    )
    
    # গ্রুপে পাঠানোর জন্য ইনলাইন বাটন
    buttons = []
    if s.get("number_bot_link"):
        buttons.append(InlineKeyboardButton("📱 নাম্বার-বট",  url=s["number_bot_link"]))
    if s.get("main_channel_link"):
        buttons.append(InlineKeyboardButton("📢 মেন চ্যানেল", url=s["main_channel_link"]))
    markup = InlineKeyboardMarkup([buttons]) if buttons else None

    sent = 0
    for g in groups:
        try:
            await context.bot.send_message(g["id"], text, parse_mode="Markdown", reply_markup=markup)
            sent += 1
        except Exception as e:
            logging.warning("Group %s error: %s", g["id"], e)

    # অ্যাডমিনের ইনবক্সে অটোমেটিক কপি পাঠানো
    if admin_chat_id:
        try:
            await context.bot.send_message(
                admin_chat_id, 
                f"📤 *ওটিপি পাঠানো হয়েছে:*\n\n{text}", 
                parse_mode="Markdown", 
                reply_markup=markup
            )
        except Exception as err:
            logging.warning("Admin inbox error: %s", err)

    return sent, text

async def background_otp_sender(context):
    while context.bot_data.get("auto_sending", False):
        try:
            s      = await db.all_settings()
            groups = await db.get_groups()
            if groups:
                otp          = generate_otp(int(s.get("otp_length", "5")))
                country_code = s.get("country", "ET")
                num_info     = generate_virtual_number(country_code)
                service_name = s.get("service", "Facebook")
                
                text = build_message(
                    masked  = num_info["masked"],
                    flag    = num_info["flag"],
                    country = num_info["country"],
                    otp     = otp,
                    service = service_name,
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

async def handle_buttons(update: Update, context):
    if not update.message or not update.message.text:
        return
    text = update.message.text
    chat_id = update.message.chat_id
    is_running = context.bot_data.get("auto_sending", False)

    if text == "🛠 অ্যাডমিন প্যানেল":
        await show_menu(update, context)
    elif text == "🚀 অটো-সেন্ড শুরু করুন":
        groups = await db.get_groups()
        if not groups:
            await update.message.reply_text("⚠️ আগে একটি গ্রুপ যোগ করুন!", reply_markup=get_main_keyboard(is_running))
            return
        context.bot_data["auto_sending"] = True
        asyncio.create_task(background_otp_sender(context))
        await update.message.reply_text("✅ অটো-সেন্ড শুরু হয়েছে!", reply_markup=get_main_keyboard(True))
    elif text == "🔴 অটো-সেন্ড বন্ধ করুন":
        context.bot_data["auto_sending"] = False
        await update.message.reply_text("🔴 অটো-সেন্ড বন্ধ করা হয়েছে।", reply_markup=get_main_keyboard(False))
    elif text == "📤 একবার ওটিপি পাঠান":
        sent, _ = await send_otp_to_groups_and_admin(context, admin_chat_id=chat_id)
        if sent == 0:
            await update.message.reply_text("⚠️ কোনো গ্রুপ সেট করা নেই।", reply_markup=get_main_keyboard(is_running))
        else:
            await update.message.reply_text(f"✅ {sent}টি গ্রুপে সফলভাবে OTP পাঠানো হয়েছে এবং ইনবক্সে কপি পাঠানো হয়েছে!", reply_markup=get_main_keyboard(is_running))
    elif text == "👥 গ্রুপ ম্যানেজ":
        groups = await db.get_groups()
        lines = "\n".join(f"• `{g['id']}` — {g['name']}" for g in groups) or "_কোনো গ্রুপ নেই_"
        markup = ReplyKeyboardMarkup([
            [KeyboardButton("➕ গ্রুপ যোগ করুন"), KeyboardButton("❌ গ্রুপ সরান")],
            [KeyboardButton("🔙 মূল মেনু")]
        ], resize_keyboard=True)
        await update.message.reply_text(f"👥 *গ্রুপ তালিকা:*\n{lines}", parse_mode="Markdown", reply_markup=markup)
    elif text == "➕ গ্রুপ যোগ করুন":
        await update.message.reply_text("➕ *গ্রুপ আইডি এবং নাম পাঠান:*\nফরম্যাট: `-1001234567890 | গ্রুপ নাম`\n\nবাতিল করতে /cancel লিখুন", parse_mode="Markdown")
        context.user_data["waiting_for"] = "add_group"
    elif text == "❌ গ্রুপ সরান":
        groups = await db.get_groups()
        if not groups:
            await update.message.reply_text("⚠️ কোনো গ্রুপ নেই।", reply_markup=get_main_keyboard(is_running))
            return
        rows = [[KeyboardButton(f"ডিলিট: {g['id']} ({g['name']})")] for g in groups]
        rows.append([KeyboardButton("🔙 মূল মেনু")])
        await update.message.reply_text("❌ *যে গ্রুপটি সরাতে চান তা সিলেক্ট করুন:*", parse_mode="Markdown", reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True))
    elif text.startswith("ডিলিট: "):
        try:
            parts = text.split(":")
            gid = int(parts[1].strip().split(" ")[0])
            await db.remove_group(gid)
            await update.message.reply_text(f"✅ গ্রুপ `{gid}` সরানো হয়েছে।", parse_mode="Markdown", reply_markup=get_main_keyboard(is_running))
        except Exception:
            await update.message.reply_text("❌ সমস্যা হয়েছে।", reply_markup=get_main_keyboard(is_running))
    elif text == "🌍 দেশ পরিবর্তন":
        rows = [[KeyboardButton(f"দেশ: {name} ({code})")] for code, (_, name, *_) in COUNTRIES.items()]
        rows.append([KeyboardButton("🔙 মূল মেনু")])
        await update.message.reply_text("🌍 *দেশ নির্বাচন করুন:*", parse_mode="Markdown", reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True))
    elif text.startswith("দেশ: "):
        try:
            code = text.split("(")[-1].strip(")")
            await db.put("country", code)
            country_name = COUNTRIES[code][1]
            await update.message.reply_text(f"কান্ট্রি সেট হয়েছে: *{country_name}*", parse_mode="Markdown", reply_markup=get_main_keyboard(is_running))
        except Exception:
            pass
    elif text == "🧩 সার্ভিস পরিবর্তন":
        rows = [[KeyboardButton(f"সার্ভিস: {svc}")] for svc in SERVICES]
        rows.append([KeyboardButton("🔙 মূল মেনু")])
        await update.message.reply_text("🧩 *সার্ভিস নির্বাচন করুন:*", parse_mode="Markdown", reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True))
    elif text.startswith("সার্ভিস: "):
        svc = text.split(": ")[1]
        await db.put("service", svc)
        await update.message.reply_text(f"সার্ভিস সেট হয়েছে: *{svc}*", parse_mode="Markdown", reply_markup=get_main_keyboard(is_running))
    elif text == "🔢 OTP দৈর্ঘ্য":
        markup = ReplyKeyboardMarkup([
            [KeyboardButton("দৈর্ঘ্য: 4"), KeyboardButton("দৈর্ঘ্য: 5"), KeyboardButton("দৈর্ঘ্য: 6")],
            [KeyboardButton("দৈর্ঘ্য: 7"), KeyboardButton("দৈর্ঘ্য: 8")],
            [KeyboardButton("🔙 মূল মেনু")]
        ], resize_keyboard=True)
        await update.message.reply_text("🔢 *OTP দৈর্ঘ্য নির্বাচন করুন:*", parse_mode="Markdown", reply_markup=markup)
    elif text.startswith("দৈর্ঘ্য: "):
        length = text.split(": ")[1]
        await db.put("otp_length", length)
        await update.message.reply_text(f"✅ OTP দৈর্ঘ্য সেট করা হয়েছে: {length}", reply_markup=get_main_keyboard(is_running))
    elif text == "🔗 নাম্বার বট / চ্যানেল":
        markup = ReplyKeyboardMarkup([
            [KeyboardButton("সেট নাম্বার বট"), KeyboardButton("সেট চ্যানেল লিংক")],
            [KeyboardButton("🔙 মূল মেনু")]
        ], resize_keyboard=True)
        await update.message.reply_text("🔗 *লিংক সেটআপ অপশন:*", parse_mode="Markdown", reply_markup=markup)
    elif text == "সেট নাম্বার বট":
        await update.message.reply_text("🔗 *নাম্বার বটের লিংক পাঠান:*\n`https://t.me/YourBot`", parse_mode="Markdown")
        context.user_data["waiting_for"] = "numbot"
    elif text == "সেট চ্যানেল লিংক":
        await update.message.reply_text("📢 *মেইন চ্যানেলের লিংক পাঠান:*\n`https://t.me/YourChannel`", parse_mode="Markdown")
        context.user_data["waiting_for"] = "channel"
    elif text == "🔙 মূল মেনু":
        context.user_data.pop("waiting_for", None)
        await update.message.reply_text("🏠 মূল মেনু:", reply_markup=get_main_keyboard(is_running))
    else:
        waiting = context.user_data.get("waiting_for")
        if waiting == "add_group":
            parts = text.split("|")
            try:
                gid = int(parts[0].strip())
                gname = parts[1].strip() if len(parts) > 1 else f"Group {gid}"
            except ValueError:
                await update.message.reply_text("❌ সঠিক ফরম্যাটে দিন। উদাহরণ:\n`-1001234567890 | আমার গ্রুপ`")
                return
            await db.add_group(gid, gname)
            context.user_data.pop("waiting_for", None)
            await update.message.reply_text(f"✅ গ্রুপ সফলভাবে যোগ হয়েছে!\nআইডি: `{gid}`\nনাম: {gname}", parse_mode="Markdown", reply_markup=get_main_keyboard(is_running))
        elif waiting == "numbot":
            await db.put("number_bot_link", text.strip())
            context.user_data.pop("waiting_for", None)
            await update.message.reply_text("✅ নাম্বার বট লিংক সেভ হয়েছে।", reply_markup=get_main_keyboard(is_running))
        elif waiting == "channel":
            await db.put("main_channel_link", text.strip())
            context.user_data.pop("waiting_for", None)
            await update.message.reply_text("✅ চ্যানেল লিংক সেভ হয়েছে।", reply_markup=get_main_keyboard(is_running))

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise SystemExit("BOT_TOKEN পাওয়া যায়নি!")
    
    app = Application.builder().token(token).post_init(lambda a: db.init_db()).build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("admin", show_menu))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))

    logging.info("বট রান হচ্ছে...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
    
