"""
Skill type definitions (inspired by deerflow).

A skill is a reusable analysis capability that can be loaded dynamically.
Skills are defined by SKILL.md files and can be extended by users.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import List, Optional


SKILL_MD_FILE = "SKILL.md"


class SkillCategory(StrEnum):
    BUILTIN = "builtin"     # Built-in analysis skills
    CUSTOM = "custom"       # User-defined skills


@dataclass
class Skill:
    """A reusable analysis skill."""
    name: str
    description: str
    category: SkillCategory
    skill_dir: Path
    allowed_tools: List[str] = field(default_factory=list)
    enabled: bool = True
    prompt_template: str = ""

    def __repr__(self) -> str:
        return f"Skill(name={self.name!r}, category={self.category!r})"
