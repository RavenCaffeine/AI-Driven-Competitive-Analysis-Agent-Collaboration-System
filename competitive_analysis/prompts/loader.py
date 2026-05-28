"""
Prompt template loader - loads .md prompt files with variable substitution.
"""

from pathlib import Path
from typing import Any


PROMPTS_DIR = Path(__file__).parent


class PromptLoader:
    """Load and render prompt templates from .md files."""

    def __init__(self, prompts_dir: Path | None = None):
        self.prompts_dir = prompts_dir or PROMPTS_DIR

    def load(self, template_name: str, **kwargs: Any) -> str:
        """Load a prompt template and substitute variables."""
        path = self.prompts_dir / f"{template_name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Prompt template not found: {path}")
        template = path.read_text(encoding="utf-8")
        for key, value in kwargs.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
        return template
