"""
Skill Manager - Initialize and manage all agent skills.

This module loads all skill implementations and registers them with the registry.
It provides a simple interface for attaching skills to agents.
"""
import logging
from typing import Any, Optional

from app.services.skill_registry import (
    get_skill_registry,
    SkillConfig,
    SkillType,
    configure_default_skills,
)

logger = logging.getLogger(__name__)

# Skill implementation modules
from app.services.skills import pdf_skill, xlsx_skill, docx_skill


def register_skill_implementations() -> None:
    """Register all skill implementations with the registry."""
    registry = get_skill_registry()

    # PDF Skills
    registry.register_skill(
        SkillConfig(
            name="pdf_extract",
            skill_type=SkillType.PDF_PROCESSING,
            enabled=True,
            description="Extract text, tables, and metadata from PDF documents",
            required_packages=["pdfplumber", "PyPDF2"],
        ),
    )

    # Excel Skills
    registry.register_skill(
        SkillConfig(
            name="xlsx_handler",
            skill_type=SkillType.OFFICE_DOCUMENTS,
            enabled=True,
            description="Create and analyze Excel spreadsheets",
            required_packages=["openpyxl", "pandas"],
        ),
    )

    # Word Skills
    registry.register_skill(
        SkillConfig(
            name="docx_handler",
            skill_type=SkillType.OFFICE_DOCUMENTS,
            enabled=True,
            description="Create and analyze Word documents",
            required_packages=["python-docx"],
        ),
    )

    logger.info("Registered all skill implementations")


def setup_agent_skills(agent: Any, agent_name: str) -> None:
    """
    Setup skills for a PydanticAI agent.

    This attaches skill-based tools to the agent, making them available
    during agent execution.

    Args:
        agent: PydanticAI agent instance
        agent_name: Name of the agent (used to look up configured skills)
    """
    registry = get_skill_registry()
    enabled_skills = registry.get_enabled_skills(agent_name)

    if not enabled_skills:
        logger.info(f"No skills enabled for agent '{agent_name}'")
        return

    logger.info(f"Setting up {len(enabled_skills)} skills for agent '{agent_name}'")

    # Attach skill tools to agent
    skill_tools_attached = 0

    # PDF Skills
    if "pdf_extract" in enabled_skills:
        try:
            # Add individual PDF tools
            @agent.tool
            async def extract_pdf_text(ctx, file_path: str, page_range: Optional[tuple[int, int]] = None) -> dict:
                """Extract text content from a PDF document."""
                from app.services.skills.pdf_skill import extract_pdf_text
                return extract_pdf_text(file_path, page_range)

            @agent.tool
            async def extract_pdf_tables(ctx, file_path: str) -> dict:
                """Extract tables from a PDF document."""
                from app.services.skills.pdf_skill import extract_pdf_tables
                return extract_pdf_tables(file_path)

            @agent.tool
            async def get_pdf_metadata(ctx, file_path: str) -> dict:
                """Get metadata from a PDF file."""
                from app.services.skills.pdf_skill import get_pdf_metadata
                return get_pdf_metadata(file_path)

            skill_tools_attached += 3
            logger.info("Attached PDF extraction tools")
        except Exception as e:
            logger.error(f"Failed to attach PDF tools: {e}")

    # Excel Skills
    if "xlsx_handler" in enabled_skills:
        try:
            @agent.tool
            async def read_excel_sheet(ctx, file_path: str, sheet_name: str = "Sheet1") -> dict:
                """Read data from an Excel spreadsheet."""
                from app.services.skills.xlsx_skill import read_excel_sheet
                return read_excel_sheet(file_path, sheet_name)

            @agent.tool
            async def list_excel_sheets(ctx, file_path: str) -> dict:
                """List all sheets in an Excel file."""
                from app.services.skills.xlsx_skill import list_excel_sheets
                return list_excel_sheets(file_path)

            @agent.tool
            async def create_excel_file(ctx, file_path: str, sheets: dict, headers: Optional[dict] = None) -> dict:
                """Create a new Excel file with specified data."""
                from app.services.skills.xlsx_skill import create_excel_file
                return create_excel_file(file_path, sheets, headers)

            skill_tools_attached += 3
            logger.info("Attached Excel tools")
        except Exception as e:
            logger.error(f"Failed to attach Excel tools: {e}")

    # Word Skills
    if "docx_handler" in enabled_skills:
        try:
            @agent.tool
            async def read_docx_text(ctx, file_path: str) -> dict:
                """Extract text from a Word document."""
                from app.services.skills.docx_skill import read_docx_text
                return read_docx_text(file_path)

            @agent.tool
            async def create_docx_file(ctx, file_path: str, content: dict) -> dict:
                """Create a new Word document."""
                from app.services.skills.docx_skill import create_docx_file
                return create_docx_file(file_path, content)

            @agent.tool
            async def extract_docx_metadata(ctx, file_path: str) -> dict:
                """Get metadata from a Word document."""
                from app.services.skills.docx_skill import extract_docx_metadata
                return extract_docx_metadata(file_path)

            skill_tools_attached += 3
            logger.info("Attached Word tools")
        except Exception as e:
            logger.error(f"Failed to attach Word tools: {e}")

    logger.info(f"Successfully attached {skill_tools_attached} skill tools to agent '{agent_name}'")


def initialize_skills() -> None:
    """Initialize the entire skill system."""
    logger.info("Initializing skill system...")
    configure_default_skills()
    register_skill_implementations()
    logger.info("Skill system initialized")
