"""
Skill Registry - Configuration-driven skill management for agents.

Manages available skills, registers them with agents, and handles skill execution.
Skills are defined in config and can be enabled/disabled per agent or globally.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class SkillType(str, Enum):
    """Available skill categories."""
    DOCUMENT_HANDLING = "document_handling"
    PDF_PROCESSING = "pdf_processing"
    OFFICE_DOCUMENTS = "office_documents"
    WEB_SCRAPING = "web_scraping"
    CUSTOM = "custom"


@dataclass
class SkillConfig:
    """Configuration for a single skill."""
    name: str
    skill_type: SkillType
    enabled: bool = True
    description: str = ""
    required_packages: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentSkillsConfig:
    """Skills configuration for an agent."""
    agent_name: str
    enabled_skills: list[str]
    default_skills: list[str] = field(default_factory=list)


class SkillRegistry:
    """Central registry for managing agent skills."""

    def __init__(self):
        self._skills: dict[str, SkillConfig] = {}
        self._skill_handlers: dict[str, Callable] = {}
        self._agent_skills: dict[str, list[str]] = {}

    def register_skill(
        self,
        config: SkillConfig,
        handler: Optional[Callable] = None,
    ) -> None:
        """Register a new skill with optional handler function."""
        if config.name in self._skills:
            logger.warning(f"Skill '{config.name}' already registered, overwriting")

        self._skills[config.name] = config
        if handler:
            self._skill_handlers[config.name] = handler

        logger.info(f"Registered skill: {config.name} ({config.skill_type})")

    def register_agent_skills(
        self,
        agent_name: str,
        skill_names: list[str],
    ) -> None:
        """Register skills for a specific agent."""
        self._agent_skills[agent_name] = skill_names
        logger.info(f"Registered {len(skill_names)} skills for agent '{agent_name}'")

    def get_enabled_skills(self, agent_name: str) -> dict[str, SkillConfig]:
        """Get all enabled skills for an agent."""
        skill_names = self._agent_skills.get(agent_name, [])
        return {
            name: config
            for name, config in self._skills.items()
            if name in skill_names and config.enabled
        }

    def get_skill_handler(self, skill_name: str) -> Optional[Callable]:
        """Get the handler function for a skill."""
        return self._skill_handlers.get(skill_name)

    def is_skill_enabled(self, skill_name: str) -> bool:
        """Check if a skill is enabled."""
        skill = self._skills.get(skill_name)
        return skill.enabled if skill else False

    def list_skills(self) -> dict[str, SkillConfig]:
        """List all registered skills."""
        return self._skills.copy()

    def list_agent_skills(self, agent_name: str) -> list[str]:
        """List skill names for an agent."""
        return self._agent_skills.get(agent_name, [])


# Global registry instance
_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    """Get or create the global skill registry."""
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry


def configure_default_skills() -> None:
    """Configure default built-in skills."""
    registry = get_skill_registry()

    # Document handling skills
    registry.register_skill(
        SkillConfig(
            name="pdf_extract",
            skill_type=SkillType.PDF_PROCESSING,
            enabled=True,
            description="Extract text and tables from PDF documents",
            required_packages=["pdfplumber", "pdf2image"],
        ),
        handler=None,  # Will implement later
    )

    registry.register_skill(
        SkillConfig(
            name="docx_handler",
            skill_type=SkillType.OFFICE_DOCUMENTS,
            enabled=True,
            description="Create, edit, and extract from Word documents",
            required_packages=["python-docx"],
        ),
    )

    registry.register_skill(
        SkillConfig(
            name="xlsx_handler",
            skill_type=SkillType.OFFICE_DOCUMENTS,
            enabled=True,
            description="Create and analyze Excel spreadsheets",
            required_packages=["openpyxl", "pandas"],
        ),
    )

    registry.register_skill(
        SkillConfig(
            name="pptx_handler",
            skill_type=SkillType.OFFICE_DOCUMENTS,
            enabled=True,
            description="Create and edit PowerPoint presentations",
            required_packages=["python-pptx"],
        ),
    )

    registry.register_skill(
        SkillConfig(
            name="web_scrape",
            skill_type=SkillType.WEB_SCRAPING,
            enabled=True,
            description="Scrape and analyze web content",
            required_packages=["beautifulsoup4", "requests"],
        ),
    )

    logger.info("Configured default built-in skills")


def attach_skills_to_agent(agent: Any, agent_name: str) -> None:
    """
    Dynamically attach registered skills to a PydanticAI agent.

    This should be called after agent creation to add skill-based tools.
    """
    registry = get_skill_registry()
    skills = registry.get_enabled_skills(agent_name)

    if not skills:
        logger.info(f"No skills enabled for agent '{agent_name}'")
        return

    logger.info(f"Attaching {len(skills)} skills to agent '{agent_name}'")

    for skill_name, skill_config in skills.items():
        handler = registry.get_skill_handler(skill_name)
        if handler and hasattr(agent, "tool"):
            # Attach as PydanticAI tool
            try:
                agent.tool(handler)
                logger.info(f"Attached skill '{skill_name}' to agent '{agent_name}'")
            except Exception as e:
                logger.error(f"Failed to attach skill '{skill_name}': {e}")
        else:
            logger.debug(f"No handler for skill '{skill_name}' (may be built-in)")


# Initialize on import
configure_default_skills()
