import os
import aiohttp
import asyncio
import tempfile
import shutil
from aiohttp import web
from pyrogram import Client, filters
from pyrogram.types import Message

# ───────────────────────────────
# 🔧 CONFIG
API_ID = int(os.getenv("API_ID", "12345"))          # from my.telegram.org
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")
PORT = int(os.getenv("PORT", "8080"))

# MediaDL API endpoint
MEDIA_DL_API = "https://www.mediadl.app/api/ajaxSearch"

# ───────────────────────────────
# 🚀 Initialize Bot
app = Client("mediadl_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# ───────────────────────────────
# 📥 MediaDL Logic
async def fetch_media_from_mediadl(insta_url: str):
    """
    Fetch downloadable media URLs from MediaDL backend.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 12; Mobile)",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {"q": insta_url}

    async with aiohttp.ClientSession() as sess:
        async with sess.post(MEDIA_DL_API, data=payload, headers=headers, timeout=30) as resp:
            if resp.status != 200:
                raise Exception(f"MediaDL API Error {resp.status}")
            return await resp.json()


async def download_file(session: aiohttp.ClientSession, media_url: str, tmp_dir: str) -> str:
    """
    Download a file asynchronously and save it locally.
    """
    fname = media_url.split("?")[0].split("/")[-1]
    path = os.path.join(tmp_dir, fname)
    async with session.get(media_url, timeout=60) as resp:
        if resp.status != 200:
            raise Exception(f"Download failed: {resp.status}")
        with open(path, "wb") as f:
            f.write(await resp.read())
    return path


# ───────────────────────────────
# 🤖 Telegram Handlers
@app.on_message(filters.command("start"))
async def start_cmd(_, message: Message):
    await message.reply_text(
        "👋 Hey! Send me a **public Instagram Reel, Post, or Story link**, "
        "and I'll download it for you in HD using MediaDL."
    )


@app.on_message(filters.regex(r"(https?://(www\.)?instagram\.com[^\s]+)"))
async def handle_instagram(_, message: Message):
    url = message.matches[0].group(1)
    await message.reply_text("🔍 Fetching media from Instagram... Please wait.")
    tmp = tempfile.mkdtemp(prefix="mediadl_")

    try:
        data = await fetch_media_from_mediadl(url)
        media_list = data.get("links") or data.get("data") or []

        if not media_list:
            await message.reply_text("❌ No downloadable media found. The post might be private.")
            return

        async with aiohttp.ClientSession() as session:
            for m in media_list:
                media_url = m.get("url") if isinstance(m, dict) else m
                if not media_url:
                    continue

                filepath = await download_file(session, media_url, tmp)
                if filepath.lower().endswith((".mp4", ".mov", ".mkv")):
                    await message.reply_video(video=filepath, caption="🎥 Instagram Video")
                elif filepath.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    await message.reply_photo(photo=filepath, caption="📸 Instagram Photo")
                else:
                    await message.reply_document(document=filepath, caption="📎 Media File")

    except Exception as e:
        await message.reply_text(f"⚠️ Error: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ───────────────────────────────
# 🌐 aiohttp Web Server (for Koyeb/Render)
async def create_web_app():
    """
    Create a minimal aiohttp web app to keep the service alive.
    """

    async def index(request):
        return web.Response(text="✅ Instagram Downloader Bot is Alive!", content_type="text/plain")

    web_app = web.Application()
    web_app.router.add_get("/", index)

    async def start_bot(app):
        print("🚀 Starting Telegram bot...")
        await app["bot"].start()
        print("🤖 Bot started!")

    async def stop_bot(app):
        print("🛑 Stopping Telegram bot...")
        await app["bot"].stop()

    web_app["bot"] = app
    web_app.on_startup.append(start_bot)
    web_app.on_cleanup.append(stop_bot)

    return web_app


async def main():
    """
    Run aiohttp server + Telegram bot concurrently.
    """
    web_app = await create_web_app()
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    print(f"✅ Web server running on port {PORT}")
    while True:
        await asyncio.sleep(3600)  # Keep alive loop


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Server stopped.")
