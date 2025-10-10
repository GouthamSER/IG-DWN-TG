# © GouthamSER — All Rights Reserved
from pyrogram import Client, filters
from pyrogram.types import Message


@Client.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    await message.reply(
        "👋 **Hello! I'm your Instagram Downloader Bot.**\n\n"
        "📥 Just send me an Instagram link — photo, video, or reel — "
        "and I’ll fetch it for you in HD quality.\n\n"
        "✅ *Make sure the link is valid and public.*"
    )
