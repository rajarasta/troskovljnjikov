"""Chat endpoint - per-item chat with LLM context powered by PydanticAI."""
from __future__ import annotations

import base64
import io
import logging
from typing import Any

from PIL import Image

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.boq import BoQItem, ChatMessage
from app.schemas.boq import ChatMessageSchema, ChatRequest
from app.services.llm_settings import run_with_settings, run_stream_with_settings
from app.ws.events import CHAT_TOKEN, CHAT_COMPLETE, emit

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# PydanticAI agent for chat
# ---------------------------------------------------------------------------

_chat_model = OpenAIModel(
    settings.LLM_MODEL_NAME,
    provider=OpenAIProvider(base_url=settings.LLM_BASE_URL),
)

chat_agent = Agent(
    model=_chat_model,
    system_prompt=(
        "You are a construction cost estimation assistant for Croatian BOQ (Bill of Quantities) projects. "
        "You help users understand BOQ items, compare prices, and make pricing decisions. "
        "Answer concisely and in the same language as the user's message. "
        "When discussing prices, always mention the currency (EUR or HRK) and reference the source data. "
        "If the item context is provided, use it to give informed answers."
    ),
)


_IMAGE_MAX_DIM = 768  # px – longest side after resize
_IMAGE_JPEG_QUALITY = 75


def _compress_image(raw: bytes, content_type: str) -> tuple[str, str]:
    """Resize and compress an uploaded image, return (b64_string, mime_type)."""
    img = Image.open(io.BytesIO(raw))
    img = img.convert("RGB")  # ensure no alpha for JPEG

    # Resize if larger than max dimension
    w, h = img.size
    if max(w, h) > _IMAGE_MAX_DIM:
        scale = _IMAGE_MAX_DIM / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=_IMAGE_JPEG_QUALITY, optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return b64, "image/jpeg"


def _build_item_context(item: BoQItem) -> str:
    """Build a textual context block from a BoQItem for the LLM prompt."""
    parts: list[str] = [
        f"Item ID: {item.id}",
        f"Description: {item.description or 'N/A'}",
    ]
    if item.full_description:
        parts.append(f"Full description: {item.full_description}")
    if item.unit:
        parts.append(f"Unit: {item.unit}")
    if item.quantity:
        parts.append(f"Quantity: {item.quantity}")
    if item.unit_price:
        parts.append(f"Unit price: {item.unit_price}")
    if item.total:
        parts.append(f"Total: {item.total}")
    if item.item_number:
        parts.append(f"Item number: {item.item_number}")
    if item.project_name:
        parts.append(f"Project: {item.project_name}")
    if item.date:
        parts.append(f"Date: {item.date}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/chat/{item_id}", response_model=list[ChatMessageSchema])
def get_chat_history(item_id: str, db: Session = Depends(get_db)) -> list[ChatMessage]:
    """Return the full chat history for a given item."""
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.item_id == item_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    return messages


@router.post("/chat/{item_id}", response_model=ChatMessageSchema)
async def send_chat_message(
    item_id: str,
    req: ChatRequest,
    db: Session = Depends(get_db),
) -> ChatMessage:
    """Send a user message, run it through the LLM with item context, and return the assistant reply."""
    try:
        # For selection-based chats (e.g. "sel-1-1708012345"), skip DB item
        # lookup — context is embedded in the message content by the frontend.
        if item_id.startswith("sel-"):
            item = None
        else:
            item = db.query(BoQItem).filter(BoQItem.id == item_id).first()

        # Build conversation history for the LLM
        history = (
            db.query(ChatMessage)
            .filter(ChatMessage.item_id == item_id)
            .order_by(ChatMessage.created_at)
            .all()
        )

        # Compose the prompt with item context and conversation history
        prompt_parts: list[str] = []

        if item:
            prompt_parts.append("=== BOQ Item Context ===")
            prompt_parts.append(_build_item_context(item))
            prompt_parts.append("")

        if history:
            prompt_parts.append("=== Conversation History ===")
            for msg in history[-10:]:  # Last 10 messages to stay within context limits
                prompt_parts.append(f"{msg.role}: {msg.content}")
            prompt_parts.append("")

        prompt_parts.append(f"user: {req.message}")

        full_prompt = "\n".join(prompt_parts)

        # Persist the user message
        user_msg = ChatMessage(item_id=item_id, role="user", content=req.message)
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)

        # Call the LLM
        try:
            result = await run_with_settings("chat", chat_agent, full_prompt)
            assistant_content = result.output
        except Exception as exc:
            logger.exception("LLM call failed for chat item %s", item_id)
            assistant_content = f"Sorry, I encountered an error: {exc}"

        # Persist the assistant reply
        assistant_msg = ChatMessage(item_id=item_id, role="assistant", content=assistant_content)
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        return assistant_msg
    except Exception as exc:
        logger.exception("Chat endpoint failed for %s", item_id)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/chat/{item_id}/image", response_model=ChatMessageSchema)
