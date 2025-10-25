import os
import math
import asyncio
import httpx
from io import BytesIO
from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo
from aiohttp import web
import urllib.parse
import ssl
import certifi
import json

# ============================
# ⚙️ Configuration
# ============================
API_ID = int(os.getenv("API_ID", "12345"))
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")
PORT = int(os.getenv("PORT", "8080"))

ADMINS_STR = os.getenv("ADMINS")
ADMINS = []
if ADMINS_STR:
    try:
        ADMINS = [int(a.strip()) for a in ADMINS_STR.split(',') if a.strip().isdigit()]
    except ValueError:
        print("WARNING: Could not parse ADMINS env var. Use comma-separated integers.")

bot = Client("insta_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
ssl_context = ssl.create_default_context(cafile=certifi.where())

# ============================
# 📥 Download Helpers (multi-API retry)
# ============================

async def try_api_request(client, url, data, headers):
    """Try POST with SSL verification."""
    try:
        resp = await client.post(url, data=data, headers=headers)
        resp.raise_for_status()
        try:
            return resp.json()
        except json.JSONDecodeError:
            raise Exception("Invalid JSON format returned.")
    except Exception as e:
        raise Exception(str(e))


async def download_instagram_media(insta_url: str):
    """Tries multiple APIs for max reliability."""

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
    }
    data_payload = {"url": insta_url, "host": "instagram"}

    apis = [
        ("SaveInsta", "https://saveinsta.io/api/ajax/instgram"),
        ("FastDL", "https://fastdl.app/api/ajax/instagram"),
        ("SnapInsta", "https://snapinsta.app/action.php")
    ]

    async with httpx.AsyncClient(timeout=40, verify=ssl_context) as client:
        for name, api_url in apis:
            try:
                print(f"🔄 Trying {name} API...")
                data = await try_api_request(client, api_url, data_payload, headers)
                medias = data.get("media") or data.get("url_list") or []
                caption = data.get("caption") or data.get("title") or ""

                if medias:
                    print(f"✅ Success from {name} API.")
                    return medias, caption
                else:
                    raise Exception("Empty media list.")
            except Exception as e:
                print(f"⚠️ {name} API failed: {e}")
                continue

    raise Exception("All APIs failed. Media may be private or link unsupported.")


# ============================
# 🧰 Helper Functions
# ============================
def trim_caption(caption: str, footer: str = "\n\n📥 Downloaded from Instagram") -> str:
    if not caption:
        return footer.strip()
    caption = caption.strip()
    footer = footer.strip()
    max_len = 1024
    safe_len = max_len - len(footer) - 15
    if len(caption) > safe_len:
        caption = caption[:safe_len].rstrip() + "… [truncated]"
    return f"{caption}\n\n{footer}"


async def _fetch_bytes(url: str, media_type: str = "File") -> BytesIO:
    async with httpx.AsyncClient(timeout=60, verify=ssl_context) as clientx:
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

    original_content = content
    try:
        parsed_url = urllib.parse.urlparse(content)
        content = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
    except Exception:
        content = original_content
        pass

    if not any(domain in content for domain in ["instagram.com", "www.instagram.com", "instagr.am"]):
        await message.reply_text("⚠️ Please send a valid **Instagram link** only!")
        return

    status_msg = await message.reply(f"🔄 Downloading in HD...\n🔗 {content}")
    try:
        medias, original_caption = await download_instagram_media(content)

        if isinstance(medias, dict):
            medias = [medias]

        photos = [m for m in medias if 'image' in m.get('type', '').lower() or 'jpg' in str(m.get('url', ''))]
        videos = [m for m in medias if 'video' in m.get('type', '').lower() or 'mp4' in str(m.get('url', ''))]
        first_caption = trim_caption(original_caption)

        async def safe_send_photo(chat_id, url_dict, caption=None):
            final_url = url_dict.get('cdn_url') or url_dict.get('url')
            try:
                await client.send_photo(chat_id=chat_id, photo=final_url, caption=caption)
            except:
                bio = await _fetch_bytes(final_url, "Photo")
                await client.send_photo(chat_id=chat_id, photo=bio, caption=caption)

        async def safe_send_video(chat_id, url_dict, caption=None):
            final_url = url_dict.get('cdn_url') or url_dict.get('url')
            try:
                await client.send_video(chat_id=chat_id, video=final_url, caption=caption)
            except:
                bio = await _fetch_bytes(final_url, "Video")
                await client.send_video(chat_id=chat_id, video=bio, caption=caption)

        MAX_GROUP = 10

        if photos and not videos and len(photos) <= MAX_GROUP:
            media_group = [
                InputMediaPhoto(m.get('cdn_url') or m.get('url'), caption=first_caption if i == 0 else None)
                for i, m in enumerate(photos)
            ]
            try:
                await client.send_media_group(chat_id=message.chat.id, media=media_group)
            except Exception:
                await asyncio.gather(*[
                    safe_send_photo(message.chat.id, m, caption=first_caption if i == 0 else None)
                    for i, m in enumerate(photos)
                ])

        elif videos and not photos and len(videos) <= MAX_GROUP:
            media_group = [
                InputMediaVideo(m.get('cdn_url') or m.get('url'), caption=first_caption if i == 0 else None)
                for i, m in enumerate(videos)
            ]
            try:
                await client.send_media_group(chat_id=message.chat.id, media=media_group)
            except Exception:
                await asyncio.gather(*[
                    safe_send_video(message.chat.id, m, caption=first_caption if i == 0 else None)
                    for i, m in enumerate(videos)
                ])

        else:
            tasks = []
            for i, m in enumerate(medias):
                t = m.get("type", "").lower()
                cap = first_caption if i == 0 else None
                if "video" in t:
                    tasks.append(safe_send_video(message.chat.id, m, caption=cap))
                elif "photo" in t or "image" in t:
                    tasks.append(safe_send_photo(message.chat.id, m, caption=cap))
            await asyncio.gather(*tasks)

        await status_msg.edit(f"✅ Done! Sent in HD.\n🔗 {content}")

    except Exception as e:
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


# ============================
# 🚀 Startup Logic
# ============================
async def main():
    asyncio.create_task(aiohttp_server())
    await bot.start()

    if ADMINS:
        try:
            bot_info = await bot.get_me()
            msg = f"🤖 Bot restarted.\nName: @{bot_info.username}\nReady to download!"
            await asyncio.gather(*[bot.send_message(a, msg) for a in ADMINS])
        except Exception as e:
            print("Startup message failed:", e)

    await asyncio.Future()


if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Bot stopped manually.")
    except Exception as e:
        print("Fatal:", e)
    finally:
        try:
            loop.run_until_complete(bot.stop())
        except:
            pass
        print("Bot stopped cleanly.")
