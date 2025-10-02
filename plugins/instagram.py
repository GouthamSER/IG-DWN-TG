import httpx
from io import BytesIO
from pyrogram import filters, Client
from pyrogram.handlers import MessageHandler
from pyrogram.types import InputMediaPhoto, InputMediaVideo


async def download_instagram_media(insta_url: str):
    """Fetch media list from mediadl API (async) with robust error handling."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://www.mediadl.app/api/download",
            json={"url": insta_url, "hd": True},
            timeout=30
        )

        # parse JSON safely
        try:
            data = resp.json()
        except Exception:
            text = resp.text or "<no-body>"
            raise Exception(f"Invalid JSON from API (status {resp.status_code}): {text[:300]}")

    # ensure we have a dict
    if not isinstance(data, dict):
        raise Exception(f"Unexpected API response type: {type(data).__name__} -> {str(data)[:200]}")

    if resp.status_code != 200:
        raise Exception(data.get("error", f"API request failed [{resp.status_code}]"))

    medias = data.get("medias") or data.get("media") or []
    if not medias:
        raise Exception("No media found in response")

    return medias


async def _fetch_bytes(url: str) -> bytes:
    async with httpx.AsyncClient() as client:
        r = await client.get(url, timeout=60)
        r.raise_for_status()
        return r.content


async def handle_link(client: Client, message):
    # support link coming in either text or caption
    content = (getattr(message, "text", None) or getattr(message, "caption", None) or "")
    if "instagram.com" not in content:
        return  # ignore non-Instagram messages

    status_msg = await message.reply("🔄 Downloading in HD...")
    try:
        medias = await download_instagram_media(content)

        # partition media
        photos = [m for m in medias if m.get("type", "").lower() in ("photo", "image")]
        videos = [m for m in medias if m.get("type", "").lower() == "video"]

        # helper to safely send a media URL, fallback to download+upload if URL fails
        async def safe_send_photo(chat_id, url, caption=None):
            try:
                await client.send_photo(chat_id=chat_id, photo=url, caption=caption)
            except Exception:
                b = await _fetch_bytes(url)
                bio = BytesIO(b)
                bio.name = "image.jpg"
                await client.send_photo(chat_id=chat_id, photo=bio, caption=caption)

        async def safe_send_video(chat_id, url, caption=None):
            try:
                await client.send_video(chat_id=chat_id, video=url, caption=caption)
            except Exception:
                b = await _fetch_bytes(url)
                bio = BytesIO(b)
                bio.name = "video.mp4"
                await client.send_video(chat_id=chat_id, video=bio, caption=caption)

        # Telegram media-group limit is 10 items
        MAX_GROUP = 10

        # Case A: photos-only and small enough -> send as gallery
        if photos and not videos and len(photos) <= MAX_GROUP:
            media_group = []
            for i, m in enumerate(photos):
                caption = "📸 Downloaded from Instagram!" if i == 0 else None
                media_group.append(InputMediaPhoto(m["url"], caption=caption))
            try:
                await client.send_media_group(chat_id=message.chat.id, media=media_group)
            except Exception:
                # fallback: individually, with download fallback
                for i, m in enumerate(photos):
                    cap = "📸 Downloaded from Instagram!" if i == 0 else None
                    await safe_send_photo(message.chat.id, m["url"], caption=cap)

        # Case B: videos-only and small enough -> try media_group of videos
        elif videos and not photos and len(videos) <= MAX_GROUP:
            media_group = []
            for i, m in enumerate(videos):
                caption = "🎥 Downloaded from Instagram!" if i == 0 else None
                media_group.append(InputMediaVideo(m["url"], caption=caption))
            try:
                await client.send_media_group(chat_id=message.chat.id, media=media_group)
            except Exception:
                for i, m in enumerate(videos):
                    cap = "🎥 Downloaded from Instagram!" if i == 0 else None
                    await safe_send_video(message.chat.id, m["url"], caption=cap)

        # Case C: mixed or too-many items -> send individually with safe helpers
        else:
            for i, m in enumerate(medias):
                url = m.get("url")
                t = m.get("type", "").lower()
                if t == "video":
                    cap = "🎥 Downloaded from Instagram!" if i == 0 else None
                    await safe_send_video(message.chat.id, url, caption=cap)
                elif t in ("photo", "image"):
                    cap = "📸 Downloaded from Instagram!" if i == 0 else None
                    await safe_send_photo(message.chat.id, url, caption=cap)
                else:
                    # unknown type — skip (or you can log it)
                    print(f"⚠️ Skipped unsupported media type: {t}")

        await status_msg.edit("✅ Done! Sent in HD.")

    except Exception as e:
        await status_msg.edit(f"❌ Failed: {e}")


def register(app: Client):
    app.add_handler(MessageHandler(handle_link, filters.private & filters.text))
