import os
import math
import asyncio
import httpx # Import httpx here for specific exception handling
from io import BytesIO
from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo
from aiohttp import web

# ============================
# ⚙️ Configuration
# ============================
API_ID = int(os.getenv("API_ID", "12345"))
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")
PORT = int(os.getenv("PORT", "8080"))

bot = Client("insta_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ============================
# 📥 Download Instagram Media
# ============================
async def download_instagram_media(insta_url: str):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://www.mediadl.app/api/download",
                json={"url": insta_url, "hd": True}
            )
            # Raise an exception for 4xx or 5xx status codes
            resp.raise_for_status() 
            data = resp.json()

    except httpx.HTTPStatusError as e:
        # Handle 4xx/5xx errors specifically
        status_code = e.response.status_code
        if status_code == 502:
            raise Exception(f"Download API failed (502 Bad Gateway). The external service might be down. Please try again later.")
        elif status_code == 404:
            raise Exception("Instagram media not found or is private.")
        else:
            raise Exception(f"Download API failed with status code {status_code}.")
    except httpx.ConnectTimeout:
        raise Exception("Connection timed out while reaching the download service.")
    except Exception as e:
        # Catch general errors like JSON decoding issues
        raise Exception(f"An unexpected error occurred during download: {e}")

    medias = data.get("medias") or data.get("media") or []
    caption = data.get("title") or data.get("caption") or ""

    if not medias:
        # Check if the API returned an error message in the body
        error_message = data.get("error") or "No media found in response."
        raise Exception(error_message)

    return medias, caption

# ============================
# 🧰 Helper Functions
# ============================
def trim_caption(caption: str, footer: str = "\n\n📥 Downloaded from Instagram") -> str:
    """Ensure total caption ≤ 1024 chars (Telegram limit)."""
    if not caption:
        return footer.strip()

    caption = caption.strip()
    footer = footer.strip()
    max_len = 1024

    # Reserve space for footer and possible truncation note
    safe_len = max_len - len(footer) - 15
    if len(caption) > safe_len:
        caption = caption[:safe_len].rstrip() + "… [truncated]"
    return f"{caption}\n\n{footer}"

async def _fetch_bytes(url: str, media_type: str = "File") -> BytesIO:
    async with httpx.AsyncClient(timeout=60) as clientx:
        r = await clientx.get(url, timeout=60, follow_redirects=True)
        r.raise_for_status()
        bio = BytesIO()
        bio.name = "media.mp4" if media_type.lower() == "video" else "image.jpg"
        async for chunk in r.aiter_bytes(32 * 1024):
            bio.write(chunk)
        bio.seek(0)
        return bio

# ============================
# 🧠 Commands
# ============================
@bot.on_message(filters.command("start"))
async def start_cmd(_, message: Message):
    await message.reply_text(
        "👋 Send me a **public Instagram Reel, Post, or Story link**, "
        "and I’ll download it in HD **with the original caption**.\n\n"
        "⚠️ Only Instagram links are supported!"
    )

# ============================
# ⚙️ Main Instagram Handler
# ============================
@bot.on_message(filters.private & filters.text)
async def handle_link(client, message: Message):
    content = getattr(message, "text", "") or getattr(message, "caption", "")
    content = content.strip()

    # ✅ Only allow Instagram URLs
    if not any(domain in content for domain in ["instagram.com", "www.instagram.com", "instagr.am"]):
        await message.reply_text(
            "⚠️ Please send a valid **Instagram link** only!\nExample:\n`https://www.instagram.com/reel/...`"
        )
        return

    status_msg = await message.reply(f"🔄 Downloading in HD...\n🔗 {content}")
    try:
        medias, original_caption = await download_instagram_media(content)
        photos = [m for m in medias if m.get("type", "").lower() in ("photo", "image")]
        videos = [m for m in medias if m.get("type", "").lower() == "video"]

        # 🧾 Prepare safely trimmed caption
        first_caption = trim_caption(original_caption)

        async def safe_send_photo(chat_id, url, caption=None):
            try:
                await client.send_photo(chat_id=chat_id, photo=url, caption=caption)
            except:
                bio = await _fetch_bytes(url, "Photo")
                await client.send_photo(chat_id=chat_id, photo=bio, caption=caption)

        async def safe_send_video(chat_id, url, caption=None):
            try:
                await client.send_video(chat_id=chat_id, video=url, caption=caption)
            except:
                bio = await _fetch_bytes(url, "Video")
                await client.send_video(chat_id=chat_id, video=bio, caption=caption)

        MAX_GROUP = 10

        # ============================
        # 🖼 Handle Photos Only
        # ============================
        if photos and not videos and len(photos) <= MAX_GROUP:
            media_group = [
                InputMediaPhoto(m["url"], caption=first_caption if i == 0 else None)
                for i, m in enumerate(photos)
            ]
            try:
                await client.send_media_group(chat_id=message.chat.id, media=media_group)
            except Exception:
                await asyncio.gather(*[
                    safe_send_photo(message.chat.id, m["url"], caption=first_caption if i == 0 else None)
                    for i, m in enumerate(photos)
                ])

        # ============================
        # 🎬 Handle Videos Only
        # ============================
        elif videos and not photos and len(videos) <= MAX_GROUP:
            media_group = [
                InputMediaVideo(m["url"], caption=first_caption if i == 0 else None)
                for i, m in enumerate(videos)
            ]
            try:
                await client.send_media_group(chat_id=message.chat.id, media=media_group)
            except Exception:
                await asyncio.gather(*[
                    safe_send_video(message.chat.id, m["url"], caption=first_caption if i == 0 else None)
                    for i, m in enumerate(videos)
                ])

        # ============================
        # 🧩 Mixed or Large Media Set
        # ============================
        else:
            tasks = []
            for i, m in enumerate(medias):
                url = m.get("url")
                t = m.get("type", "").lower()
                cap = first_caption if i == 0 else None
                if t == "video":
                    tasks.append(safe_send_video(message.chat.id, url, caption=cap))
                elif t in ("photo", "image"):
                    tasks.append(safe_send_photo(message.chat.id, url, caption=cap))
            await asyncio.gather(*tasks)

        await status_msg.edit(f"✅ Done! Sent in HD.\n🔗 {content}")

    except Exception as e:
        # The main handler now catches the detailed exceptions from the download function
        await status_msg.edit(f"❌ Failed: {e}\n🔗 {content}")

# ============================
# 🌐 AIOHTTP Keep-Alive Server
# ============================
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

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(aiohttp_server())
    bot.run()
