# © GouthamSER — All Rights Reserved
import os
import sys
import psutil
import platform
import time
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram import __version__ as pyrogram_version

ADMIN_ID = int(os.getenv("ADMIN_ID", 6108995220))
START_TIME = time.time()
MESSAGE_COUNT = 0


def format_uptime(seconds: int) -> str:
    """Format uptime duration nicely."""
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


@Client.on_message(filters.all & ~filters.service)
async def count_messages(_, message: Message):
    """Count every message handled."""
    global MESSAGE_COUNT
    MESSAGE_COUNT += 1


@Client.on_message(filters.command("status"))
async def status_cmd(client, message: Message):
    """Show full bot status (uptime, memory, etc)."""
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


@Client.on_message(filters.command("ping"))
async def ping_cmd(client, message: Message):
    """Simple latency check for all users."""
    start_time = datetime.now()
    reply = await message.reply_text("🏓 Pinging...")
    latency = (datetime.now() - start_time).microseconds / 1000
    await reply.edit_text(f"🏓 Pong!\n⚡ **{latency:.2f} ms**\n🌐 **Host:** Koyeb Server")


@Client.on_message(filters.command("restart") & filters.user(ADMIN_ID))
async def restart_cmd(client, message: Message):
    """Admin-only bot restart."""
    await message.reply_text("♻️ **Restarting bot...**", quote=True)
    try:
        await client.stop()
        os.execv(sys.executable, [sys.executable, *sys.argv])
    except Exception as e:
        await message.reply_text(f"⚠️ Restart failed:\n`{e}`")
