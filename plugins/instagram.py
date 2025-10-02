import httpx
from pyrogram import filters, Client
from pyrogram.handlers import MessageHandler
from pyrogram.types import InputMediaPhoto, InputMediaVideo


async def download_instagram_media(insta_url: str):
    """Fetch media list from mediadl API (async)."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://www.mediadl.app/api/download",
            json={"url": insta_url, "hd": True},
            timeout=30
        )
        data = resp.json()

    if resp.status_code != 200 or "error" in data:
        raise Exception(data.get("error", f"API request failed [{resp.status_code}]"))

    if "medias" in data and len(data["medias"]) > 0:
        return data["medias"]

    raise Exception("No media found in response")


async def handle_link(client: Client, message):
    if "instagram.com" not in message.text:
        return  # ignore non-Instagram messages

    msg = await message.reply("🔄 Downloading in HD...")
    try:
        medias = await download_instagram_media(message.text)

        # Separate photos and videos
        photos = [m for m in medias if m.get("type", "").lower() in ["photo", "image"]]
        videos = [m for m in medias if m.get("type", "").lower() == "video"]

        # Case 1: All are photos → send as media group (gallery)
        if photos and not videos:
            media_group = []
            for i, m in enumerate(photos):
                if i == 0:
                    media_group.append(InputMediaPhoto(m["url"], caption="📸 Downloaded from Instagram!"))
                else:
                    media_group.append(InputMediaPhoto(m["url"]))
            await client.send_media_group(chat_id=message.chat.id, media=media_group)

        # Case 2: Mixed (photos + videos) or only videos → send individually
        else:
            for m in medias:
                media_url = m["url"]
                media_type = m.get("type", "").lower()

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

        await msg.edit("✅ Done! Sent in HD.")

    except Exception as e:
        await msg.edit(f"❌ Failed: {str(e)}")


def register(app: Client):
    app.add_handler(MessageHandler(handle_link, filters.private & filters.text))
