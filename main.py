import os
from pyrogram import Client
from plugins import start, instagram
from aiohttp import web
from plugins.webcode import bot_run  # optional if you have a ping route

PORT_CODE = int(os.environ.get("PORT", "8080"))

class Bot:
    def __init__(self):
        # Load environment variables
        self.api_id = int(os.environ.get("API_ID"))
        self.api_hash = os.environ.get("API_HASH")
        self.bot_token = os.environ.get("BOT_TOKEN")

        # Initialize Pyrogram client
        self.app = Client(
            "insta_downloader_bot",
            api_id=self.api_id,
            api_hash=self.api_hash,
            bot_token=self.bot_token
        )

        # Register plugins
        self.register_plugins()

    def register_plugins(self):
        start.register(self.app)
        instagram.register(self.app)

    async def start_webserver(self):
        # Simple webserver to keep Koyeb alive
        async def handle(request):
            return web.Response(text="Bot is running 🤖")

        server = web.Application()
        server.add_routes([web.get("/", handle)])
        runner = web.AppRunner(server)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT_CODE)
        await site.start()
        print(f"🌐 Webserver running on port {PORT_CODE}")

    async def run_bot(self):
        # Start bot and webserver concurrently
        import asyncio
        await asyncio.gather(
            self.app.start(),
            self.start_webserver()
        )
        print("🤖 Bot started!")

        # Keep the bot running
        await self.app.idle()

if __name__ == "__main__":
    import asyncio
    bot = Bot()
    asyncio.run(bot.run_bot())
