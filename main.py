import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters,
)
import database as db
from utils import (
    COUNTRIES, SERVICES, OTP_TYPES,
    generate_otp, generate_virtual_number, build_message,
)

load_dotenv()
logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)

WAIT_NUM_BOT, WAIT_CHANNEL, WAIT_ADD_GROUP = range(3)

kb_back_main   = [[InlineKeyboardButton("◀️ মেনু", callback_data="menu")]]
kb_back_groups = [[InlineKeyboardButton("◀️ ফিরে যান", callback_data="groups")]]

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
    
    send_btn_text = "🔴 অটো-সেন্ড বন্ধ করুন" if is_running else "🚀 অটো-সেন্ড শুরু করুন"
    send_cb = "stop_auto" if is_running else "start_auto"

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 দেশ", callback_data="set_country"),
         InlineKeyboardButton("🧩 সার্ভিস", callback_data="set_service")],
        [InlineKeyboardButton("🔢 OTP দৈর্ঘ্য", callback_data="set_length"),
         InlineKeyboardButton("📨 OTP টাইপ", callback_data="set_type")],
        [InlineKeyboardButton("🔗 নাম্বার বট", callback_data="set_numbot"),
         InlineKeyboardButton("📢 চ্যানেল লিংক", callback_data="set_channel")],
        [InlineKeyboardButton("👥 গ্রুপ ম্যানেজ", callback_data="groups")],
        [InlineKeyboardButton(send_btn_text, callback_data=send_cb)],
        [InlineKeyboardButton("📤 একবার ওটিপি পাঠান", callback_data="send_once")],
    ])
    
    if update.callback_query:
        try:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            await update.callback_query.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)

async def country_menu(update: Update, context):
    await update.callback_query.answer()
    rows, row = [], []
    for code, (flag, name, *_) in COUNTRIES.items():
        row.append(InlineKeyboardButton(f"{flag} {name}", callback_data=f"c_{code}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton("◀️ ফিরে যান", callback_data="menu")])
    await update.callback_query.edit_message_text(
        "🌍 *দেশ নির্বাচন করুন:*", parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(rows),
    )

async def service_menu(update: Update, context):
    await update.callback_query.answer()
    rows, row = [], []
    for svc in SERVICES:
        row.append(InlineKeyboardButton(svc, callback_data=f"s_{svc}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton("◀️ ফিরে যান", callback_data="menu")])
    await update.callback_query.edit_message_text(
        "🧩 *সার্ভিস নির্বাচন করুন:*", parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(rows),
    )

async def length_menu(update: Update, context):
    await update.callback_query.answer()
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{n} সংখ্যা", callback_data=f"l_{n}") for n in (4, 5, 6)],
        [InlineKeyboardButton(f"{n} সংখ্যা", callback_data=f"l_{n}") for n in (7, 8)],
        [InlineKeyboardButton("◀️ ফিরে যান", callback_data="menu")],
    ])
    await update.callback_query.edit_message_text(
        "🔢 *OTP দৈর্ঘ্য নির্বাচন করুন:*", parse_mode="Markdown",
        reply_markup=markup,
    )

async def type_menu(update: Update, context):
    await update.callback_query.answer()
    rows = [[InlineKeyboardButton(label, callback_data=f"t_{key}")]
            for key, label in OTP_TYPES.items()]
    rows.append([InlineKeyboardButton("◀️ ফিরে যান", callback_data="menu")])
    await update.callback_query.edit_message_text(
        "📨 *OTP টাইপ নির্বাচন করুন:*", parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(rows),
    )

async def on_country(update: Update, context):
    await update.callback_query.answer()
    code = update.callback_query.data[2:]
    await db.put("country", code)
    flag, name, *_ = COUNTRIES[code]
    await update.callback_query.edit_message_text(
        f"✅ দেশ সেট: {flag} *{name}*", parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb_back_main),
    )

async def on_service(update: Update, context):
    await update.callback_query.answer()
    svc = update.callback_query.data[2:]
    await db.put("service", svc)
    await update.callback_query.edit_message_text(
        f"✅ সার্ভিস সেট: *{svc}*", parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb_back_main),
    )

async def on_length(update: Update, context):
    await update.callback_query.answer()
    length = update.callback_query.data[2:]
    await db.put("otp_length", length)
    await update.callback_query.edit_message_text(
        f"✅ OTP দৈর্ঘ্য সেট: *{length} সংখ্যা*", parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb_back_main),
    )

async def on_type(update: Update, context):
    await update.callback_query.answer()
    key = update.callback_query.data[2:]
    await db.put("otp_type", key)
    await update.callback_query.edit_message_text(
        f"✅ OTP টাইপ সেট: *{OTP_TYPES[key]}*", parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb_back_main),
    )

async def groups_menu(update: Update, context):
    await update.callback_query.answer()
    groups = await db.get_groups()
    lines = "\n".join(f"• `{g['id']}` — {g['name']}" for g in groups) or "_কোনো গ্রুপ নেই_"
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ গ্রুপ যোগ", callback_data="grp_add"),
         InlineKeyboardButton("❌ গ্রুপ সরান", callback_data="grp_rm")],
        [InlineKeyboardButton("◀️ ফিরে যান", callback_data="menu")],
    ])
    await update.callback_query.edit_message_text(f"👥 *গ্রুপ তালিকা:*\n{lines}", parse_mode="Markdown", reply_markup=markup)

async def ask_add_group(update: Update, context):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "➕ *গ্রুপ আইডি এবং নাম পাঠান:*\nফরম্যাট: `-1001234567890 | গ্রুপ নাম`\n\nবাতিল: /cancel",
        parse_mode="Markdown",
    )
    return WAIT_ADD_GROUP

