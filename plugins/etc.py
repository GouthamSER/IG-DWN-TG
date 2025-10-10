import os
import sys
import psutil
import platform
import time
from pyrogram import filters, __version__ as pyrogram_version
from pyrogram.types import Message

# Load admin ID
ADMIN_ID = int(os.getenv("ADMIN_ID", "6108995220"))

# Track bot start time and message count
START_TIME = time.time()
MESSAGE_COUNT = 0

def format_uptime(seconds):
    """Convert uptime seconds into D:H:M:S"""
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days: parts.append(f"{days}d")
    if hours: parts.append(f"{hours}h")
    if minutes: parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)

def register(app):
    global MESSAGE_COUNT

    # Count all non-service messages
    @app.on_message(filters.all & ~filters.service)
    async def count_messages(_, __: Message):
        global MESSAGE_COUNT
        MESSAGE_COUNT += 1

    # Admin-only restart command
    @app.on_message(filters.command("restart") & filters.user(ADMIN_ID))
    async def restart_cmd(client, message):
        await message.reply_text("♻️ **Restarting bot on Koyeb...**", quote=True)
        try:
            await client.stop()
            os.execv(sys.executable, [sys.executable, *sys.argv])
        except Exception as e:
            await message.reply_text(f"⚠️ Restart failed:\n`{e}`")

    # Public status command
    @app.on_message(filters.command("status"))
    async def status_cmd(client, message):
        uptime = format_uptime(time.time() - START_TIME)
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info().rss / (1024 * 1024)
        cpu_usage = process.cpu_percent(interval=0.5)

        text = (
            "📊 **Bot Status Report**\n\n"
            f"🕒 **Uptime:** `{uptime}`\n"
            f"💬 **Messages Handled:** `{MESSAGE_COUNT}`\n"
            f"🧠 **Memory Usage:** `{mem_info:.2f} MB`\n"
            f"💾 **CPU Usage:** `{cpu_usage:.1f}%`\n"
            f"🌐 **Platform:** `{platform.system()}`\n"
            f"⚙️ **Pyrogram Version:** `{pyrogram_version}`"
        )

        await message.reply_text(text, quote=True)
