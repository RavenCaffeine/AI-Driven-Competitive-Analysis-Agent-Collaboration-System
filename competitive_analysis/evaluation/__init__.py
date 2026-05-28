"""Evaluation framework for competitive analysis agent."""

from .metrics import evaluate_run
from .scenarios import SCENARIOS

__all__ = ["evaluate_run", "SCENARIOS"]
