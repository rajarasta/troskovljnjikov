"""
Document Processor Agent - Example agent that uses document handling skills.

This agent demonstrates how to use PDF, Excel, and Word document skills
to process and analyze documents.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.anthropic import AnthropicModel

from app.config import settings
from app.services.llm_settings import run_with_settings, get_model
from app.services.skill_manager import initialize_skills, setup_agent_skills

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Structured output models
# ---------------------------------------------------------------------------

class ExtractedData(BaseModel):
    """Extracted data from documents."""
    file_path: str = Field(description="Path to the processed file")
    file_type: str = Field(description="Type of file (pdf, xlsx, docx)")
    summary: str = Field(description="Summary of extracted content")
    key_findings: dict[str, Any] = Field(default_factory=dict, description="Important data extracted")
    metadata: dict[str, Any] = Field(default_factory=dict, description="File metadata")


class DocumentProcessingResult(BaseModel):
    """Result of document processing."""
    documents_processed: int = Field(description="Number of documents processed")
    extractions: list[ExtractedData] = Field(default_factory=list)
    combined_analysis: str = Field(default="", description="Analysis across all documents")
    reasoning: str = Field(default="")


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

@dataclass
class DocumentDeps:
    """Dependencies for document processor agent."""
    file_paths: list[str]
    analysis_prompt: str = ""
    _processing_log: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# LLM model & agent
# ---------------------------------------------------------------------------

# Ensure ANTHROPIC_API_KEY is in environment
if settings.ANTHROPIC_API_KEY:
    os.environ["ANTHROPIC_API_KEY"] = settings.ANTHROPIC_API_KEY

_model = AnthropicModel(model_name=settings.CLAUDE_MODEL)

SYSTEM_PROMPT = """\
You are a document processing specialist. Your task is to:
1. Analyze documents (PDFs, Excel files, Word documents)
2. Extract key information and data
3. Compare and synthesize information across multiple documents
4. Provide structured analysis and summaries

You have access to tools for:
- Reading and extracting text from PDFs
- Reading and creating Excel spreadsheets
- Reading and creating Word documents

Approach:
1. First, examine the structure of each document
2. Extract the most relevant information
3. Identify key data points and patterns
4. Provide a comprehensive summary and analysis\
"""

document_processor = Agent(
    _model,
    output_type=DocumentProcessingResult,
    deps_type=DocumentDeps,
    system_prompt=SYSTEM_PROMPT,
    retries=1,
    model_settings={"temperature": 0.2},
)


@document_processor.instructions
def build_processing_context(ctx: RunContext[DocumentDeps]) -> str:
    """Build the dynamic prompt with file details."""
    deps = ctx.deps
    lines = [
        "FILES TO PROCESS:",
        *[f"  - {fp}" for fp in deps.file_paths],
    ]
    if deps.analysis_prompt:
        lines.append(f"\nSPECIFIC ANALYSIS REQUEST:\n{deps.analysis_prompt}")
    lines.append("\nAnalyze these documents and extract all relevant information.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Agent tools (added via skill manager)
# ---------------------------------------------------------------------------

# Initialize and setup skills for this agent
initialize_skills()
setup_agent_skills(document_processor, "document_processor")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def process_documents(
    file_paths: list[str],
    analysis_prompt: str = "",
) -> DocumentProcessingResult:
    """
    Process documents using the document processor agent.

    Parameters
    ----------
    file_paths : list[str]
        List of paths to documents to process
    analysis_prompt : str
        Optional specific analysis request

    Returns
    -------
    DocumentProcessingResult
        Structured result with extracted data and analysis
    """
    logger.info(f"🔍 Starting document processing for {len(file_paths)} files")
    logger.info(f"🔍 Current model: {get_model()}")

    deps = DocumentDeps(
        file_paths=file_paths,
        analysis_prompt=analysis_prompt,
    )

    result = await run_with_settings(
        "document_processor",
        document_processor,
        "Process the provided documents. Extract key information, analyze content, and provide structured insights.",
        deps=deps,
    )

    output = result.output
    logger.info(
        f"🔍 Document processor returned: "
        f"documents_processed={output.documents_processed}, "
        f"extractions={len(output.extractions)}"
    )

    return output
