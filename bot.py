import os
import aiohttp
import asyncio
import tempfile
import shutil
from pyrogram import Client, filters
from pyrogram.types import Message

API_ID = int(os.getenv("API_ID", "12345"))
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "123456:ABC-DEF")

# Telegram Client
app = Client("insta_api_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------- Instagram API URL ----------
# Many free APIs exist; this one is stable and public
API_URL = "https://instagram-api.savetube.me/api/instagram/media"


async def get_instagram_media(url: str):
    """Fetch downloadable media links using a public API."""
    params = {"url": url}
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL, params=params) as resp:
            if resp.status != 200:
                raise Exception(f"API error: {resp.status}")
            data = await resp.json()
            return data


async def download_file(session, url, tmp_dir):
    """Download media file asynchronously."""
    filename = url.split("?")[0].split("/")[-1]
    filepath = os.path.join(tmp_dir, filename)
    async with session.get(url) as resp:
        if resp.status != 200:
            raise Exception("Download failed")
        with open(filepath, "wb") as f:
            f.write(await resp.read())
    return filepath


@app.on_message(filters.command("start"))
async def start(_, message: Message):
    await message.reply_text(
        "👋 Send me any **public Instagram** reel, post, or story link.\n\n"
        "I’ll fetch and send it in HD (no login needed)."
    )


@app.on_message(filters.regex(r"(https?://(www\.)?instagram\.com[^\s]+)"))
async def instagram_dl(_, message: Message):
    url = message.matches[0].group(1)
    await message.reply_text("🔍 Fetching media from Instagram... Please wait.")
    tmp_dir = tempfile.mkdtemp(prefix="instadl_")

    try:
        data = await get_instagram_media(url)

        # Check valid response
        if not data or "data" not in data or len(data["data"]) == 0:
            await message.reply_text("❌ Could not fetch media. Maybe the post is private.")
            return

        async with aiohttp.ClientSession() as session:
            for item in data["data"]:
                media_url = item.get("url")
                media_type = item.get("type", "")
                if not media_url:
                    continue

                filepath = await download_file(session, media_url, tmp_dir)

                # Send based on type
                if "video" in media_type:
                    await message.reply_video(video=filepath, caption="🎥 Instagram Video")
                elif "image" in media_type:
                    await message.reply_photo(photo=filepath, caption="📸 Instagram Photo")
                else:
                    await message.reply_document(document=filepath, caption="📎 Instagram Media")

    except Exception as e:
        await message.reply_text(f"⚠️ Error: {e}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    print("Bot running...")
    app.run()
