"""Tests for competitive analysis schemas."""

import pytest
from competitive_analysis.schemas.competitive import (
    SourceReference, Feature, FeatureTree, PricingTier, PricingModel,
    SWOTItem, SWOTAnalysis, UserSegment, UserProfile,
    CompetitorProfile, CompetitiveReport, ReviewSummary,
)


def test_source_reference_creation():
    ref = SourceReference(url="https://example.com", title="Test", snippet="Some info")
    assert ref.url == "https://example.com"
    assert ref.confidence == 0.8  # default


def test_feature_nested():
    f = Feature(
        name="AI Assistant",
        description="Built-in AI",
        category="advanced",
        sub_features=[Feature(name="Summarize", description="Auto summarize")],
    )
    assert len(f.sub_features) == 1
    assert f.sub_features[0].name == "Summarize"


def test_pricing_model():
    pm = PricingModel(
        product_name="Notion",
        has_free_tier=True,
        tiers=[
            PricingTier(name="Free", price="$0", features_included=["Basic pages"]),
            PricingTier(name="Plus", price="$8/mo", features_included=["Unlimited blocks"]),
        ],
        pricing_strategy="freemium",
    )
    assert len(pm.tiers) == 2
    assert pm.has_free_tier is True


def test_swot_analysis():
    swot = SWOTAnalysis(
        product_name="Notion",
        strengths=[SWOTItem(description="All-in-one workspace", impact="high")],
        weaknesses=[SWOTItem(description="Steep learning curve", impact="medium")],
    )
    assert len(swot.strengths) == 1
    assert swot.strengths[0].impact == "high"


def test_competitor_profile_full():
    profile = CompetitorProfile(
        company_name="Notion Labs",
        product_name="Notion",
        website="https://notion.so",
        description="All-in-one workspace",
        sources=[SourceReference(url="https://notion.so")],
    )
    assert profile.company_name == "Notion Labs"
    assert profile.feature_tree is None  # optional
    assert len(profile.sources) == 1


def test_competitive_report():
    report = CompetitiveReport(
        query="Compare Notion vs Obsidian",
        competitors=[
            CompetitorProfile(company_name="Notion", product_name="Notion"),
            CompetitorProfile(company_name="Obsidian", product_name="Obsidian"),
        ],
    )
    assert len(report.competitors) == 2
    assert report.query == "Compare Notion vs Obsidian"


def test_schema_serialization():
    """Test that schemas can round-trip through JSON."""
    profile = CompetitorProfile(
        company_name="Test",
        product_name="TestProd",
        swot=SWOTAnalysis(
            product_name="TestProd",
            strengths=[SWOTItem(description="Fast", impact="high",
                               sources=[SourceReference(url="https://test.com")])],
        ),
    )
    data = profile.model_dump()
    restored = CompetitorProfile(**data)
    assert restored.company_name == "Test"
    assert len(restored.swot.strengths) == 1
    assert restored.swot.strengths[0].sources[0].url == "https://test.com"
