"""
Competitive Analysis Knowledge Schemas

Defines structured output schemas that all agents must conform to.
Ensures consistency across the pipeline: 功能树, 定价模型, 用户画像, SWOT, etc.
Every schema field supports traceability via source_urls.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ============ Source Traceability ============

class SourceReference(BaseModel):
    """Every claim must link back to its data source for traceability."""
    url: str = Field(..., description="Original data source URL")
    title: str = Field(default="", description="Page/document title")
    accessed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    snippet: str = Field(default="", description="Relevant excerpt from source")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence score")


# ============ Feature Tree (功能树) ============

class Feature(BaseModel):
    """A single product feature with traceability."""
    name: str
    description: str = ""
    category: str = Field(default="core", description="core / advanced / unique")
    sub_features: List[Feature] = Field(default_factory=list)
    sources: List[SourceReference] = Field(default_factory=list)


class FeatureTree(BaseModel):
    """Complete feature tree for one competitor."""
    product_name: str
    total_features: int = 0
    categories: Dict[str, List[Feature]] = Field(default_factory=dict)
    sources: List[SourceReference] = Field(default_factory=list)


# ============ Pricing Model (定价模型) ============

class PricingTier(BaseModel):
    """A single pricing tier/plan."""
    name: str
    price: str = Field(description="e.g. '$9.99/mo', 'Free', 'Enterprise contact'")
    billing_cycle: str = Field(default="monthly")
    features_included: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    sources: List[SourceReference] = Field(default_factory=list)


class PricingModel(BaseModel):
    """Complete pricing information for one competitor."""
    product_name: str
    currency: str = "USD"
    has_free_tier: bool = False
    tiers: List[PricingTier] = Field(default_factory=list)
    pricing_strategy: str = Field(default="", description="freemium / subscription / usage-based / one-time")
    sources: List[SourceReference] = Field(default_factory=list)


# ============ User Persona (用户画像) ============

class UserSegment(BaseModel):
    """A target user segment."""
    segment_name: str
    description: str = ""
    demographics: Dict[str, str] = Field(default_factory=dict)
    pain_points: List[str] = Field(default_factory=list)
    use_cases: List[str] = Field(default_factory=list)
    sources: List[SourceReference] = Field(default_factory=list)


class UserProfile(BaseModel):
    """Complete user profile analysis for one competitor."""
    product_name: str
    primary_segments: List[UserSegment] = Field(default_factory=list)
    estimated_user_base: str = Field(default="unknown")
    geographic_focus: List[str] = Field(default_factory=list)
    sources: List[SourceReference] = Field(default_factory=list)


# ============ SWOT Analysis ============

class SWOTItem(BaseModel):
    """A single SWOT item with evidence."""
    description: str
    impact: str = Field(default="medium", description="high / medium / low")
    sources: List[SourceReference] = Field(default_factory=list)


class SWOTAnalysis(BaseModel):
    """SWOT analysis for one competitor."""
    product_name: str
    strengths: List[SWOTItem] = Field(default_factory=list)
    weaknesses: List[SWOTItem] = Field(default_factory=list)
    opportunities: List[SWOTItem] = Field(default_factory=list)
    threats: List[SWOTItem] = Field(default_factory=list)
    sources: List[SourceReference] = Field(default_factory=list)


# ============ User Reviews Summary ============

class ReviewSummary(BaseModel):
    """Aggregated user review data."""
    product_name: str
    overall_rating: Optional[float] = None
    total_reviews: int = 0
    positive_themes: List[str] = Field(default_factory=list)
    negative_themes: List[str] = Field(default_factory=list)
    notable_quotes: List[str] = Field(default_factory=list)
    review_platforms: List[str] = Field(default_factory=list)
    sources: List[SourceReference] = Field(default_factory=list)


# ============ Complete Competitor Profile ============

class CompetitorProfile(BaseModel):
    """Full structured profile for one competitor - conforms to the competitive knowledge schema."""
    company_name: str
    product_name: str
    website: str = ""
    founded_year: Optional[int] = None
    headquarters: str = ""
    description: str = ""
    feature_tree: Optional[FeatureTree] = None
    pricing: Optional[PricingModel] = None
    user_profile: Optional[UserProfile] = None
    swot: Optional[SWOTAnalysis] = None
    reviews: Optional[ReviewSummary] = None
    market_position: str = ""
    recent_updates: List[str] = Field(default_factory=list)
    sources: List[SourceReference] = Field(default_factory=list)


# ============ Competitive Analysis Report Schema ============

class CompetitiveReport(BaseModel):
    """The final structured output - a complete competitive analysis report."""
    query: str = Field(description="Original analysis request")
    industry: str = ""
    analysis_date: str = Field(default_factory=lambda: datetime.now().isoformat())
    competitors: List[CompetitorProfile] = Field(default_factory=list)
    comparison_matrix: Dict[str, Dict[str, str]] = Field(
        default_factory=dict,
        description="Feature comparison matrix: {feature: {competitor: value}}"
    )
    executive_summary: str = ""
    key_insights: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    methodology: str = ""
    all_sources: List[SourceReference] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
