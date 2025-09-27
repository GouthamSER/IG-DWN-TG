from pyrogram import filters

def register(app):
    @app.on_message(filters.private & filters.command("start"))
    async def start_command(client, message):
        await message.reply(
            "👋 Hello! I am your Instagram Downloader Bot.\n\n"
            "📥 Send me an Instagram link, and I will download the media in HD for you.\n\n"
            "✅ Just make sure the link is valid and public."
        )
