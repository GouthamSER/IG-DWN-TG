import os
import aiohttp
import asyncio
import tempfile
import shutil
from aiohttp import web
from pyrogram import *
from pyrogram.types import *

# ───────────────────────────────
API_ID = int(os.getenv("API_ID", "12345"))
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")
PORT = int(os.getenv("PORT", "8080"))

MEDIA_DL_API = "https://www.mediadl.app/api/ajaxSearch"

app = Client("mediadl_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# ───────────────────────────────
async def fetch_media_from_mediadl(insta_url: str):
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


async def download_file(session: aiohttp.ClientSession, media_url: str, tmp_dir: str, message: Message) -> str:
    fname = media_url.split("?")[0].split("/")[-1]
    path = os.path.join(tmp_dir, fname)

    async with session.get(media_url, timeout=60) as resp:
        if resp.status != 200:
            raise Exception(f"Download failed: {resp.status}")
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 1024 * 32  # 32KB chunks

        with open(path, "wb") as f:
            async for chunk in resp.content.iter_chunked(chunk_size):
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    progress = int(downloaded * 100 / total)
                    try:
                        await message.edit_text(f"⬇️ Downloading... {progress}%")
                    except:
                        pass  # ignore edit errors if message too fast
    return path


# ───────────────────────────────
@app.on_message(filters.command("start"))
async def start_cmd(_, message: Message):
    await message.reply_text(
        "👋 Send me a **public Instagram Reel, Post, or Story link**, "
        "and I’ll download it for you in HD with progress updates."
    )


@app.on_message(filters.regex(r"(https?://(www\.)?instagram\.com[^\s]+)"))
async def handle_instagram(_, message: Message):
    url = message.matches[0].group(1)
    tmp = tempfile.mkdtemp(prefix="mediadl_")
    progress_msg = await message.reply_text("⬇️ Starting download...")

    try:
        data = await fetch_media_from_mediadl(url)
        media_list = data.get("links") or data.get("data") or []

        if not media_list:
            await progress_msg.edit_text("❌ No media found.")
            return

        async with aiohttp.ClientSession() as session:
            for m in media_list:
                media_url = m.get("url") if isinstance(m, dict) else m
                if not media_url:
                    continue
                filepath = await download_file(session, media_url, tmp, progress_msg)

                # Send media
                if filepath.lower().endswith((".mp4", ".mov", ".mkv")):
                    await message.reply_video(video=filepath)
                elif filepath.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    await message.reply_photo(photo=filepath)
                else:
                    await message.reply_document(document=filepath)
        await progress_msg.delete()  # delete progress message after done

    except Exception:
        await progress_msg.edit_text("❌ Failed to download media.")
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
async def main():
    await asyncio.gather(
        app.start(),
        aiohttp_server()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Bot stopped.")
