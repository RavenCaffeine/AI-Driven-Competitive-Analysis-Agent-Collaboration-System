"""
HTML Report Template Engine — Dark Business Theme.

Renders competitive analysis data into a polished, self-contained HTML report
with embedded CSS. Supports:
- Dark theme with card-based layout (Notion/Linear style)
- SWOT quadrant visualization
- Feature comparison matrix
- Pricing comparison cards
- Source citations with links
- Responsive design for print and screen
- Full UTF-8 support
"""

from __future__ import annotations

import html
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional


# ─── CSS Theme ────────────────────────────────────────────────────────

DARK_THEME_CSS = """
:root {
    --bg-primary: #0f1117;
    --bg-secondary: #1a1d2e;
    --bg-card: #1e2235;
    --bg-card-hover: #252a40;
    --border: #2d3348;
    --text-primary: #e6e8f0;
    --text-secondary: #9ca3b8;
    --text-muted: #6b7280;
    --accent-blue: #3b82f6;
    --accent-purple: #8b5cf6;
    --accent-green: #10b981;
    --accent-orange: #f59e0b;
    --accent-red: #ef4444;
    --accent-cyan: #06b6d4;
    --gradient-start: #3b82f6;
    --gradient-end: #8b5cf6;
    --swot-s: #10b981;
    --swot-w: #ef4444;
    --swot-o: #3b82f6;
    --swot-t: #f59e0b;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.7;
    font-size: 15px;
}

.report-container {
    max-width: 1100px;
    margin: 0 auto;
    padding: 0 24px 60px;
}

/* ─── Header ─── */
.report-header {
    background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
    padding: 48px 40px;
    border-radius: 0 0 20px 20px;
    margin-bottom: 40px;
    position: relative;
    overflow: hidden;
}
.report-header::before {
    content: '';
    position: absolute;
    top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: radial-gradient(circle, rgba(255,255,255,0.05) 0%, transparent 60%);
}
.report-header h1 {
    font-size: 28px;
    font-weight: 700;
    color: #fff;
    position: relative;
    margin-bottom: 12px;
}
.report-header .subtitle {
    font-size: 15px;
    color: rgba(255,255,255,0.8);
    position: relative;
}
.report-meta {
    display: flex;
    gap: 20px;
    margin-top: 20px;
    position: relative;
}
.meta-tag {
    background: rgba(255,255,255,0.15);
    backdrop-filter: blur(8px);
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 12px;
    color: rgba(255,255,255,0.9);
    font-weight: 500;
}

/* ─── Section ─── */
.section {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 32px;
    margin-bottom: 24px;
    transition: border-color 0.2s;
}
.section:hover { border-color: var(--accent-blue); }
.section-title {
    font-size: 20px;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.section-title .icon {
    width: 32px; height: 32px;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
}
.section p, .section li {
    color: var(--text-secondary);
    margin-bottom: 10px;
}
.section ul, .section ol {
    padding-left: 20px;
}

/* ─── Cards Grid ─── */
.cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px;
    margin: 16px 0;
}
.card {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    transition: transform 0.15s, border-color 0.2s;
}
.card:hover {
    transform: translateY(-2px);
    border-color: var(--accent-blue);
}
.card-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 8px;
}
.card-subtitle {
    font-size: 12px;
    color: var(--text-muted);
    margin-bottom: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.card-body { color: var(--text-secondary); font-size: 14px; }

/* ─── Competitor Profile Cards ─── */
.competitor-card {
    border-left: 4px solid var(--accent-blue);
}
.competitor-card:nth-child(2) { border-left-color: var(--accent-purple); }
.competitor-card:nth-child(3) { border-left-color: var(--accent-green); }
.competitor-card:nth-child(4) { border-left-color: var(--accent-orange); }

/* ─── SWOT Quadrant ─── */
.swot-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin: 16px 0;
}
.swot-cell {
    border-radius: 12px;
    padding: 20px;
    min-height: 120px;
}
.swot-cell h4 {
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.swot-cell ul { list-style: none; padding: 0; }
.swot-cell li {
    font-size: 13px;
    padding: 3px 0;
    color: rgba(255,255,255,0.85);
}
.swot-cell li::before { content: '• '; opacity: 0.5; }
.swot-s { background: rgba(16,185,129,0.15); border: 1px solid rgba(16,185,129,0.3); }
.swot-s h4 { color: var(--swot-s); }
.swot-w { background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.3); }
.swot-w h4 { color: var(--swot-w); }
.swot-o { background: rgba(59,130,246,0.15); border: 1px solid rgba(59,130,246,0.3); }
.swot-o h4 { color: var(--swot-o); }
.swot-t { background: rgba(245,158,11,0.15); border: 1px solid rgba(245,158,11,0.3); }
.swot-t h4 { color: var(--swot-t); }

/* ─── Comparison Table ─── */
.comparison-table {
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0;
    font-size: 14px;
}
.comparison-table thead th {
    background: var(--bg-secondary);
    color: var(--text-primary);
    padding: 14px 16px;
    text-align: left;
    font-weight: 600;
    border-bottom: 2px solid var(--accent-blue);
    position: sticky;
    top: 0;
}
.comparison-table tbody td {
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    color: var(--text-secondary);
    vertical-align: top;
}
.comparison-table tbody tr:hover td {
    background: var(--bg-card-hover);
}
.check { color: var(--accent-green); font-weight: 700; }
.cross { color: var(--accent-red); font-weight: 700; }
.partial { color: var(--accent-orange); font-weight: 700; }

/* ─── Pricing Cards ─── */
.pricing-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px;
    margin: 16px 0;
}
.pricing-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    text-align: center;
}
.pricing-card .price {
    font-size: 28px;
    font-weight: 700;
    color: var(--accent-blue);
    margin: 12px 0 4px;
}
.pricing-card .period {
    font-size: 12px;
    color: var(--text-muted);
}
.pricing-card .plan-name {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
}
.pricing-card .features-list {
    list-style: none;
    padding: 0;
    margin-top: 16px;
    text-align: left;
}
.pricing-card .features-list li {
    font-size: 13px;
    padding: 4px 0;
    color: var(--text-secondary);
}
.pricing-card .features-list li::before {
    content: '✓ ';
    color: var(--accent-green);
}

/* ─── Citations ─── */
.citation {
    background: rgba(59,130,246,0.1);
    border: 1px solid rgba(59,130,246,0.2);
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 12px;
    color: var(--accent-blue);
    text-decoration: none;
    white-space: nowrap;
}
.citation:hover { background: rgba(59,130,246,0.2); }

.sources-list {
    list-style: none;
    padding: 0;
}
.sources-list li {
    padding: 10px 16px;
    border-bottom: 1px solid var(--border);
    font-size: 13px;
}
.sources-list li a {
    color: var(--accent-blue);
    text-decoration: none;
}
.sources-list li a:hover { text-decoration: underline; }
.source-idx {
    background: var(--accent-blue);
    color: #fff;
    border-radius: 4px;
    padding: 1px 6px;
    font-size: 11px;
    font-weight: 600;
    margin-right: 8px;
}

/* ─── Insights Callout ─── */
.insight-box {
    background: linear-gradient(135deg, rgba(59,130,246,0.1), rgba(139,92,246,0.1));
    border: 1px solid rgba(59,130,246,0.25);
    border-radius: 12px;
    padding: 20px 24px;
    margin: 12px 0;
}
.insight-box .insight-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--accent-blue);
    margin-bottom: 8px;
}

/* ─── Footer ─── */
.report-footer {
    text-align: center;
    padding: 32px 0;
    color: var(--text-muted);
    font-size: 12px;
    border-top: 1px solid var(--border);
    margin-top: 40px;
}

/* ─── Responsive ─── */
@media (max-width: 768px) {
    .report-header { padding: 32px 24px; }
    .report-header h1 { font-size: 22px; }
    .section { padding: 20px; }
    .swot-grid { grid-template-columns: 1fr; }
    .report-meta { flex-wrap: wrap; gap: 8px; }
}

/* ─── Print ─── */
@media print {
    body { background: #fff; color: #111; }
    .section { border: 1px solid #ddd; break-inside: avoid; }
    .report-header { background: #2563eb !important; }
    .comparison-table thead th { background: #f3f4f6; color: #111; }
}
"""