async def send_chat_message_with_image(
    item_id: str,
    message: str = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ChatMessage:
    """Send a user message with an attached image through the LLM."""
    try:
        # Read, resize, and compress image to reduce token count
        image_bytes = await image.read()
        b64_string, content_type = _compress_image(image_bytes, image.content_type or "image/jpeg")

        # Build item context (same as text-only endpoint)
        if item_id.startswith("sel-"):
            item = None
        else:
            item = db.query(BoQItem).filter(BoQItem.id == item_id).first()

        history = (
            db.query(ChatMessage)
            .filter(ChatMessage.item_id == item_id)
            .order_by(ChatMessage.created_at)
            .all()
        )

        prompt_parts: list[str] = []

        if item:
            prompt_parts.append("=== BOQ Item Context ===")
            prompt_parts.append(_build_item_context(item))
            prompt_parts.append("")

        if history:
            prompt_parts.append("=== Conversation History ===")
            for msg in history[-10:]:
                prompt_parts.append(f"{msg.role}: {msg.content}")
            prompt_parts.append("")

        prompt_parts.append(f"user: {message}")
        prompt_parts.append(f"![attached image](data:{content_type};base64,{b64_string})")

        full_prompt = "\n".join(prompt_parts)

        # Persist user message (text only - images not stored in DB)
        user_msg = ChatMessage(item_id=item_id, role="user", content=message)
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)

        # Call the LLM
        try:
            result = await run_with_settings("chat", chat_agent, full_prompt)
            assistant_content = result.output
        except Exception as exc:
            logger.exception("LLM call failed for chat item %s (with image)", item_id)
            assistant_content = f"Sorry, I encountered an error: {exc}"

        # Persist assistant reply
        assistant_msg = ChatMessage(item_id=item_id, role="assistant", content=assistant_content)
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        return assistant_msg
    except Exception as exc:
        logger.exception("Chat image endpoint failed for %s", item_id)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/chat/{item_id}/stream", response_model=ChatMessageSchema)
async def send_chat_message_stream(
    item_id: str,
    req: ChatRequest,
    db: Session = Depends(get_db),
) -> ChatMessage:
    """Send a user message, stream the LLM response via WebSocket tokens, return final message."""
    try:
        if item_id.startswith("sel-"):
            item = None
        else:
            item = db.query(BoQItem).filter(BoQItem.id == item_id).first()

        history = (
            db.query(ChatMessage)
            .filter(ChatMessage.item_id == item_id)
            .order_by(ChatMessage.created_at)
            .all()
        )

        prompt_parts: list[str] = []
        if item:
            prompt_parts.append("=== BOQ Item Context ===")
            prompt_parts.append(_build_item_context(item))
            prompt_parts.append("")
        if history:
            prompt_parts.append("=== Conversation History ===")
            for msg in history[-10:]:
                prompt_parts.append(f"{msg.role}: {msg.content}")
            prompt_parts.append("")
        prompt_parts.append(f"user: {req.message}")

        full_prompt = "\n".join(prompt_parts)

        # Persist the user message
        user_msg = ChatMessage(item_id=item_id, role="user", content=req.message)
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)

        # Stream the LLM response
        accumulated = ""
        try:
            async with await run_stream_with_settings("chat", chat_agent, full_prompt) as stream:
                async for token in stream.stream_text(delta=True):
                    accumulated += token
                    await emit(CHAT_TOKEN, {
                        "item_id": item_id,
                        "token": token,
                    })
        except Exception as exc:
            logger.exception("LLM stream failed for chat item %s", item_id)
            accumulated = f"Sorry, I encountered an error: {exc}"

        # Persist the assistant reply
        assistant_msg = ChatMessage(item_id=item_id, role="assistant", content=accumulated)
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        # Signal completion
        await emit(CHAT_COMPLETE, {"item_id": item_id})

        return assistant_msg
    except Exception as exc:
        logger.exception("Chat stream endpoint failed for %s", item_id)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
