"""
Skill loader - discovers and loads analysis skills from directories.

Supports both built-in and user-custom skills following deerflow's pattern.
"""

import logging
from pathlib import Path
from typing import Dict, List

from .types import Skill, SkillCategory, SKILL_MD_FILE

logger = logging.getLogger("competitive_analysis.skills")

BUILTIN_SKILLS_DIR = Path(__file__).parent / "builtin"


def discover_skills(
    custom_dir: Path | None = None,
    builtin_dir: Path | None = None,
) -> List[Skill]:
    """Discover all available skills from built-in and custom directories."""
    skills = []
    builtin = builtin_dir or BUILTIN_SKILLS_DIR

    # Load built-in skills
    if builtin.exists():
        for skill_dir in builtin.iterdir():
            if skill_dir.is_dir() and (skill_dir / SKILL_MD_FILE).exists():
                skill = _load_skill(skill_dir, SkillCategory.BUILTIN)
                if skill:
                    skills.append(skill)

    # Load custom skills
    if custom_dir and custom_dir.exists():
        for skill_dir in custom_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / SKILL_MD_FILE).exists():
                skill = _load_skill(skill_dir, SkillCategory.CUSTOM)
                if skill:
                    skills.append(skill)

    return skills


def _load_skill(skill_dir: Path, category: SkillCategory) -> Skill | None:
    """Load a single skill from its directory."""
    try:
        skill_file = skill_dir / SKILL_MD_FILE
        content = skill_file.read_text(encoding="utf-8")

        # Parse SKILL.md frontmatter
        name = skill_dir.name
        description = ""
        lines = content.split("\n")
        for line in lines:
            if line.startswith("# "):
                name = line.lstrip("# ").strip()
            elif line.startswith("description:"):
                description = line.split(":", 1)[1].strip()
                break

        if not description and len(lines) > 1:
            description = lines[1].strip() if lines[1].strip() else lines[0].strip()

        return Skill(
            name=name,
            description=description,
            category=category,
            skill_dir=skill_dir,
            prompt_template=content,
        )
    except Exception as e:
        logger.warning("Failed to load skill from %s: %s", skill_dir, e)
        return None
