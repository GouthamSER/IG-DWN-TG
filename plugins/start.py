from pyrogram import filters, Client
from pyrogram.handlers import MessageHandler

async def start_command(client: Client, message):
    await message.reply(
        "👋 Hello! I am your Instagram Downloader Bot.\n\n"
        "📥 Send me an Instagram link, and I will download the media in HD for you.\n\n"
        "✅ Just make sure the link is valid and public."
    )

def register(app: Client):
    app.add_handler(MessageHandler(start_command, filters.private & filters.command("start")))
