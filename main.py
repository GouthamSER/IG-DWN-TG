import os
import asyncio
import psutil
import shutil
import aiohttp
import uuid
from pyrogram import Client, filters, idle

# ----------------- Config -----------------
API_ID = int(os.getenv("API_ID", 18979569))
API_HASH = os.getenv("API_HASH", "45db354387b8122bdf6c1b0beef93743")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7383836546:AAHnsD7iK4uVIfZueHAzyQ4Cl6OMnts6EWg")
ADMIN_ID = int(os.getenv("ADMIN_ID", 6108995220))

# Folder to store downloads
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

bot = Client("insta_dl_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------------- Helper Functions ----------------
def get_system_status() -> str:
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    total, used, free = shutil.disk_usage("/")
    storage = used / total * 100
    return f"⚙️ CPU: {cpu}% | 💾 RAM: {ram}% | 🗃️ Storage: {storage:.2f}%"

def measure_ping() -> str:
    import time
    start = time.time()
    end = time.time()
    return f"Pong! 🏓 {(end - start) * 1000:.0f} ms"

async def download_instagram_video(url: str, msg=None) -> str | None:
    """
    Async download Instagram video with live progress.
    Generates a unique filename to allow multiple simultaneous downloads.
    """
    try:
        if "instagram.com" not in url:
            return None

        api_url = f"https://ssinstagram.com/api/convert?url={url}"
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as resp:
                data = await resp.json()
                video_url = data['url'][0]['url']

            # Unique filename
            filename = os.path.join(DOWNLOAD_DIR, f"{uuid.uuid4().hex}.mp4")

            async with session.get(video_url) as vid_resp:
                total_size = int(vid_resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 1024 * 1024  # 1 MB

                with open(filename, "wb") as f:
                    async for chunk in vid_resp.content.iter_chunked(chunk_size):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if msg and total_size > 0:
                            percent = downloaded / total_size * 100
                            await msg.edit_text(f"📥 Downloading video: {percent:.1f}%")
        return filename

    except Exception as e:
        if msg:
            await msg.edit_text(f"❌ Download failed: {e}")
        return None

# ---------------- Commands ----------------
@bot.on_message(filters.command("start"))
async def start(_, msg):
    await msg.reply_text(
        "👋 Hi! Send me any Instagram video link and I’ll send you the HD video!\n\n"
        "Commands:\n/ping\n/status"
    )

@bot.on_message(filters.command("ping"))
async def ping(_, msg):
    await msg.reply_text(measure_ping())

@bot.on_message(filters.command("status"))
async def status(_, msg):
    await msg.reply_text(get_system_status())

@bot.on_message(filters.text & ~filters.command(["start", "ping", "status"]))
async def handle_instagram(_, msg):
    url = msg.text.strip()
    if "instagram.com" not in url:
        return await msg.reply_text("❌ Please send a valid Instagram URL.")
    
    m = await msg.reply_text("📥 Starting download...")
    filename = await download_instagram_video(url, m)
    if not filename:
        return

    await msg.reply_video(filename, caption="✅ Here’s your HD video!")
    os.remove(filename)  # automatic cleanup
    await m.delete()

# ----------------- Startup -----------------
async def main():
    await bot.start()
    # Notify admin
    try:
        await bot.send_message(ADMIN_ID, "🔄 Bot restarted and is now online!")
    except Exception as e:
        print(f"Admin notify failed: {e}")
    print("✅ Bot is running...")
    await idle()
    await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
