"""
Predefined evaluation scenarios for benchmarking the competitive analysis agent.

Each scenario defines: query, expected competitors, required sections, score thresholds.
"""

SCENARIOS = [
    {
        "id": "saas_pm_tools",
        "name": "SaaS Project Management Tools",
        "query": "Compare project management tools: Notion, Monday.com, and Asana",
        "competitors": ["Notion", "Monday.com", "Asana"],
        "required_sections": [
            "Executive Summary", "Feature Comparison", "Pricing Analysis",
            "SWOT Analysis", "Sources",
        ],
        "required_terms": ["pricing", "features", "collaboration", "integration"],
        "thresholds": {
            "section_completeness": 0.7,
            "source_coverage": 0.3,
            "schema_compliance": 0.5,
            "overall_score": 0.5,
        },
    },
    {
        "id": "llm_providers",
        "name": "LLM API Providers",
        "query": "Compare LLM API providers: OpenAI, Anthropic, and Google DeepMind",
        "competitors": ["OpenAI", "Anthropic", "Google DeepMind"],
        "required_sections": [
            "Executive Summary", "Feature Comparison", "Pricing Analysis",
            "SWOT Analysis", "Sources",
        ],
        "required_terms": ["API", "pricing", "model", "context window", "safety"],
        "thresholds": {
            "section_completeness": 0.7,
            "overall_score": 0.5,
        },
    },
    {
        "id": "note_taking_apps",
        "name": "Note-Taking Applications",
        "query": "Compare note-taking apps: Obsidian, Logseq, and Roam Research",
        "competitors": ["Obsidian", "Logseq", "Roam Research"],
        "required_sections": [
            "Executive Summary", "Feature Comparison", "Pricing Analysis",
            "SWOT Analysis", "Sources",
        ],
        "required_terms": ["markdown", "graph", "plugin", "sync"],
        "thresholds": {
            "section_completeness": 0.6,
            "overall_score": 0.45,
        },
    },
]
