import os
import sys
import psutil
import platform
import time
from pyrogram import filters, __version__ as pyrogram_version
from pyrogram.types import Message
from pyrogram.handlers import MessageHandler
from datetime import datetime

# Load admin ID
ADMIN_ID = int(os.getenv("ADMIN_ID", "6108995220"))

# Track bot start time and message count
START_TIME = time.time()
MESSAGE_COUNT = 0


def format_uptime(seconds: int) -> str:
    """Convert uptime seconds into D:H:M:S format"""
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


# ---------- Handlers ---------- #

async def count_messages(_: "Client", __: Message):
    """Increment message counter for every non-service message."""
    global MESSAGE_COUNT
    MESSAGE_COUNT += 1


async def restart_command(client, message: Message):
    """Admin-only restart command."""
    await message.reply_text("♻️ **Restarting bot on Koyeb...**", quote=True)
    try:
        await client.stop()
        os.execv(sys.executable, [sys.executable, *sys.argv])
    except Exception as e:
        await message.reply_text(f"⚠️ Restart failed:\n`{e}`")


async def status_command(_, message: Message):
    """Public status command."""
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
        f"🌐 **Platform:** `{platform.system()}` (Koyeb)\n"
        f"⚙️ **Pyrogram Version:** `{pyrogram_version}`"
    )

    await message.reply_text(text, quote=True)


async def ping_command(_, message: Message):
    """Public /ping command — shows latency."""
    start = datetime.now()
    reply = await message.reply_text("🏓 Pinging...")
    latency = (datetime.now() - start).microseconds / 1000
    await reply.edit_text(f"🏓 **Pong!**\n⚡ **{latency:.2f} ms**\n🌐 **Host:** Koyeb Server")


# ---------- Register Function ---------- #

def register(app):
    """Attach all handlers to the bot instance."""
    # Message counter (for all)
    app.add_handler(MessageHandler(count_messages, filters.all & ~filters.service))

    # Admin-only restart command
    app.add_handler(MessageHandler(restart_command, filters.command("restart") & filters.user(ADMIN_ID)))

    # Public status command
    app.add_handler(MessageHandler(status_command, filters.command("status")))

    # Public ping command
    app.add_handler(MessageHandler(ping_command, filters.command("ping")))
