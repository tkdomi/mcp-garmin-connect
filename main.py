import asyncio
import logging

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent
from contextlib import asynccontextmanager
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import JSONResponse
import uvicorn

from src.config import settings
from src.scheduler import start_scheduler, sync_health_data
from src.tools import ALL_TOOLS, dispatch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

mcp = Server("garmin-mcp")


@mcp.list_tools()
async def list_tools():
    return ALL_TOOLS


@mcp.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    logger.info(f"Tool called: {name} | args: {arguments}")
    try:
        result = await dispatch(name, arguments)
        if result is None:
            result = {"error": f"Unknown tool: {name}"}
        return [TextContent(type="text", text=str(result))]
    except Exception as e:
        logger.error(f"Tool error ({name}): {e}")
        return [TextContent(type="text", text=f"Error fetching data: {str(e)}")]


async def health_check(request: Request):
    return JSONResponse({"status": "ok", "service": "garmin-mcp"})


async def manual_sync(request: Request):
    asyncio.create_task(sync_health_data())
    return JSONResponse({"status": "sync_started"})


sse_transport = SseServerTransport("/messages/")


async def handle_sse(request: Request):
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp.run(streams[0], streams[1], mcp.create_initialization_options())


@asynccontextmanager
async def lifespan(app):
    start_scheduler()
    yield


app = Starlette(
    lifespan=lifespan,
    routes=[
        Route("/health", health_check),
        Route("/sync", manual_sync, methods=["POST"]),
        Route("/sse", handle_sse),
        Mount("/messages/", app=sse_transport.handle_post_message),
    ],
)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.mcp_port, log_level="info")
