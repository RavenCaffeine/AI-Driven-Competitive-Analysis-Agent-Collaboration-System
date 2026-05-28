"""
Structured logging with per-agent context.

Every log line includes agent name and trace run_id for observability.
"""

import logging
import sys
from typing import Optional


def setup_logger(
    name: str = "competitive_analysis",
    level: str = "INFO",
    log_file: Optional[str] = None,
) -> logging.Logger:
    """Create a configured logger instance."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        fmt = logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(fmt)
        logger.addHandler(console)

        if log_file:
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setFormatter(fmt)
            logger.addHandler(fh)

    return logger


def get_agent_logger(agent_name: str) -> logging.Logger:
    """Get a logger scoped to a specific agent."""
    return logging.getLogger(f"competitive_analysis.{agent_name}")
