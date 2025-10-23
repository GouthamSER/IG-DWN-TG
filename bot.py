import os
import math
import asyncio
import httpx 
from io import BytesIO
from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo
from aiohttp import web
import urllib.parse

# ============================
# ⚙️ Configuration
# ============================
API_ID = int(os.getenv("API_ID", "12345"))
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")
PORT = int(os.getenv("PORT", "8080"))
# NEW: Define a target chat IDs (your personal user IDs) for restart notifications
ADMINS_STR = os.getenv("ADMINS")
ADMINS = []
if ADMINS_STR:
    # Parse ADMINS as a comma-separated list of integer IDs
    try:
        ADMINS = [int(admin_id.strip()) for admin_id in ADMINS_STR.split(',') if admin_id.strip().isdigit()]
    except ValueError:
        print("WARNING: Could not parse ADMINS environment variable. Ensure it is a comma-separated list of integers.")


# Initialize Client
bot = Client("insta_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# ============================
# 📥 Download Instagram Media - USING NEW API (fastdl.app)
# (Contents remain the same)
# ============================
async def download_instagram_media(insta_url: str):
    DOWNLOAD_API_URL = "https://fastdl.app/api/json"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "Referer": "https://fastdl.app/"
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                DOWNLOAD_API_URL,
                params={"url": insta_url},
                headers=headers
            )
            
            resp.raise_for_status() 
            data = resp.json()

    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        if status_code in (500, 502, 503):
            raise Exception(f"Download API failed ({status_code}). The external service is likely down or overloaded.")
        elif status_code == 404:
            raise Exception("Instagram media not found or is private.")
        else:
            raise Exception(f"Download API failed with status code {status_code}.")
    except httpx.ConnectTimeout:
        raise Exception("Connection timed out while reaching the download service.")
    except Exception as e:
        raise Exception(f"An unexpected error occurred during download: {e}")

    medias = data.get("media") or []
    caption = data.get("caption") or ""
    
    if not medias:
        error_message = data.get("error") or data.get("message")
        
        if error_message:
            raise Exception(str(error_message))
        else:
            raise Exception("No media found in the response. It might be a private account or an unsupported link.")

    return medias, caption

# ============================
# 🧰 Helper Functions
# (Contents remain the same)
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
# (Contents remain the same)
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
# (Contents remain the same)
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
        await message.reply_text(
            "⚠️ Please send a valid **Instagram link** only!\nExample:\n`https://www.instagram.com/reel/...`"
        )
        return

    status_msg = await message.reply(f"🔄 Downloading in HD...\n🔗 {content}")
    try:
        medias, original_caption = await download_instagram_media(content)
        
        if isinstance(medias, dict):
             medias = [medias]
             
        photos = [m for m in medias if m.get("type", "").lower() in ("photo", "image") or ('cdn_url' in m and 'video' not in m.get('type',''))]
        videos = [m for m in medias if m.get("type", "").lower() == "video" or 'video' in m.get('type','')]

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
                if t == "video":
                    tasks.append(safe_send_video(message.chat.id, m, caption=cap))
                elif t in ("photo", "image"):
                    tasks.append(safe_send_photo(message.chat.id, m, caption=cap))
            await asyncio.gather(*tasks)

        await status_msg.edit(f"✅ Done! Sent in HD.\n🔗 {content}")

    except Exception as e:
        await status_msg.edit(f"❌ Failed: {e}\n🔗 {content}")

# ============================
# 🌐 AIOHTTP Keep-Alive Server
# (Contents remain the same)
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
    """Runs the web server and the bot client."""
    
    # 1. Start the web server in the background
    web_server_task = asyncio.create_task(aiohttp_server())

    # 2. Start the Pyrogram client
    await bot.start()
    
    # 3. Send startup notification to all ADMINS
    if ADMINS:
        bot_info = None
        try:
            bot_info = await bot.get_me()
        except Exception as e:
            print(f"WARNING: Could not fetch bot info for startup message. Error: {e}")
            
        
        message_text = (
            f"🤖 **Bot Restarted Successfully!**\n\n"
            f"**Name:** @{bot_info.username if bot_info else 'N/A'}\n"
            f"**Time:** {asyncio.get_event_loop().time():.2f}s after loop start."
        )
            
        tasks = []
        for admin_id in ADMINS:
            tasks.append(
                bot.send_message(
                    chat_id=admin_id,
                    text=message_text,
                    disable_notification=True # Optional: Send silently
                )
            )
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"ERROR: Failed to send startup notification to ADMIN ID {ADMINS[i]}. Error: {result}")
            
    # 4. Wait indefinitely until the bot is stopped
    await asyncio.Future()

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Bot shutdown initiated by user.")
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        # Ensure the client stops cleanly
        try:
            loop.run_until_complete(bot.stop())
        except Exception:
            pass
        print("Bot has stopped.")
