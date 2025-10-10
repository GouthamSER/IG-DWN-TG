# © GouthamSER — All Rights Reserved
from aiohttp import web

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_handler(request):
    """Basic route to confirm the bot is alive."""
    return web.json_response({"status": "IG-DWN-TG Bot is running 🚀"})

async def bot_run():
    """Creates and returns an aiohttp web app instance."""
    app = web.Application(client_max_size=30_000_000)
    app.add_routes(routes)
    return app
