"""
Analyst Agent (分析师 Agent)

Responsible for:
- Comparative feature analysis across competitors
- SWOT analysis generation
- Pricing strategy comparison
- User sentiment synthesis
- Producing structured analysis conforming to schema

Takes collector output, produces structured analysis with traceability.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from ..llm.base import BaseLLM
from ..prompts.loader import PromptLoader
from ..schemas.competitive import (
    CompetitorProfile, SWOTAnalysis, SWOTItem, FeatureTree,
    PricingModel, UserProfile, ReviewSummary, SourceReference,
)

logger = logging.getLogger("competitive_analysis.analyst")


class AnalystAgent:
    """Competitive analysis agent - synthesizes collected data into structured insights."""

    def __init__(self, llm: BaseLLM):
        self.llm = llm
        self.prompt_loader = PromptLoader()

    def analyze(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive competitive analysis on collected data.

        Reads from state['collected_data'], writes to state['analysis_result'].
        """
        collected = state.get("collected_data", {})
        if not collected:
            logger.warning("No collected data to analyze")
            state["analysis_result"] = {}
            return state

        # Build analysis prompt
        prompt = self.prompt_loader.load(
            "analyst_compare",
            collected_data=json.dumps(collected, ensure_ascii=False, default=str)[:8000],
        )
        response = self.llm.generate(prompt, temperature=0.4)

        try:
            analysis = self._parse_json(response)
        except Exception as e:
            logger.error("Failed to parse analysis: %s", e)
            analysis = {"raw_analysis": response}

        state["analysis_result"] = analysis

        # Build competitor profiles conforming to schema
        profiles = self._build_profiles(collected, analysis)
        state["competitor_profiles"] = profiles

        return state

    def _build_profiles(
        self, collected: Dict, analysis: Dict
    ) -> List[Dict[str, Any]]:
        """Build structured CompetitorProfile objects from collected + analyzed data."""
        profiles = []
        competitors = collected.get("competitors", [])
        swot_data = analysis.get("swot_analyses", {})

        for comp_name in competitors:
            comp_data = collected.get(comp_name, {})
            swot = swot_data.get(comp_name, {})

            profile = CompetitorProfile(
                company_name=comp_name,
                product_name=comp_data.get("product_name", comp_name),
                website=comp_data.get("website", ""),
                description=comp_data.get("description", ""),
                market_position=comp_data.get("market_position", ""),
                swot=SWOTAnalysis(
                    product_name=comp_name,
                    strengths=[SWOTItem(description=s) for s in swot.get("strengths", [])],
                    weaknesses=[SWOTItem(description=w) for w in swot.get("weaknesses", [])],
                    opportunities=[SWOTItem(description=o) for o in swot.get("opportunities", [])],
                    threats=[SWOTItem(description=t) for t in swot.get("threats", [])],
                ) if swot else None,
                sources=[SourceReference(url=s.get("url", ""), title=s.get("title", ""))
                         for s in comp_data.get("sources", [])],
            )
            profiles.append(profile.model_dump())

        return profiles

    def _parse_json(self, text: str) -> Dict:
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text.strip())
