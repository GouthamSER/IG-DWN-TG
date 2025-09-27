# IG-DWN-TG

# Instagram Downloader Bot

A Telegram bot to download Instagram photos and videos in HD, built with **Pyrogram** and modular plugins. Includes a lightweight web server to keep the bot alive on cloud platforms like **Koyeb**.

---

## Features

- Download Instagram photos and videos in HD
- Modular plugin system (`start`, `instagram`, etc.)
- Async-ready structure (can be extended with `httpx`)
- Simple web server for uptime monitoring (`aiohttp`)
- Environment variables for secure credentials

---

## Folder Structure
your_bot/
├── bot.py # Main bot class and runner
├── plugins/
│ ├── start.py # /start command
│ ├── instagram.py # Instagram download handler
│ └── webcode.py # Optional webserver routes
├── requirements.txt # Python dependencies
├── runtime.txt # Python runtime for Koyeb
└── README.md

---

## Requirements

- Python 3.12+
- Pyrogram v2
- tgcrypto
- requests / httpx
- aiohttp

---

### `requirements.txt`

```pyrogram==2.0.108
tgcrypto==1.4.9
requests==2.31.0
httpx==0.26.1
aiohttp==3.9.3
```

`This `README.md` is ready to be included in your GitHub repo and clearly documents the project for anyone using or deploying it.`

