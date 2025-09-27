import os
import asyncio
from pyrogram import Client
from plugins import start, instagram
from aiohttp import web

# Load environment variables
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", "8080"))

class Bot:
    def __init__(self):
        # Initialize Pyrogram client
        self.app = Client(
            "insta_downloader_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN
        )

        # Register plugins
        self.register_plugins()

    def register_plugins(self):
        start.register(self.app)
        instagram.register(self.app)

    async def start_webserver(self):
        """Start a simple webserver for Koyeb uptime checks."""
        async def handle(request):
            return web.Response(text="Bot is running 🤖")

        server = web.Application()
        server.add_routes([web.get("/", handle)])
        runner = web.AppRunner(server)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
        print(f"🌐 Webserver running on port {PORT}")

    async def run(self):
        """Run both bot and webserver concurrently."""
        await self.app.start()
        print("🤖 Bot started!")

        # Run webserver concurrently
        await self.start_webserver()

        # Keep the bot alive
        try:
            while True:
                await asyncio.sleep(3600)  # sleep in a loop
        finally:
            await self.app.stop()
            print("🤖 Bot stopped.")

if __name__ == "__main__":
    bot = Bot()
    asyncio.run(bot.run())
