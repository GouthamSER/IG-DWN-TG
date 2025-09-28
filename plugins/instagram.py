import httpx
from pyrogram import filters, Client
from pyrogram.handlers import MessageHandler

async def download_instagram_media(insta_url: str):
    """Fetch media list from mediadl API (async)."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://www.mediadl.app/api/download",
            json={"url": insta_url, "hd": True},
            timeout=30
        )
        data = resp.json()

    if "medias" in data and len(data["medias"]) > 0:
        return data["medias"]
    raise Exception("No media found in response")


async def handle_link(client: Client, message):
    if "instagram.com" not in message.text:
        return  # ignore non-Instagram messages

    msg = await message.reply("🔄 Downloading in HD...")
    try:
        medias = await download_instagram_media(message.text)

        for media in medias:
            media_url = media["url"]
            media_type = media.get("type", "").lower()

            if media_type == "video":
                await client.send_video(
                    chat_id=message.chat.id,
                    video=media_url,
                    caption="🎥 Downloaded from Instagram!"
                )
            elif media_type in ["photo", "image"]:
                await client.send_photo(
                    chat_id=message.chat.id,
                    photo=media_url,
                    caption="📸 Downloaded from Instagram!"
                )
            else:
                print(f"⚠️ Skipped unsupported media type: {media_type}")

        await msg.delete()
    except Exception as e:
        await msg.edit(f"❌ Failed: {str(e)}")


def register(app: Client):
    app.add_handler(MessageHandler(handle_link, filters.private & filters.text))
