"""
Report Renderer — Orchestrates HTML generation and optional screenshot.

Usage:
    renderer = ReportRenderer(config)
    html_path = renderer.render(state)            # Always works
    png_path = renderer.screenshot(html_path)      # Requires playwright or e2b
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .html_template import render_html_report

logger = logging.getLogger("competitive_analysis.report")


class ReportRenderer:
    """Orchestrates report rendering: Markdown -> HTML -> optional PNG/PDF."""

    def __init__(self, output_dir: str = "./outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render(
        self,
        state: Dict[str, Any],
        filename: str = "report.html",
    ) -> Path:
        """
        Render the report from workflow state to a polished HTML file.

        Args:
            state: Final workflow state containing report_draft, query, etc.
            filename: Output filename

        Returns:
            Path to the generated HTML file
        """
        markdown_report = state.get("report_draft", state.get("final_report", ""))
        query = state.get("query", "")
        competitors = state.get("competitors", [])
        trace = state.get("trace", {})

        metadata = {
            "provider": trace.get("provider", ""),
            "model": trace.get("model", ""),
            "run_id": trace.get("run_id", ""),
            "qa_iterations": state.get("qa_iteration", 0),
        }

        html_content = render_html_report(
            markdown_report=markdown_report,
            query=query,
            competitors=competitors,
            metadata=metadata,
        )

        out_path = self.output_dir / filename
        out_path.write_text(html_content, encoding="utf-8")
        logger.info("HTML report saved to: %s", out_path)
        return out_path

    def render_from_markdown(
        self,
        markdown_text: str,
        query: str = "",
        competitors: list | None = None,
        filename: str = "report.html",
    ) -> Path:
        """Render directly from a markdown string (no state needed)."""
        html_content = render_html_report(
            markdown_report=markdown_text,
            query=query,
            competitors=competitors,
        )
        out_path = self.output_dir / filename
        out_path.write_text(html_content, encoding="utf-8")
        return out_path

    def screenshot(
        self,
        html_path: Path,
        output_format: str = "png",
        width: int = 1200,
        height: int = 800,
    ) -> Optional[Path]:
        """
        Take a screenshot of the HTML report using Playwright (local) or E2B (remote).

        Falls back gracefully if neither is available.

        Args:
            html_path: Path to the HTML file
            output_format: "png" or "pdf"
            width: Viewport width
            height: Viewport height (ignored for PDF, uses full page)

        Returns:
            Path to screenshot file, or None if unavailable
        """
        # Try local Playwright first
        try:
            return self._screenshot_playwright(html_path, output_format, width, height)
        except ImportError:
            logger.info("Playwright not installed, trying E2B...")
        except Exception as e:
            logger.warning("Playwright screenshot failed: %s", e)

        # Try E2B sandbox
        try:
            return self._screenshot_e2b(html_path, output_format, width, height)
        except ImportError:
            logger.info("E2B SDK not installed. Install with: pip install e2b-code-interpreter")
        except Exception as e:
            logger.warning("E2B screenshot failed: %s", e)

        logger.warning(
            "Screenshot unavailable. Install playwright or e2b to enable."
        )
        return None

    def _screenshot_playwright(
        self, html_path: Path, output_format: str, width: int, height: int
    ) -> Path:
        """Local Playwright headless browser screenshot."""
        from playwright.sync_api import sync_playwright

        out_ext = "pdf" if output_format == "pdf" else "png"
        out_path = html_path.with_suffix("." + out_ext)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": width, "height": height})

            file_url = "file://" + str(html_path.resolve())
            page.goto(file_url)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)

            if output_format == "pdf":
                page.pdf(
                    path=str(out_path),
                    format="A4",
                    print_background=True,
                    margin={"top": "20px", "bottom": "20px", "left": "20px", "right": "20px"},
                )
            else:
                page.screenshot(path=str(out_path), full_page=True)

            browser.close()

        logger.info("Screenshot saved to: %s", out_path)
        return out_path

    def _screenshot_e2b(
        self, html_path: Path, output_format: str, width: int, height: int
    ) -> Path:
        """E2B cloud sandbox screenshot — runs Playwright in a remote sandbox."""
        import os
        import base64
        from e2b_code_interpreter import Sandbox

        api_key = os.environ.get("E2B_API_KEY", "")
        if not api_key:
            raise EnvironmentError("E2B_API_KEY not set. Get one at https://e2b.dev")

        html_content = html_path.read_text(encoding="utf-8")
        out_ext = "pdf" if output_format == "pdf" else "png"
        out_path = html_path.with_suffix("." + out_ext)

        # Escape for embedding in Python string
        escaped_html = html_content.replace("\\", "\\\\").replace("'", "\\'")

        # Build the screenshot action line
        if output_format == "pdf":
            action_line = "page.pdf(path='/tmp/output.{ext}', format='A4', print_background=True)".format(ext=out_ext)
        else:
            action_line = "page.screenshot(path='/tmp/output.{ext}', full_page=True)".format(ext=out_ext)

        sandbox_code = (
            "import base64\n"
            "from playwright.sync_api import sync_playwright\n"
            "\n"
            "html = '''" + escaped_html + "'''\n"
            "\n"
            "with open('/tmp/report.html', 'w', encoding='utf-8') as f:\n"
            "    f.write(html)\n"
            "\n"
            "with sync_playwright() as p:\n"
            "    browser = p.chromium.launch(headless=True)\n"
            "    page = browser.new_page(viewport={'width': " + str(width) + ", 'height': " + str(height) + "})\n"
            "    page.goto('file:///tmp/report.html')\n"
            "    page.wait_for_load_state('networkidle')\n"
            "    page.wait_for_timeout(1500)\n"
            "    " + action_line + "\n"
            "    browser.close()\n"
            "\n"
            "with open('/tmp/output." + out_ext + "', 'rb') as f:\n"
            "    print(base64.b64encode(f.read()).decode())\n"
        )

        sandbox = Sandbox(api_key=api_key, template="playwright")
        try:
            result = sandbox.run_code(sandbox_code, timeout=60)
            if result.logs.stdout:
                img_data = base64.b64decode(result.logs.stdout[-1].strip())
                out_path.write_bytes(img_data)
                logger.info("E2B screenshot saved to: %s", out_path)
                return out_path
            else:
                stderr = "\n".join(result.logs.stderr) if result.logs.stderr else "Unknown error"
                raise RuntimeError("E2B sandbox error: " + stderr)
        finally:
            sandbox.kill()
