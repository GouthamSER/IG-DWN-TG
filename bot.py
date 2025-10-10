import os
import psutil
import shutil
import aiohttp
import uuid
from pyrogram import Client, filters

# ----------------- Config -----------------
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

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
    Unique filename to allow multiple simultaneous downloads.
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
@bot.on_message(filters.private & filters.command("start"))
async def start(_, msg):
    await msg.reply_text(
        "👋 Hi! Send me any Instagram video link and I’ll send you the HD video!\n\n"
        "Commands:\n/ping\n/status"
    )

@bot.on_message(filters.private & filters.command("ping"))
async def ping(_, msg):
    await msg.reply_text(measure_ping())

@bot.on_message(filters.private & filters.command("status"))
async def status(_, msg):
    await msg.reply_text(get_system_status())

@bot.on_message(filters.private & ~filters.command(["start", "ping", "status"]))
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

# ---------------- Admin Notification ----------------
@bot.on_message(filters.private & filters.command("admin_notify"))
async def notify_admin_command(_, msg):
    if msg.from_user.id == ADMIN_ID:
        await msg.reply_text("✅ Admin notification test")

async def notify_admin_on_start():
    try:
        await bot.send_message(ADMIN_ID, "🔄 Bot restarted and is now online!")
    except Exception as e:
        print(f"Admin notify failed: {e}")

# ----------------- Startup -----------------
# Register startup task
bot.start()
bot.loop.create_task(notify_admin_on_start())
bot.run()
