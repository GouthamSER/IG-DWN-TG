import os
import asyncio
from pyrogram import Client
from plugins import start, instagram, etc  # Import plugins
from webcode import bot_run
from aiohttp import web

API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
PORT = int(os.getenv("PORT", 8080))
ADMIN_ID = int(os.getenv("ADMIN_ID", 6108995220))

# ------------------- Bot Instance -------------------
bot = Client(
    "igdwbot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=50,
    sleep_threshold=5,
    in_memory=True
)

# ------------------- Register Plugins -------------------
start.register(bot)
instagram.register(bot)
etc.register(bot)

# ------------------- Startup -------------------
async def main():
    await bot.start()

    # Start aiohttp server
    app = await bot_run()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    print(f"🌐 Webserver running on port {PORT}")
    print("🤖 Bot Started (Modular + Async)")

    # Notify admin about restart
    try:
        await bot.send_message(ADMIN_ID, "✅ **Bot restarted successfully!**\nEverything is up and running 🚀")
    except Exception as e:
        print(f"⚠️ Failed to send restart message: {e}")

    await asyncio.Event().wait()  # keep bot running

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped manually.")
