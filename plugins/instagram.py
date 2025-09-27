import requests
from pyrogram import filters

def download_instagram_media(insta_url: str):
    resp = requests.post(
        "https://www.mediadl.app/api/download",
        json={"url": insta_url, "hd": True}
    )
    data = resp.json()
    if "medias" in data and len(data["medias"]) > 0:
        return data["medias"]
    raise Exception("No media found in response")

def register(app):
    @app.on_message(filters.private & filters.text)
    async def handle_link(client, message):
        if "instagram.com" not in message.text:
            return

        msg = await message.reply("🔄 Downloading in HD...")
        try:
            medias = download_instagram_media(message.text)

            for media in medias:
                media_url = media["url"]
                media_type = media.get("type", "").lower()

                if media_type == "video":
                    await client.send_video(message.chat.id, media_url, caption="🎥 Downloaded from Instagram!")
                elif media_type in ["photo", "image"]:
                    await client.send_photo(message.chat.id, media_url, caption="📸 Downloaded from Instagram!")

            await msg.delete()
        except Exception as e:
            await msg.edit(f"❌ Failed: {str(e)}")
