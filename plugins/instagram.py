from pyrogram.types import InputMediaPhoto, InputMediaVideo

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

        # Case 2: Mixed or only videos → send individually
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
