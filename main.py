import os
from pyrogram import Client
from plugins.webcode import bot_run  # must return aiohttp.web.Application
from aiohttp import web as webserver

# Load environment variables
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", "8080"))

class Bot(Client):
    async def start(self):
        await super().start()

        # Setup aiohttp server after Pyrogram client starts
        app = await bot_run()  # make sure bot_run() returns aiohttp.web.Application
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
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=50,
    plugins={"root": "plugins"},  # loads all handlers from plugins/
    sleep_threshold=5,
)

if __name__ == "__main__":
    bot.run()
