import os
import aiohttp
import asyncio
import tempfile
import shutil
from pyrogram import Client, filters
from pyrogram.types import Message

# ───────────────────────────────
# 🔧 CONFIG
API_ID = int(os.getenv("API_ID", "12345"))          # from my.telegram.org
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")

# MediaDL API endpoint (tested pattern)
MEDIA_DL_API = "https://www.mediadl.app/api/ajaxSearch"

# ───────────────────────────────
# 🚀 Initialize Bot
app = Client("mediadl_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


async def fetch_media_from_mediadl(insta_url: str):
    """
    Sends request to MediaDL backend to retrieve downloadable URLs.
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
            data = await resp.json()
            return data


async def download_file(session: aiohttp.ClientSession, media_url: str, tmp_dir: str) -> str:
    """
    Downloads file asynchronously and saves to temp directory.
    """
    fname = media_url.split("?")[0].split("/")[-1]
    path = os.path.join(tmp_dir, fname)
    async with session.get(media_url, timeout=60) as resp:
        if resp.status != 200:
            raise Exception(f"Download failed: {resp.status}")
        with open(path, "wb") as f:
            f.write(await resp.read())
    return path


@app.on_message(filters.command("start"))
async def start_cmd(_, message: Message):
    await message.reply_text(
        "👋 Hey! Send me a **public Instagram Reel, Post, or Story link** and I'll download it for you in HD."
    )


@app.on_message(filters.regex(r"(https?://(www\.)?instagram\.com[^\s]+)"))
async def handle_instagram(_, message: Message):
    url = message.matches[0].group(1)
    await message.reply_text("🔍 Fetching media from Instagram... Please wait.")
    tmp = tempfile.mkdtemp(prefix="mediadl_")

    try:
        data = await fetch_media_from_mediadl(url)
        # MediaDL typically returns `data["links"]` list with URLs
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


if __name__ == "__main__":
    print("🚀 Bot is running...")
    app.run()
