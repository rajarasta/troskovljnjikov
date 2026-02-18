import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import settings
from app.database import create_tables, seed_default_presets
from app.routers import upload, files, items, agents, chat, export, pipeline, presets, completion, autopilot, llm_settings, price_search
from app.ws.manager import manager

logger = logging.getLogger(__name__)


class CatchAllMiddleware:
    """Raw ASGI middleware that catches unhandled exceptions.

    Returns JSON 500 responses so CORSMiddleware (outer) can add CORS headers.
    Only handles HTTP requests; passes through WebSocket/lifespan unchanged.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False
        original_send = send

        async def send_wrapper(message):
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await original_send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            logger.exception(
                "Unhandled %s on %s %s",
                type(exc).__name__,
                scope.get("method", "?"),
                scope.get("path", "?"),
            )
            if not response_started:
                # Don't expose error details in production
                error_detail = "Internal server error"
                # Only include details in development mode
                if settings.DEBUG:
                    error_detail = f"Internal server error: {type(exc).__name__}"

                response = JSONResponse(
                    status_code=500,
                    content={"detail": error_detail},
                )
                await response(scope, receive, original_send)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    seed_default_presets()
    yield


app = FastAPI(
    title="BOQ Matcher",
    description="Construction Bill of Quantities matching and pricing",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware stack (outermost first):
# ServerErrorMiddleware -> CORSMiddleware -> CatchAllMiddleware -> ExceptionMiddleware -> Router
#
# Starlette's add_middleware() inserts at position 0, so the LAST call
# becomes the OUTERMOST middleware. We need CORS outside CatchAll so that
# error JSONResponses from CatchAll get CORS headers added by CORS.
app.add_middleware(CatchAllMiddleware)      # inner: catches exceptions, returns JSON 500
app.add_middleware(                         # outer: adds CORS headers to ALL responses
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(files.router, prefix="/api", tags=["files"])
app.include_router(items.router, prefix="/api", tags=["items"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(export.router, prefix="/api", tags=["export"])
app.include_router(pipeline.router, prefix="/api", tags=["pipeline"])
app.include_router(presets.router, prefix="/api", tags=["presets"])
app.include_router(completion.router, prefix="/api", tags=["completion"])
app.include_router(autopilot.router, prefix="/api", tags=["autopilot"])
app.include_router(llm_settings.router, prefix="/api", tags=["llm-settings"])
app.include_router(price_search.router, prefix="/api", tags=["price-search"])

# Static file serving for uploaded drawings (must come AFTER router registrations)
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time pipeline and agent events."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive by reading incoming messages.
            # Clients can send pings or commands; we discard them for now.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
