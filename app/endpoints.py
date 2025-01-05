import logging
from aiohttp import web
from config import HEALTH_CHECK_PORT  # Import health check port from config

async def health_check(request):
    """Health check endpoint."""
    return web.Response(text="OK", status=200)


async def start_aiohttp_app():
    """Start aiohttp web server for health check."""
    app = web.Application()
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", HEALTH_CHECK_PORT)
    await site.start()
    logging.info(f"Health check server started on http://0.0.0.0:{HEALTH_CHECK_PORT}/health")