# ─── Template Helpers ─────────────────────────────────────────────────

def _esc(text: str) -> str:
    """HTML-escape text."""
    return html.escape(str(text)) if text else ""


def _md_to_html(text: str) -> str:
    """Minimal Markdown-to-HTML for LLM output (no external deps)."""
    if not text:
        return ""
    lines = text.split("\n")
    result = []
    in_list = False
    in_table = False

    for line in lines:
        stripped = line.strip()

        # Skip markdown headers (we handle sections separately)
        if stripped.startswith("## ") or stripped.startswith("# "):
            continue

        # Bold
        stripped = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped)
        # Italic
        stripped = re.sub(r'\*(.+?)\*', r'<em>\1</em>', stripped)
        # Inline code
        stripped = re.sub(r'`(.+?)`', r'<code>\1</code>', stripped)
        # Links
        stripped = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', stripped)

        # Source citations → styled spans
        stripped = re.sub(
            r'\[Source:\s*(https?://[^\]]+)\]',
            r'<a class="citation" href="\1" target="_blank">Source ↗</a>',
            stripped
        )
        stripped = re.sub(
            r'\[E(\d+)\]',
            r'<span class="citation">E\1</span>',
            stripped
        )

        # Table rows
        if "|" in stripped and not stripped.startswith("|-"):
            if stripped.startswith("|"):
                cells = [c.strip() for c in stripped.split("|")[1:-1]]
            else:
                cells = [c.strip() for c in stripped.split("|")]
            if cells:
                if not in_table:
                    result.append('<table class="comparison-table"><thead><tr>')
                    for c in cells:
                        # Replace check/cross marks
                        c = c.replace("✓", '<span class="check">✓</span>')
                        c = c.replace("✗", '<span class="cross">✗</span>')
                        c = c.replace("△", '<span class="partial">△</span>')
                        result.append(f"<th>{c}</th>")
                    result.append("</tr></thead><tbody>")
                    in_table = True
                else:
                    result.append("<tr>")
                    for c in cells:
                        c = c.replace("✓", '<span class="check">✓</span>')
                        c = c.replace("✗", '<span class="cross">✗</span>')
                        c = c.replace("△", '<span class="partial">△</span>')
                        result.append(f"<td>{c}</td>")
                    result.append("</tr>")
                continue
        elif in_table and (not stripped or not "|" in stripped):
            result.append("</tbody></table>")
            in_table = False

        # Skip table separator lines
        if re.match(r'^[\|\-\s:]+$', stripped):
            continue

        # Unordered list
        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                result.append("<ul>")
                in_list = True
            result.append(f"<li>{stripped[2:]}</li>")
            continue
        elif in_list and (not stripped or not (stripped.startswith("- ") or stripped.startswith("* "))):
            result.append("</ul>")
            in_list = False

        # Empty line
        if not stripped:
            continue

        # Regular paragraph
        result.append(f"<p>{stripped}</p>")

    if in_list:
        result.append("</ul>")
    if in_table:
        result.append("</tbody></table>")

    return "\n".join(result)


