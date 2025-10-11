import os
import asyncio
import tempfile
import shutil
from pyrogram import Client, filters
from pyrogram.types import Message
from aiohttp import web
import yt_dlp

# ───────────────────────────────
API_ID = int(os.getenv("API_ID", "12345"))
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")
PORT = int(os.getenv("PORT", "8080"))

bot = Client("insta_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

COOKIES_FILE = "cookies.txt"  # Optional cookies file


# ───────────────────────────────
async def download_instagram_media(url: str, tmp_dir: str, message: Message):
    """
    Download Instagram media using yt-dlp with progress updates.
    Automatically uses cookies.txt if available.
    """
    filename = None

    def progress_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            if total:
                percent = int(downloaded * 100 / total)
                asyncio.create_task(message.edit_text(f"⬇️ Downloading... {percent}%"))
        elif d['status'] == 'finished':
            asyncio.create_task(message.edit_text("✅ Download complete!"))

    ydl_opts = {
        'format': 'best',
        'outtmpl': os.path.join(tmp_dir, '%(title)s.%(ext)s'),
        'progress_hooks': [progress_hook],
        'quiet': True,
        'no_warnings': True
    }

    # Use cookies if file exists
    if os.path.exists(COOKIES_FILE):
        ydl_opts['cookiefile'] = COOKIES_FILE

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([url]))

    # Get downloaded file path
    files = os.listdir(tmp_dir)
    if files:
        filename = os.path.join(tmp_dir, files[0])
    return filename


# ───────────────────────────────
@bot.on_message(filters.command("start"))
async def start_cmd(_, message: Message):
    await message.reply_text(
        "👋 Send me a **public or private Instagram Reel, Post, or Story link**, "
        "and I will download it in HD. Private content requires a valid cookies.txt file."
    )


@bot.on_message(filters.regex(r"(https?://(www\.)?instagram\.com[^\s]+)"))
async def insta_handler(_, message: Message):
    tmp = tempfile.mkdtemp(prefix="insta_")
    progress_msg = await message.reply_text("⬇️ Starting download...")

    try:
        file_path = await download_instagram_media(message.text, tmp, progress_msg)
        if not file_path:
            await progress_msg.edit_text("❌ Failed to download media.")
            return

        # Send file
        if file_path.lower().endswith(('.mp4', '.mov', '.mkv')):
            await message.reply_video(video=file_path)
        elif file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            await message.reply_photo(photo=file_path)
        else:
            await message.reply_document(document=file_path)

        await progress_msg.delete()

    except Exception as e:
        await progress_msg.edit_text(f"❌ Error: {e}")
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
