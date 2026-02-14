from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_tables
from app.routers import upload, files, items, agents, chat, export, pipeline
from app.ws.manager import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title="BOQ Matcher",
    description="Construction Bill of Quantities matching and pricing",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
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
        manager.disconnect(websocket)
