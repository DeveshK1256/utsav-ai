"""
Unit tests for Google Gemini Providers with full offline mocking.
Validates multi-modal quote extraction, negotiation drafting, replanning explanations,
vibe extraction, theme generation, retry handling, and fallback behavior.
"""

import json
from unittest.mock import MagicMock, patch
import httpx
import pytest

from backend.app.services.providers.gemini_provider import (
    GeminiQuoteExtractionProvider,
    GeminiNegotiationDraftProvider,
    GeminiReplanningExplanationProvider,
    GeminiVibeProvider,
    ExtractionValidationError,
)


@pytest.fixture
def mock_gemini_quote_response():
    return {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "vendor_name": "Royal Caterers Pune",
                                "category": "caterer",
                                "currency": "INR",
                                "subtotal": 150000.0,
                                "tax_amount": 27000.0,
                                "total_amount": 177000.0,
                                "is_gst_included": True,
                                "validity_date": "2026-12-31",
                                "confidence_score": 0.95,
                                "terms_and_conditions": ["50% advance on booking", "Non-refundable cancellation within 14 days"],
                                "line_items": [
                                    {
                                        "name": "Maharashtrian Traditional Feast",
                                        "qty": 300.0,
                                        "unit": "plate",
                                        "unit_price": 500.0,
                                        "total": 150000.0,
                                        "category_tag": "food",
                                        "notes": "Includes Puran Poli and Modak"
                                    }
                                ]
                            })
                        }
                    ]
                }
            }
        ]
    }


def test_gemini_quote_extraction_success(mock_gemini_quote_response):
    provider = GeminiQuoteExtractionProvider(api_key="mock_gemini_key")

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_gemini_quote_response
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        result = provider.extract_quote_from_document(
            file_bytes=b"%PDF-1.4 mock quote bytes",
            file_name="quote.pdf",
            mime_type="application/pdf",
            category_hint="caterer"
        )

        assert result.vendor_name == "Royal Caterers Pune"
        assert result.total_amount == 177000.0
        assert len(result.line_items) == 1
        assert result.line_items[0].qty == 300.0


def test_gemini_quote_extraction_fallback_on_no_api_key():
    provider = GeminiQuoteExtractionProvider(api_key="")
    result = provider.extract_quote_from_document(
        file_bytes=b"sample",
        file_name="sample.pdf",
        mime_type="application/pdf"
    )
    assert result.vendor_name is not None
    assert result.total_amount > 0


def test_gemini_quote_extraction_retry_and_failure():
    provider = GeminiQuoteExtractionProvider(api_key="mock_key")

    with patch("httpx.Client.post") as mock_post, patch("time.sleep"):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError("Server Error", request=MagicMock(), response=mock_resp)
        mock_post.return_value = mock_resp

        with pytest.raises(ExtractionValidationError):
            provider.extract_quote_from_document(
                file_bytes=b"error",
                file_name="error.pdf",
                mime_type="application/pdf"
            )


def test_gemini_negotiation_draft_success():
    provider = GeminiNegotiationDraftProvider(api_key="mock_key")

    mock_resp_data = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "polite": {
                                    "english": "Dear Royal Caterers, we appreciate your quote. Our target is ₹1,40,000.",
                                    "hindi": "नमस्ते जी, आपके कोटेशन के लिए धन्यवाद। हमारा बजट ₹1,40,000 है।"
                                }
                            })
                        }
                    ]
                }
            }
        ]
    }

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_resp_data
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        res = provider.generate_negotiation_drafts(
            vendor_name="Royal Caterers",
            category="caterer",
            quoted_total=177000.0,
            target_discount_pct=15.0,
            leverage_points=["Off-peak weekday", "Large guest count"]
        )
        assert isinstance(res, dict)
        assert "polite" in res or len(res) > 0


def test_gemini_negotiation_draft_fallback():
    provider = GeminiNegotiationDraftProvider(api_key="")
    res = provider.generate_negotiation_drafts(
        vendor_name="Shree Mandap",
        category="decorator",
        quoted_total=80000.0,
        target_discount_pct=10.0,
        leverage_points=["Immediate booking"]
    )
    assert isinstance(res, dict)
    assert len(res) > 0


