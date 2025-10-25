import os
import re
import json
import httpx
import asyncio
import tempfile
import instaloader
from io import BytesIO
from aiohttp import web
from pyrogram import Client, filters
from pyrogram.types import Message

# ============================
# ⚙️ Config
# ============================
API_ID = int(os.getenv("API_ID", "12345"))
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")
PORT = int(os.getenv("PORT", "8080"))
ADMINS = [int(x) for x in os.getenv("ADMINS", "").split(",") if x.strip().isdigit()]

bot = Client("insta_dl_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ============================
# 📥 Downloader Function
# ============================
async def download_instagram_media(insta_url: str):
    """
    Tries multiple APIs, then falls back to Instaloader if all fail.
    Returns (medias, caption)
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/128.0.0.0 Safari/537.36"
        )
    }

    async with httpx.AsyncClient(timeout=40, follow_redirects=True) as client:
        # 1️⃣ FASTDL
        try:
            print("🔹 Trying FastDL...")
            r = await client.post("https://fastdl.app/action.php", data={"url": insta_url}, headers=headers)
            r.raise_for_status()
            text = r.text
            match = re.search(r"(\{.*\"url\".*\})", text)
            if match:
                data = json.loads(match.group(1))
                medias = []
                if "url" in data:
                    medias.append({"url": data["url"], "type": "video" if ".mp4" in data["url"] else "photo"})
                elif "links" in data:
                    for l in data["links"]:
                        medias.append({"url": l["url"], "type": "video" if ".mp4" in l["url"] else "photo"})
                if medias:
                    return medias, data.get("title", "")
            raise Exception("FastDL returned no usable data.")
        except Exception as e:
            print(f"⚠️ FastDL failed: {e}")

        # 2️⃣ SNAPINSTA
        try:
            print("🔹 Trying SnapInsta...")
            r = await client.post("https://snapinsta.app/action.php", data={"url": insta_url}, headers=headers)
            r.raise_for_status()
            text = r.text
            match = re.search(r"(\{.*\"url\".*\})", text)
            if match:
                data = json.loads(match.group(1))
                medias = []
                if "url" in data:
                    medias.append({"url": data["url"], "type": "video" if ".mp4" in data["url"] else "photo"})
                elif "links" in data:
                    for l in data["links"]:
                        medias.append({"url": l["url"], "type": "video" if ".mp4" in l["url"] else "photo"})
                if medias:
                    return medias, data.get("title", "")
            raise Exception("SnapInsta returned no usable data.")
        except Exception as e:
            print(f"⚠️ SnapInsta failed: {e}")

        # 3️⃣ IGRAM
        try:
            print("🔹 Trying iGram...")
            r = await client.post("https://igram.world/api/", data={"url": insta_url}, headers=headers)
            r.raise_for_status()
            j = r.json()
            urls = j.get("url_list") or []
            if urls:
                medias = [{"url": u, "type": "video" if ".mp4" in u else "photo"} for u in urls]
                return medias, j.get("desc", "")
            raise Exception("iGram returned no usable data.")
        except Exception as e:
            print(f"⚠️ iGram failed: {e}")

    # 4️⃣ INSTALOADER (final fallback)
    try:
        print("🔹 Using Instaloader fallback...")
        loader = instaloader.Instaloader(dirname_pattern=tempfile.gettempdir(), save_metadata=False)
        shortcode = re.search(r"/(p|reel|tv)/([^/?]+)", insta_url)
        if not shortcode:
            raise Exception("Invalid Instagram link format.")
        shortcode = shortcode.group(2)
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        medias = []
        if post.is_video:
            medias.append({"url": post.video_url, "type": "video"})
        else:
            medias.append({"url": post.url, "type": "photo"})
        return medias, post.caption or ""
    except Exception as e:
        print(f"⚠️ Instaloader failed: {e}")
        raise Exception("All APIs (FastDL, SnapInsta, iGram, Instaloader) failed.")

# ============================
# 🧠 Caption Trim
# ============================
def trim_caption(caption, footer="\n\n📥 Downloaded via InstaDL Bot"):
    caption = (caption or "").strip()
    footer = footer.strip()
    max_len = 1024
    safe_len = max_len - len(footer) - 5
    if len(caption) > safe_len:
        caption = caption[:safe_len] + "…"
    return f"{caption}\n{footer}" if caption else footer

# ============================
# 🚀 Commands
# ============================
@bot.on_message(filters.command("start"))
async def start_cmd(_, m: Message):
    await m.reply_text(
        "👋 Send me a **public Instagram link** (Reel, Post, Video, Carousel).\n\n"
        "I'll try multiple download methods and send it in HD! 🔥"
    )

# ============================
# 📸 Instagram Handler
# ============================
@bot.on_message(filters.private & filters.text)
async def handle_instagram(client, m: Message):
    url = m.text.strip()
    if "instagram.com" not in url:
        await m.reply_text("⚠️ Please send a valid Instagram link.")
        return

    status = await m.reply_text("🔄 Fetching from multiple sources...")

    try:
        medias, caption = await download_instagram_media(url)
        caption = trim_caption(caption)
        for media in medias:
            if media["type"] == "video":
                await client.send_video(m.chat.id, media["url"], caption=caption)
            else:
                await client.send_photo(m.chat.id, media["url"], caption=caption)
        await status.delete()
    except Exception as e:
        await status.edit(f"❌ Failed: {e}")

# ============================
# 🌐 Web Server (Koyeb Keepalive)
# ============================
async def aiohttp_server():
    async def index(request):
        return web.Response(text="✅ InstaDL Bot alive!", content_type="text/plain")

    app = web.Application()
    app.router.add_get("/", index)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"✅ Web server running on port {PORT}")
    while True:
        await asyncio.sleep(3600)

# ============================
# 🧩 Main Entry
# ============================
async def main():
    web_task = asyncio.create_task(aiohttp_server())
    await bot.start()

    # Notify admins
    if ADMINS:
        me = await bot.get_me()
        text = f"🤖 Bot Online: @{me.username}\n✅ Using FastDL + SnapInsta + iGram + Instaloader"
        for a in ADMINS:
            try:
                await bot.send_message(a, text)
            except Exception:
                pass

    await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot stopped.")
