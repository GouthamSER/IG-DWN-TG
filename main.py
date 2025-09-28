# © COPYRIGHT TO https://github.com/GouthamSER
import os
from pyrogram import Client
from plugins import start, instagram
from plugins.webcode import bot_run
from aiohttp import web as webserver

# Load environment variables
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", "8080"))
PORT = int(os.environ.get("PORT", "8080"))

class Bot(Client):
    async def start(self):
        await super().start()

        # Register plugins manually
        start.register(self)
        instagram.register(self)

        # Setup aiohttp server
        app = await bot_run()  # must return aiohttp.web.Application
        runner = webserver.AppRunner(app)
        await runner.setup()
        site = webserver.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()

        print(f"🌐 Webserver started on port {PORT}")
        print("🤖 IG-DWN-TG Bot Started 🫣")

    async def stop(self, *args):
        await super().stop()
        print("🛑 Bot stopped!")

# Initialize bot
bot = Bot(
    name="igdwbot",
    api_id=int(os.environ.get("API_ID",)),
    api_hash=os.environ.get("API_HASH", ""),
    bot_token=os.environ.get("BOT_TOKEN", ""),
    workers=50,
    sleep_threshold=5,
)

if __name__ == "__main__":
    bot.run()

