from os import environ
from pyrogram import Client
from plugins.webcode import bot_run
from aiohttp import web as webserver
import asyncio

# Load environment variables
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", "8080"))

class Bot(Client):
    async def start(self):
        await super().start()
        # Setup aiohttp server after Pyrogram client starts
        app = await bot_run()  # assume bot_run returns aiohttp.web.Application
        runner = webserver.AppRunner(app)
        await runner.setup()
        site = webserver.TCPSite(runner, "0.0.0.0", PORT_CODE)
        await site.start()
        print(f"Server started on port {PORT_CODE}")
        print("IG-DWN-TG Bot Started 🫣 ")

    async def stop(self, *args):
        await super().stop()
        # You can also cleanup your aiohttp server here if needed

bot = Bot(
    name="igdwbot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=50,
    plugins={"root": "plugins"},
    sleep_threshold=5,
)

if __name__ == "__main__":
    bot.run()