def _parse_sections(markdown_report: str) -> List[Dict[str, str]]:
    """Parse a markdown report into sections by ## headers."""
    sections = []
    current_title = ""
    current_body_lines = []

    for line in markdown_report.split("\n"):
        if line.strip().startswith("## "):
            if current_title or current_body_lines:
                sections.append({
                    "title": current_title,
                    "body": "\n".join(current_body_lines),
                })
            current_title = line.strip().lstrip("# ").strip()
            current_body_lines = []
        elif line.strip().startswith("# ") and not current_title:
            # Top-level title (skip, used in header)
            continue
        else:
            current_body_lines.append(line)

    if current_title or current_body_lines:
        sections.append({
            "title": current_title,
            "body": "\n".join(current_body_lines),
        })

    return sections


# ─── Section Icons ────────────────────────────────────────────────────

SECTION_ICONS = {
    "executive summary": ("📊", "var(--accent-blue)"),
    "methodology":       ("🔬", "var(--accent-purple)"),
    "competitor":        ("🏢", "var(--accent-green)"),
    "feature":           ("⚡", "var(--accent-cyan)"),
    "pricing":           ("💰", "var(--accent-orange)"),
    "swot":              ("🎯", "var(--accent-red)"),
    "user":              ("👥", "var(--accent-purple)"),
    "sentiment":         ("💬", "var(--accent-purple)"),
    "insight":           ("💡", "var(--accent-blue)"),
    "recommendation":    ("🚀", "var(--accent-green)"),
    "source":            ("📎", "var(--text-muted)"),
    "key":               ("🔑", "var(--accent-orange)"),
}


def _get_icon(title: str) -> tuple:
    """Get icon and color for a section title."""
    lower = title.lower()
    for keyword, (icon, color) in SECTION_ICONS.items():
        if keyword in lower:
            return icon, color
    return "📄", "var(--accent-blue)"


