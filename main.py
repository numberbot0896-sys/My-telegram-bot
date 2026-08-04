import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)

async def start(update: Update, context):
    await update.message.reply_text("✅ বট সফলভাবে চালু হয়েছে!")

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise SystemExit("BOT_TOKEN পাওয়া যায়নি!")
    
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    
    logging.info("বট রান হচ্ছে...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
    
