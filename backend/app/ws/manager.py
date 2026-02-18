"""WebSocket Connection Manager - handles active connections and message broadcasting."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time event streaming with thread-safe operations."""

    def __init__(self) -> None:
        self.active_connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(
            "WebSocket connected. Active connections: %d",
            len(self.active_connections),
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from the active list."""
        async with self._lock:
            self.active_connections.discard(websocket)
        logger.info(
            "WebSocket disconnected. Active connections: %d",
            len(self.active_connections),
        )

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Send a JSON message to all active WebSocket connections.

        Silently removes connections that fail to send.
        Safely handles concurrent modifications to the connection list.
        """
        # Create a snapshot of connections to avoid race conditions
        async with self._lock:
            connections_snapshot = list(self.active_connections)

        stale: list[WebSocket] = []
        for connection in connections_snapshot:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.debug(f"Failed to send message to connection: {e}")
                stale.append(connection)

        # Disconnect stale connections
        for conn in stale:
            await self.disconnect(conn)

    async def send_personal(self, websocket: WebSocket, message: dict[str, Any]) -> None:
        """Send a JSON message to a single WebSocket connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.debug(f"Failed to send personal message: {e}")
            await self.disconnect(websocket)


# Singleton instance used across the application
manager = ConnectionManager()
