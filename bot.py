import os
import httpx
import asyncio
import tempfile
import shutil
from pyrogram import Client, filters
from pyrogram.types import Message
from aiohttp import web

# ───────────────────────────────
API_ID = int(os.getenv("API_ID", "12345"))
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")
PORT = int(os.getenv("PORT", "8080"))

MEDIA_DL_API = "https://www.mediadl.app/api/ajaxSearch"

bot = Client("insta_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# ───────────────────────────────
async def fetch_media(insta_url: str):
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            MEDIA_DL_API,
            data={"q": insta_url},
            headers={"User-Agent": "Mozilla/5.0"}
        )
        resp.raise_for_status()
        return resp.json()


async def download_file(url: str, tmp_dir: str, message: Message) -> str:
    fname = url.split("?")[0].split("/")[-1]
    path = os.path.join(tmp_dir, fname)

    async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
        r = await client.stream("GET", url)
        total = int(r.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 1024 * 32

        with open(path, "wb") as f:
            async for chunk in r.aiter_bytes(chunk_size):
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    progress = int(downloaded * 100 / total)
                    try:
                        await message.edit_text(f"⬇️ Downloading... {progress}%")
                    except:
                        pass
    return path


# ───────────────────────────────
@bot.on_message(filters.command("start"))
async def start_cmd(_, message: Message):
    await message.reply_text(
        "👋 Send a **public Instagram Reel, Post, or Story link**, and I will download it in HD."
    )


@bot.on_message(filters.regex(r"(https?://(www\.)?instagram\.com[^\s]+)"))
async def insta_handler(_, message: Message):
    tmp = tempfile.mkdtemp(prefix="insta_")
    progress_msg = await message.reply_text("⬇️ Starting download...")

    try:
        data = await fetch_media(message.text)
        media_list = data.get("links") or data.get("data") or []

        if not media_list:
            await progress_msg.edit_text("❌ No media found.")
            return

        for m in media_list:
            media_url = m.get("url") if isinstance(m, dict) else m
            if not media_url:
                continue

            filepath = await download_file(media_url, tmp, progress_msg)

            # Send file
            if filepath.lower().endswith((".mp4", ".mov", ".mkv")):
                await message.reply_video(video=filepath)
            elif filepath.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                await message.reply_photo(photo=filepath)
            else:
                await message.reply_document(document=filepath)

        await progress_msg.delete()

    except Exception as e:
        await progress_msg.edit_text(f"❌ Failed to download media.\n{e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ───────────────────────────────
async def aiohttp_server():
    async def index(request):
        return web.Response(text="✅ Bot is alive!", content_type="text/plain")
    app_web = web.Application()
    app_web.router.add_get("/", index)
    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"✅ Web server running on port {PORT}")
    while True:
        await asyncio.sleep(3600)


# ───────────────────────────────
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(aiohttp_server())
    bot.run()