def test_gemini_replanning_explanation_success():
    provider = GeminiReplanningExplanationProvider(api_key="mock_key")

    mock_resp_data = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "explanation": "Guest count reduced from 300 to 250. Catering and seating scaled down.",
                                "mitigation_suggestions": ["Update seating chart", "Notify caterer with revised plate count"]
                            })
                        }
                    ]
                }
            }
        ]
    }

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_resp_data
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        res = provider.generate_explanation_and_mitigations(
            change_type="guest_count_changed",
            diff_summary={"budget_total_delta": -50000.0, "budget_total_new": 1450000.0},
            total_budget=1500000.0
        )
        assert isinstance(res, dict)
        assert "explanation" in res


def test_gemini_vibe_provider_success():
    provider = GeminiVibeProvider(api_key="mock_key")

    mock_resp_data = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "images": [
                                    {
                                        "palette": ["#FF9933", "#800020", "#FFD700", "#2E8B57", "#FFF8DC"],
                                        "style_tags": ["royal_rajasthani", "heritage_palace"],
                                        "materials": ["brass", "raw_silk"],
                                        "lighting_mood": "warm_candlelight_ambient",
                                        "flower_types": ["genda_marigold", "rajnigandha"]
                                    }
                                ],
                                "overall_mood_words": ["regal", "festive"]
                            })
                        }
                    ]
                }
            }
        ]
    }

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_resp_data
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        res = provider.extract_vibe_from_images(
            images=[{"data": "mock_b64", "mime_type": "image/jpeg"}],
            text_description="Vibrant royal celebration"
        )
        assert len(res.images) == 1
        assert "regal" in res.overall_mood_words


def test_gemini_theme_generation_success():
    provider = GeminiVibeProvider(api_key="mock_key")

    decor_items = [
        {"category": "stage_backdrop", "name": "Backdrop", "quantity_formula": "1 fixed", "cost_tier": "medium", "sourcing_type": "rent"},
        {"category": "mandap", "name": "Mandap", "quantity_formula": "1 fixed", "cost_tier": "high", "sourcing_type": "rent"},
        {"category": "entrance_arch", "name": "Arch", "quantity_formula": "2 units", "cost_tier": "medium", "sourcing_type": "rent"},
        {"category": "table_centerpiece", "name": "Centerpieces", "quantity_formula": "1 per table", "cost_tier": "low", "sourcing_type": "diy"},
        {"category": "lighting", "name": "Fairy Lights", "quantity_formula": "1 per 10 guests", "cost_tier": "low", "sourcing_type": "rent"},
        {"category": "ceiling_drapes", "name": "Silk Drapes", "quantity_formula": "1 fixed", "cost_tier": "medium", "sourcing_type": "rent"},
        {"category": "photobooth", "name": "Photo Corner", "quantity_formula": "1 fixed", "cost_tier": "low", "sourcing_type": "diy"},
        {"category": "seating_lounges", "name": "Diwan Lounges", "quantity_formula": "1 per 25 guests", "cost_tier": "medium", "sourcing_type": "rent"},
        {"category": "cultural_performance", "name": "Shehnai Troupe", "quantity_formula": "1 fixed", "cost_tier": "medium", "sourcing_type": "rent"},
        {"category": "default", "name": "Toran Hangings", "quantity_formula": "1 fixed", "cost_tier": "low", "sourcing_type": "buy"},
    ]

    mock_resp_data = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "theme_name": "Royal Rajwada Heritage",
                                "palette": ["#990000", "#D4AF37", "#FFFFFF", "#FF9933", "#2E8B57"],
                                "menu_direction": "Traditional Rajasthani & Royal Mughlai dishes",
                                "playlist_genres": ["Sufi", "Classical Shehnai", "Bollywood Fusion"],
                                "dress_code_suggestion": "Royal Festive Attire in jewel tones",
                                "invitation_design_brief": "Rich crimson parchment with gold foil motifs",
                                "decor_items": decor_items
                            })
                        }
                    ]
                }
            }
        ]
    }

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_resp_data
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        res = provider.generate_theme_proposal(
            style_profile={"extracted_palette": ["#990000", "#D4AF37"]},
            event_details={"guest_count": 300, "city": "Jaipur"}
        )
        assert res.theme_name == "Royal Rajwada Heritage"
        assert len(res.decor_items) >= 10
