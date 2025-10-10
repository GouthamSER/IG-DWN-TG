from pyrogram import filters
from pyrogram.types import Message
from main import bot  # Import the same bot instance

@bot.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    await message.reply(
        "👋 Hello! I am your Instagram Downloader Bot.\n\n"
        "📥 Send me an Instagram link, and I will download the media in HD for you.\n\n"
        "✅ Just make sure the link is valid and public."
    )
