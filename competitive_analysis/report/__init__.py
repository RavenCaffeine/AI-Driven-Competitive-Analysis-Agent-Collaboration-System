"""Report generation module — HTML template engine and screenshot utilities."""

from .html_template import render_html_report
from .renderer import ReportRenderer

__all__ = ["render_html_report", "ReportRenderer"]
