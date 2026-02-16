"""
Vision Agent - Analyzes construction site photos to identify work items.

Uses a PydanticAI agent with a vision-capable model on llama-server to
inspect site photographs and identify visible construction work items,
assess progress, and estimate confidence levels.

NOTE: This agent requires a vision-capable model to be loaded on the
llama-server (e.g. LLaVA, Obsidian, or similar multimodal GGUF).
"""
from __future__ import annotations

import base64

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.config import settings
from app.services.llm_settings import run_with_settings

# ---------------------------------------------------------------------------
# Pydantic models for structured output
# ---------------------------------------------------------------------------


class IdentifiedItem(BaseModel):
    """A single construction work item identified in a photo."""

    description: str = Field(
        description="Description of the identified construction work item",
    )
    status: str = Field(
        description=(
            "Completion status: 'completed', 'in_progress', 'not_started', "
            "or 'unclear'"
        ),
    )
    location_in_image: str = Field(
        description="Where in the image this item is visible (e.g. 'center', 'left side', 'background')",
    )


class PhotoAnalysis(BaseModel):
    """Complete analysis result for a construction site photo."""

    items_identified: list[str] = Field(
        description="List of construction work item descriptions visible in the photo",
    )
    detailed_items: list[IdentifiedItem] = Field(
        default_factory=list,
        description="Detailed breakdown of each identified item with status",
    )
    progress_assessment: str = Field(
        description=(
            "Overall assessment of construction progress visible in the photo, "
            "including stage of work and general observations"
        ),
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall confidence in the analysis (0.0 to 1.0)",
    )


# ---------------------------------------------------------------------------
# LLM model & agent
# ---------------------------------------------------------------------------

_provider = OpenAIProvider(base_url=settings.LLM_BASE_URL)
_model = OpenAIChatModel(model_name=settings.LLM_MODEL_NAME, provider=_provider)

SYSTEM_PROMPT = """\
You are a construction site progress inspector specializing in Croatian construction \
projects. Analyze site photos and identify construction work items that are visible \
or have been completed.

When analyzing a photo:
1. **Identify work items** - List all construction activities visible in the photo. \
Use standard Croatian BOQ terminology where appropriate (e.g. "betonski radovi", \
"armirački radovi", "zidarski radovi", "fasaderski radovi", "krovopokrivački radovi").
2. **Assess completion** - For each item, estimate whether it is completed, in progress, \
or not yet started.
3. **Overall progress** - Provide a summary assessment of the construction stage:
   - Foundation/groundwork (temelji)
   - Structural work (konstrukcija)
   - Envelope/facade (fasada, krov)
   - Interior finishing (unutarnji radovi)
   - MEP (instalacije)
   - Exterior/landscaping (okoliš)
4. **Confidence** - Rate your confidence based on image quality and visibility:
   - 0.8-1.0: Clear photo, items easily identifiable
   - 0.5-0.79: Reasonable photo, some items partially visible
   - 0.2-0.49: Poor visibility, significant guessing involved
   - 0.0-0.19: Very unclear, analysis is speculative

Be specific about what you can actually see. Do not hallucinate items that are not \
visible in the photo.\
"""

vision_agent = Agent(
    _model,
    output_type=PhotoAnalysis,
    system_prompt=SYSTEM_PROMPT,
    retries=2,
    model_settings={"temperature": 0.1},
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def analyze_site_photo(
    image_data: str | bytes,
    context: str = "",
) -> PhotoAnalysis:
    """Analyze a construction site photo and identify work items.

    Parameters
    ----------
    image_data : str | bytes
        Either a base64-encoded string of the image, or raw image bytes.
        Supported formats: JPEG, PNG.
    context : str, optional
        Additional context about the project or what to look for.

    Returns
    -------
    PhotoAnalysis
        Analysis result with identified items, progress assessment, and
        confidence score.

    Notes
    -----
    This function requires a vision-capable model to be loaded on the
    llama-server. If a text-only model is running, the agent will not be
    able to process the image content.
    """
    # Ensure we have a base64 string
    if isinstance(image_data, bytes):
        b64_string = base64.b64encode(image_data).decode("ascii")
    else:
        b64_string = image_data

    # Build the multimodal prompt using OpenAI-compatible image_url format.
    # PydanticAI passes this through to the OpenAI-compatible API.
    prompt_parts: list[str] = [
        "Analyze this construction site photo and identify all visible work items.",
    ]
    if context:
        prompt_parts.append(f"Additional context: {context}")
    prompt_parts.append(
        f"![site photo](data:image/jpeg;base64,{b64_string})"
    )

    result = await run_with_settings("vision", vision_agent, "\n".join(prompt_parts))
    return result.output