async def save_add_group(update: Update, context):
    text = update.message.text.strip()
    parts = text.split("|")
    try:
        gid = int(parts[0].strip())
        gname = parts[1].strip() if len(parts) > 1 else f"Group {gid}"
    except ValueError:
        await update.message.reply_text("❌ সঠিক ফরম্যাটে দিন। উদাহরণ:\n`-1001234567890 | আমার গ্রুপ`")
        return WAIT_ADD_GROUP
    
    await db.add_group(gid, gname)
    await update.message.reply_text(
        f"✅ গ্রুপ সফলভাবে যোগ হয়েছে!\nআইডি: `{gid}`\nনাম: {gname}", parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb_back_groups),
    )
    return ConversationHandler.END

async def grp_remove_list(update: Update, context):
    await update.callback_query.answer()
    groups = await db.get_groups()
    if not groups:
        await update.callback_query.edit_message_text(
            "⚠️ কোনো গ্রুপ নেই।",
            reply_markup=InlineKeyboardMarkup(kb_back_groups),
        )
        return
    rows = [[InlineKeyboardButton(f"❌ {g['name']}", callback_data=f"dg_{g['id']}")] for g in groups]
    rows.append([InlineKeyboardButton("◀️ ফিরে যান", callback_data="groups")])
    await update.callback_query.edit_message_text(
        "❌ *কোন গ্রুপ সরাবেন?*", parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(rows),
    )

async def do_remove_group(update: Update, context):
    await update.callback_query.answer()
    gid = int(update.callback_query.data[3:])
    await db.remove_group(gid)
    await update.callback_query.edit_message_text(
        f"✅ গ্রুপ `{gid}` সরানো হয়েছে।", parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb_back_groups),
    )

async def ask_numbot(update: Update, context):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "🔗 *নাম্বার বটের লিংক পাঠান:*\n`https://t.me/YourBot`\n\nবাতিল: /cancel",
        parse_mode="Markdown",
    )
    return WAIT_NUM_BOT

async def save_numbot(update: Update, context):
    await db.put("number_bot_link", update.message.text.strip())
    await update.message.reply_text(
        "✅ নাম্বার বট লিংক সেভ হয়েছে।",
        reply_markup=InlineKeyboardMarkup(kb_back_main),
    )
    return ConversationHandler.END

async def ask_channel(update: Update, context):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "📢 *মেইন চ্যানেলের লিংক পাঠান:*\n`https://t.me/YourChannel`\n\nবাতিল: /cancel",
        parse_mode="Markdown",
    )
    return WAIT_CHANNEL

async def save_channel(update: Update, context):
    await db.put("main_channel_link", update.message.text.strip())
    await update.message.reply_text(
        "✅ চ্যানেল লিংক সেভ হয়েছে।",
        reply_markup=InlineKeyboardMarkup(kb_back_main),
    )
    return ConversationHandler.END

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
    groups = await db.get_groups()
    if not groups:
        await update.callback_query.answer("⚠️ আগে একটি গ্রুপ যোগ করুন!", show_alert=True)
        return
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

async def cmd_cancel(update: Update, context):
    context.user_data.clear()
    await update.message.reply_text("❌ বাতিল করা হয়েছে।", reply_markup=InlineKeyboardMarkup(kb_back_main))
    return ConversationHandler.END

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise SystemExit("BOT_TOKEN পাওয়া যায়নি!")
    
    app = Application.builder().token(token).post_init(lambda a: db.init_db()).build()
    
    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(ask_numbot,     pattern="^set_numbot$"),
            CallbackQueryHandler(ask_channel,    pattern="^set_channel$"),
            CallbackQueryHandler(ask_add_group,  pattern="^grp_add$"),
        ],
        states={
            WAIT_NUM_BOT:   [MessageHandler(filters.TEXT & ~filters.COMMAND, save_numbot)],
            WAIT_CHANNEL:   [MessageHandler(filters.TEXT & ~filters.COMMAND, save_channel)],
            WAIT_ADD_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_add_group)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("admin", show_menu))
    app.add_handler(conv)

    app.add_handler(CallbackQueryHandler(show_menu,         pattern="^menu$"))
    app.add_handler(CallbackQueryHandler(start_auto_callback, pattern="^start_auto$"))
    app.add_handler(CallbackQueryHandler(stop_auto_callback,  pattern="^stop_auto$"))
    app.add_handler(CallbackQueryHandler(send_once_callback,  pattern="^send_once$"))
    app.add_handler(CallbackQueryHandler(country_menu,      pattern="^set_country$"))
    app.add_handler(CallbackQueryHandler(service_menu,      pattern="^set_service$"))
    app.add_handler(CallbackQueryHandler(type_menu,         pattern="^set_type$"))
    app.add_handler(CallbackQueryHandler(length_menu,       pattern="^set_length$"))
    app.add_handler(CallbackQueryHandler(on_country,        pattern="^c_"))
    app.add_handler(CallbackQueryHandler(on_service,        pattern="^s_"))
    app.add_handler(CallbackQueryHandler(on_type,           pattern="^t_"))
    app.add_handler(CallbackQueryHandler(on_length,         pattern="^l_"))
    app.add_handler(CallbackQueryHandler(groups_menu,       pattern="^groups$"))
    app.add_handler(CallbackQueryHandler(grp_remove_list,   pattern="^grp_rm$"))
    app.add_handler(CallbackQueryHandler(do_remove_group,   pattern="^dg_"))

    logging.info("বট রান হচ্ছে...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
    
