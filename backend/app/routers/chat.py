"""Chat endpoint - per-item chat with LLM context powered by PydanticAI."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.boq import BoQItem, ChatMessage
from app.schemas.boq import ChatMessageSchema, ChatRequest

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
        result = await chat_agent.run(full_prompt)
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
