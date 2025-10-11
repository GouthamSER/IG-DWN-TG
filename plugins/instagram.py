import os
import asyncio
from io import BytesIO
from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo
import httpx
from aiohttp import web

# ───────────────────────────────
API_ID = int(os.getenv("API_ID", "12345"))
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")
PORT = int(os.getenv("PORT", "8080"))

bot = Client("insta_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ───────────────────────────────
async def download_instagram_media(insta_url: str):
    """Fetch downloadable Instagram media URLs using MediaDL API"""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://www.mediadl.app/api/download",
            json={"url": insta_url, "hd": True}
        )
        resp.raise_for_status()
        data = resp.json()
    return data.get("medias", [])


async def _fetch_bytes(url: str) -> bytes:
    """Download content as bytes fallback"""
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.content


# ───────────────────────────────
@bot.on_message(filters.command("start"))
async def start_cmd(_, message: Message):
    await message.reply_text(
        "👋 Send me a **public Instagram Reel, Post, or Story link**, "
        "and I will download it in HD using MediaDL."
    )


@bot.on_message(filters.private & filters.text)
async def instagram_handler(client, message: Message):
    content = getattr(message, "text", "") or getattr(message, "caption", "")
    if "instagram.com" not in content.lower():
        return

    status_msg = await message.reply(f"🔄 Downloading in HD...\n🔗 {content}")
    try:
        medias = await download_instagram_media(content)

        photos = [m for m in medias if m.get("type", "").lower() in ("photo", "image")]
        videos = [m for m in medias if m.get("type", "").lower() == "video"]

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

        MAX_GROUP = 10

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
        else:
            tasks = []
            for i, m in enumerate(medias):
                url = m.get("url")
                t = m.get("type", "").lower()
                cap = "🎥 Downloaded from Instagram!" if t=="video" and i==0 else None
                if t in ("photo", "image") and i==0:
                    cap = "📸 Downloaded from Instagram!"
                if t=="video":
                    tasks.append(safe_send_video(message.chat.id, url, caption=cap))
                elif t in ("photo", "image"):
                    tasks.append(safe_send_photo(message.chat.id, url, caption=cap))
            await asyncio.gather(*tasks)

        await status_msg.edit(f"✅ Done! Sent in HD.\n🔗 {content}")

    except Exception as e:
        await status_msg.edit(f"❌ Failed: {e}\n🔗 {content}")


# ───────────────────────────────
async def aiohttp_server():
    async def index(request):
        return web.Response(text="✅ Bot is alive!", content_type="text/plain")

    app_web = web.Application()
    app_web.router.add_get("/", index)
    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"✅ Web server running on port {PORT}")
    while True:
        await asyncio.sleep(3600)


# ───────────────────────────────
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(aiohttp_server())
    bot.run()
