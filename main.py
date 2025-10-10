# © COPYRIGHT TO https://github.com/GouthamSER
import os
import asyncio
from pyrogram import Client
from plugins import start, instagram
from plugins.webcode import bot_run
from aiohttp import web as webserver

# Load environment variables
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
PORT = int(os.getenv("PORT", "8080"))
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))  # 👈 Add this to your Koyeb environment

class Bot(Client):
    def __init__(self):
        super().__init__(
            name="igdwbot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=50,
            sleep_threshold=5,
            in_memory=True,
        )

    async def start(self):
        await super().start()

        # Register plugins
        start.register(self)
        instagram.register(self)

        # Setup aiohttp webserver
        app = await bot_run()  # must return aiohttp.web.Application
        runner = webserver.AppRunner(app)
        await runner.setup()
        site = webserver.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()

        print(f"🌐 Webserver running on port {PORT}")
        print("🤖 IG-DWN-TG Bot Started (Pyrogram v2) 🫣")

        # Notify admin about restart
        if ADMIN_ID:
            try:
                await self.send_message(
                    ADMIN_ID,
                    "✅ **Bot restarted successfully!**\n\n"
                    "Everything is up and running 🚀"
                )
                print(f"📩 Restart message sent to admin ({ADMIN_ID})")
            except Exception as e:
                print(f"⚠️ Failed to send restart message to admin: {e}")

    async def stop(self, *args):
        await super().stop()
        print("🛑 Bot stopped!")

async def main():
    bot = Bot()
    async with bot:
        await asyncio.Event().wait()  # keeps bot running

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped manually.")