def _render_swot_section(body: str) -> str:
    """Detect SWOT content and render as quadrant grid."""
    # Try to parse SWOT items from the body text
    categories = {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []}
    current_cat = None

    for line in body.split("\n"):
        lower = line.strip().lower()
        if "strength" in lower:
            current_cat = "strengths"
        elif "weakness" in lower or "weaknesse" in lower:
            current_cat = "weaknesses"
        elif "opportunit" in lower:
            current_cat = "opportunities"
        elif "threat" in lower:
            current_cat = "threats"
        elif current_cat and (line.strip().startswith("- ") or line.strip().startswith("* ")):
            item = line.strip().lstrip("-* ").strip()
            if item:
                categories[current_cat].append(item)

    # If we found structured SWOT data, render as grid
    has_data = any(v for v in categories.values())
    if has_data:
        html_parts = ['<div class="swot-grid">']
        swot_map = [
            ("strengths", "Strengths", "swot-s", "💪"),
            ("weaknesses", "Weaknesses", "swot-w", "⚠️"),
            ("opportunities", "Opportunities", "swot-o", "🌟"),
            ("threats", "Threats", "swot-t", "🔥"),
        ]
        for key, label, css_class, emoji in swot_map:
            items = categories[key]
            html_parts.append(f'<div class="swot-cell {css_class}">')
            html_parts.append(f'<h4>{emoji} {label}</h4><ul>')
            for item in items[:6]:
                html_parts.append(f"<li>{_esc(item)}</li>")
            if not items:
                html_parts.append("<li><em>No data</em></li>")
            html_parts.append("</ul></div>")
        html_parts.append("</div>")
        return "\n".join(html_parts)

    # Fallback: render as normal HTML
    return _md_to_html(body)


# ─── Main Render Function ────────────────────────────────────────────

def render_html_report(
    markdown_report: str,
    query: str = "",
    competitors: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Render a markdown competitive analysis report as a polished HTML page.

    Args:
        markdown_report: The markdown report text (from Writer Agent)
        query: Original analysis query
        competitors: List of competitor names
        metadata: Optional dict with provider, model, run_id, etc.

    Returns:
        Complete self-contained HTML string
    """
    competitors = competitors or []
    metadata = metadata or {}

    # Parse into sections
    sections = _parse_sections(markdown_report)

    # Extract top-level title if present
    title_match = re.search(r'^#\s+(.+)', markdown_report, re.MULTILINE)
    report_title = title_match.group(1).strip() if title_match else query or "Competitive Analysis Report"

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    provider = metadata.get("provider", "")
    model = metadata.get("model", "")
    run_id = metadata.get("run_id", "")

    # Build sections HTML
    sections_html = []
    for sec in sections:
        title = sec["title"]
        body = sec["body"]
        icon, color = _get_icon(title)

        # Special rendering for SWOT sections
        if "swot" in title.lower():
            body_html = _render_swot_section(body)
        else:
            body_html = _md_to_html(body)

        sections_html.append(f"""
        <div class="section">
            <div class="section-title">
                <span class="icon" style="background:{color}20;color:{color}">{icon}</span>
                {_esc(title)}
            </div>
            <div class="section-body">
                {body_html}
            </div>
        </div>""")

    sections_block = "\n".join(sections_html)

    # Meta tags
    meta_tags = []
    if competitors:
        meta_tags.append(f'<span class="meta-tag">🏢 {" vs ".join(competitors)}</span>')
    if provider:
        meta_tags.append(f'<span class="meta-tag">🤖 {_esc(provider)} / {_esc(model)}</span>')
    meta_tags.append(f'<span class="meta-tag">📅 {now}</span>')
    if run_id:
        meta_tags.append(f'<span class="meta-tag">🔍 {_esc(run_id[:12])}</span>')
    meta_html = "\n            ".join(meta_tags)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{_esc(report_title)}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
{DARK_THEME_CSS}
    </style>
</head>
<body>
    <div class="report-header">
        <h1>{_esc(report_title)}</h1>
        <div class="subtitle">AI-Driven Competitive Analysis Report</div>
        <div class="report-meta">
            {meta_html}
        </div>
    </div>

    <div class="report-container">
        {sections_block}
    </div>

    <div class="report-container">
        <div class="report-footer">
            Generated by Competitive Analysis Multi-Agent System &middot; {now}
            {f'&middot; {_esc(provider)}/{_esc(model)}' if provider else ''}
        </div>
    </div>
</body>
</html>"""
