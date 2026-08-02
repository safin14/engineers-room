from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
from supabase import create_client, Client


TOKEN = "8889835818:AAGAL-r8TBxB6raO2Y08Qy-XZXtR-1vUL7s"
SUPABASE_URL = "https://cxnnikxpljcatpxmifoa.supabase.co"
SUPABASE_KEY = "sb_publishable_gPPDgfTthPSdnV70yHpwDw_9iDmTEPg"

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


chat_ids = [
    8090435198,
    8172077703,
    7534627531,
    7498570406,
    7515472779,
    8358034366
]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    name = user.first_name

    print("Name:", name)
    print("Chat ID:", chat_id)

    data = {
        "name": name,
        "chat_id": chat_id
    }

    supabase.table("telegram_members").upsert(data).execute()

    await update.message.reply_text(
        "Welcome! You are registered ✅"
    )


async def send_reminder():
    bot = Bot(token=TOKEN)

    message = """🍽️ ENGINEERS ROOM

⏰ Meal Entry Reminder

আজকের meal entry এখনো করা হয়নি।
দয়া করে আপনার meal entry সম্পন্ন করুন।

✅ Breakfast
✅ Lunch
✅ Dinner

ধন্যবাদ।"""

    for chat_id in chat_ids:
        await bot.send_message(
            chat_id=chat_id,
            text=message
        )


async def main():

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        send_reminder,
        "cron",
        hour=9,
        minute=0
    )

    scheduler.start()

    print("Bot + Scheduler running...")

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    while True:
        await asyncio.sleep(60)


asyncio.run(main())