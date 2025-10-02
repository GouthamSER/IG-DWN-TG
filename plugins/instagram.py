# GOUTHAMSER ALL RIGHT RESERVED !!!!!!!!!!!!!!-------------------------------------
import httpx
import asyncio
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

        try:
            data = resp.json()
        except Exception:
            text = resp.text or "<no-body>"
            raise Exception(f"Invalid JSON from API (status {resp.status_code}): {text[:300]}")

    if not isinstance(data, dict):
        raise Exception(f"Unexpected API response: {type(data).__name__}")

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
    # Support link in either text or caption
    content = (getattr(message, "text", None) or getattr(message, "caption", None) or "")
    if "instagram.com" not in content:
        return

    status_msg = await message.reply(f"🔄 Downloading in HD...\n🔗 {content}")
    try:
        medias = await download_instagram_media(content)

        photos = [m for m in medias if m.get("type", "").lower() in ("photo", "image")]
        videos = [m for m in medias if m.get("type", "").lower() == "video"]

        # Safe senders (fallback to file upload if Telegram blocks URL)
        async def safe_send_photo(chat_id, url, caption=None):
            try:
                await client.send_photo(chat_id=chat_id, photo=url, caption=caption)
            except Exception:
                b = await _fetch_bytes(url)
                bio = BytesIO(b); bio.name = "image.jpg"
                await client.send_photo(chat_id=chat_id, photo=bio, caption=caption)

        async def safe_send_video(chat_id, url, caption=None):
            try:
                await client.send_video(chat_id=chat_id, video=url, caption=caption)
            except Exception:
                b = await _fetch_bytes(url)
                bio = BytesIO(b); bio.name = "video.mp4"
                await client.send_video(chat_id=chat_id, video=bio, caption=caption)

        MAX_GROUP = 10  # Telegram media-group limit

        # Case A: photos-only gallery
        if photos and not videos and len(photos) <= MAX_GROUP:
            media_group = [
                InputMediaPhoto(m["url"], caption="📸 Downloaded from Instagram!" if i == 0 else None)
                for i, m in enumerate(photos)
            ]
            try:
                await client.send_media_group(chat_id=message.chat.id, media=media_group)
            except Exception:
                await asyncio.gather(*[
                    safe_send_photo(message.chat.id, m["url"], caption="📸 Downloaded from Instagram!" if i == 0 else None)
                    for i, m in enumerate(photos)
                ])

        # Case B: videos-only gallery
        elif videos and not photos and len(videos) <= MAX_GROUP:
            media_group = [
                InputMediaVideo(m["url"], caption="🎥 Downloaded from Instagram!" if i == 0 else None)
                for i, m in enumerate(videos)
            ]
            try:
                await client.send_media_group(chat_id=message.chat.id, media=media_group)
            except Exception:
                await asyncio.gather(*[
                    safe_send_video(message.chat.id, m["url"], caption="🎥 Downloaded from Instagram!" if i == 0 else None)
                    for i, m in enumerate(videos)
                ])

        # Case C: mixed or too many -> parallel sending
        else:
            tasks = []
            for i, m in enumerate(medias):
                url = m.get("url")
                t = m.get("type", "").lower()
                cap = "🎥 Downloaded from Instagram!" if t == "video" and i == 0 else None
                if t in ("photo", "image") and i == 0:
                    cap = "📸 Downloaded from Instagram!"
                if t == "video":
                    tasks.append(safe_send_video(message.chat.id, url, caption=cap))
                elif t in ("photo", "image"):
                    tasks.append(safe_send_photo(message.chat.id, url, caption=cap))
            await asyncio.gather(*tasks)

        await status_msg.edit(f"✅ Done! Sent in HD.\n🔗 {content}")

    except Exception as e:
        await status_msg.edit(f"❌ Failed: {e}\n🔗 {content}")


def register(app: Client):
    app.add_handler(MessageHandler(handle_link, filters.private & filters.text))


# GOUTHAMSER ALL RIGHT RESERVED !!!!!!!!!!!!!!-------------------------------------
