import os
import asyncio
from pyrogram import Client
from plugins import start, instagram, etc  # Importing plugins registers decorators
from webcode import bot_run
from aiohttp import web

API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
PORT = int(os.getenv("PORT", 8080))
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# Create bot instance
bot = Client("igdwbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, workers=50, sleep_threshold=5, in_memory=True)

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
    print("🤖 Bot Started (Decorator + Modular)")

    # Notify admin
    try:
        await bot.send_message(ADMIN_ID, "✅ **Bot restarted successfully!**\nEverything is up and running 🚀")
    except Exception as e:
        print(f"⚠️ Failed to send restart message: {e}")

    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped manually.")

