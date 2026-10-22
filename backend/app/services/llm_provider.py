import os
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from backend.app.schemas.quotes import QuoteExtractionPayloadSchema, ExtractedLineItemSchema


class BaseQuoteExtractionProvider(ABC):
    @abstractmethod
    def extract_quote_from_document(
        self,
        file_bytes: bytes,
        file_name: str,
        mime_type: str,
        category_hint: Optional[str] = None
    ) -> QuoteExtractionPayloadSchema:
        """Extract structured quote payload from document bytes."""
        pass


class BaseNegotiationDraftProvider(ABC):
    @abstractmethod
    def generate_negotiation_drafts(
        self,
        vendor_name: str,
        category: str,
        quoted_total: float,
        target_discount_pct: float,
        leverage_points: List[str],
        competing_vendor_name: Optional[str] = None,
        competing_quote_total: Optional[float] = None
    ) -> Dict[str, Dict[str, str]]:
        """Generate polite, firm, and bundle-ask negotiation draft variants in English and Hindi."""
        pass


class DeterministicStubQuoteExtractionProvider(BaseQuoteExtractionProvider):
    """
    Deterministic stub provider for local tests, schema validation, and CI.
    Zero external network calls, zero token costs, 100% reproducible fixtures.
    """

    def extract_quote_from_document(
        self,
        file_bytes: bytes,
        file_name: str,
        mime_type: str,
        category_hint: Optional[str] = None
    ) -> QuoteExtractionPayloadSchema:
        cat = (category_hint or "caterer").lower()

        if "cater" in cat:
            return QuoteExtractionPayloadSchema(
                vendor_name="Shree Ganesh Caterers & Hospitality",
                category="caterer",
                currency="INR",
                subtotal=525000.0,
                tax_amount=26250.0,
                total_amount=551250.0,
                is_gst_included=True,
                validity_date="2026-12-31",
                confidence_score=0.98,
                terms_and_conditions=[
                    "50% advance at booking, balance 2 days prior to event",
                    "Breakage of crockery to be charged at ₹150 per plate/glass"
                ],
                line_items=[
                    ExtractedLineItemSchema(
                        name="Deluxe Royal Rajasthani Thali Buffet",
                        qty=350.0,
                        unit="plates",
                        unit_price=1200.0,
                        total=420000.0,
                        category_tag="food_buffet",
                        notes="Includes 4 starters, 3 main vegetables, dal baati churma, 3 desserts"
                    ),
                    ExtractedLineItemSchema(
                        name="Live Chaat & Mocktail Counter",
                        qty=350.0,
                        unit="plates",
                        unit_price=250.0,
                        total=87500.0,
                        category_tag="live_counter",
                        notes="Pani puri, dahi bhalla, 4 mocktail varieties"
                    ),
                    ExtractedLineItemSchema(
                        name="Uniformed Banquet Service Staff",
                        qty=15.0,
                        unit="servers",
                        unit_price=1150.0,
                        total=17500.0,
                        category_tag="service_staff",
                        notes="Standard 6-hour dinner service"
                    )
                ]
            )
        elif "venue" in cat:
            return QuoteExtractionPayloadSchema(
                vendor_name="Grand Heritage Palace Banquet & Lawns",
                category="venue",
                currency="INR",
                subtotal=750000.0,
                tax_amount=135000.0,
                total_amount=885000.0,
                is_gst_included=True,
                validity_date="2026-11-30",
                confidence_score=0.96,
                terms_and_conditions=[
                    "Hall AC timing strictly 6:00 PM to 11:30 PM",
                    "Outside decorators must pay ₹35,000 royalty fee"
                ],
                line_items=[
                    ExtractedLineItemSchema(
                        name="Main Banquet Hall & Central Lawn Rental",
                        qty=1.0,
                        unit="day",
                        unit_price=650000.0,
                        total=650000.0,
                        category_tag="rent"
                    ),
                    ExtractedLineItemSchema(
                        name="Bridal Suite & Green Rooms (2 Rooms)",
                        qty=2.0,
                        unit="rooms",
                        unit_price=25000.0,
                        total=50000.0,
                        category_tag="rooms"
                    ),
                    ExtractedLineItemSchema(
                        name="Valet Parking Logistics & Marshals",
                        qty=1.0,
                        unit="package",
                        unit_price=50000.0,
                        total=50000.0,
                        category_tag="parking"
                    )
                ]
            )
        elif "decorator" in cat:
            return QuoteExtractionPayloadSchema(
                vendor_name="Mayur Mandap & Floral Decor Studio",
                category="decorator",
                currency="INR",
                subtotal=420000.0,
                tax_amount=75600.0,
                total_amount=495600.0,
                is_gst_included=True,
                confidence_score=0.94,
                terms_and_conditions=[
                    "Floral rates subject to wholesale mandi fluctuations",
                    "Teardown must be complete by 6:00 AM next day"
                ],
                line_items=[
                    ExtractedLineItemSchema(
                        name="Vedic Wedding Mandap with Fresh Marigold & Jasmine",
                        qty=1.0,
                        unit="set",
                        unit_price=240000.0,
                        total=240000.0,
                        category_tag="mandap"
                    ),
                    ExtractedLineItemSchema(
                        name="Grand Entrance Arch & Pathway Truss Lighting",
                        qty=1.0,
                        unit="set",
                        unit_price=120000.0,
                        total=120000.0,
                        category_tag="entrance"
                    ),
                    ExtractedLineItemSchema(
                        name="Dining Area Centerpieces & Fabric Draping",
                        qty=1.0,
                        unit="package",
                        unit_price=60000.0,
                        total=60000.0,
                        category_tag="draping"
                    )
                ]
            )
        else:
            return QuoteExtractionPayloadSchema(
                vendor_name="Snapshot Stories Cinematography",
                category="photographer",
                currency="INR",
                subtotal=280000.0,
                tax_amount=50400.0,
                total_amount=330400.0,
                is_gst_included=True,
                confidence_score=0.97,
                terms_and_conditions=[
                    "Raw footage provided on external hard drive provided by client",
                    "Teaser video delivered within 15 days, main film within 60 days"
                ],
                line_items=[
                    ExtractedLineItemSchema(
                        name="Traditional Photo & 4K Video Coverage (2 Days)",
                        qty=2.0,
                        unit="days",
                        unit_price=90000.0,
                        total=180000.0,
                        category_tag="photo_video"
                    ),
                    ExtractedLineItemSchema(
                        name="Candid Lead Photographer & Cinematic Teaser",
                        qty=1.0,
                        unit="package",
                        unit_price=100000.0,
                        total=100000.0,
                        category_tag="candid"
                    )
                ]
            )


class DeterministicStubNegotiationDraftProvider(BaseNegotiationDraftProvider):
    """
    Deterministic negotiation draft generator for tests and offline operations.
    Formats contextual leverage points into culturally grounded negotiation letters.
    """

    def generate_negotiation_drafts(
        self,
        vendor_name: str,
        category: str,
        quoted_total: float,
        target_discount_pct: float,
        leverage_points: List[str],
        competing_vendor_name: Optional[str] = None,
        competing_quote_total: Optional[float] = None
    ) -> Dict[str, Dict[str, str]]:
        target_amount = round(quoted_total * (1.0 - target_discount_pct / 100.0), 2)
        diff_amount = round(quoted_total - target_amount, 2)
        leverage_summary_en = "; ".join(leverage_points) if leverage_points else "standard regional festival rates"

        polite_en = (
            f"Dear {vendor_name},\n\n"
            f"Thank you for sharing your detailed proposal for our upcoming celebration. Our family deeply admires your work and craft.\n\n"
            f"We are working within a predetermined family budget envelope. Based on our requirements and local benchmarks ({leverage_summary_en}), "
            f"we would love to finalize your team immediately if we can align on an inclusive rate of ₹{target_amount:,.0f} (a modest adjustment of ₹{diff_amount:,.0f}).\n\n"
            f"Could we confirm this inclusive figure so we can proceed with the advance token today?\n\nWarm regards,\nFamily Host"
        )
        polite_hi = (
            f"नमस्ते {vendor_name} जी,\n\n"
            f"आपके द्वारा भेजे गए कोटेशन के लिए बहुत-बहुत धन्यवाद। हमारे परिवार को आपका काम बहुत पसंद आया है।\n\n"
            f"हमारे परिवार का बजट सीमित है। यदि आप इसे कुल ₹{target_amount:,.0f} में अंतिम रूप दे सकें, तो हम आज ही टोकन राशि देकर बुकिंग कन्फर्म करना चाहते हैं।\n\n"
            f"कृपया बताएं कि क्या हम इस बजट पर आगे बढ़ सकते हैं?\n\nसादर,\nहोस्ट परिवार"
        )

        firm_en = (
            f"Dear {vendor_name},\n\n"
            f"We have thoroughly reviewed your quote of ₹{quoted_total:,.0f}. "
            + (f"We currently have a competitive and fully itemized proposal from {competing_vendor_name} at ₹{competing_quote_total:,.0f}. " if competing_vendor_name and competing_quote_total else "")
            + f"Furthermore, we noted potential extra contingencies ({leverage_summary_en}) that need to be explicitly capped.\n\n"
            f"We are prepared to close today at ₹{target_amount:,.0f} inclusive of all taxes, overtime, and logistics with zero hidden surcharges. "
            f"Please let us know if this works so we can sign the agreement.\n\nRegards,\nEvent Host"
        )
        firm_hi = (
            f"नमस्कार {vendor_name} जी,\n\n"
            f"हमने आपके ₹{quoted_total:,.0f} के प्रस्ताव की समीक्षा की है। "
            + (f"हमारे पास {competing_vendor_name} से ₹{competing_quote_total:,.0f} का पूरा प्रस्ताव भी उपलब्ध है। " if competing_vendor_name and competing_quote_total else "")
            + f"साथ ही कुछ अतिरिक्त खर्चों ({leverage_summary_en}) पर स्पष्टता जरूरी है।\n\n"
            f"यदि आप बिना किसी छिपे शुल्क के सभी कर सहित ₹{target_amount:,.0f} में तैयार हैं, तो हम आज ही अनुबंध कर सकते हैं।\n\nधन्यवाद,\nहोस्ट"
        )

        bundle_en = (
            f"Dear {vendor_name},\n\n"
            f"We would love to retain your team at the quoted price of ₹{quoted_total:,.0f}, provided we can bundle key critical services "
            f"that are currently unmentioned ({leverage_summary_en}) into this comprehensive package.\n\n"
            f"If you can include these elements within the quoted ₹{quoted_total:,.0f} with an all-inclusive formal invoice, we will sign and pay the booking advance immediately.\n\nBest regards,\nHost Family"
        )
        bundle_hi = (
            f"नमस्ते {vendor_name} जी,\n\n"
            f"हम आपके ₹{quoted_total:,.0f} के मूल्य पर काम करने के लिए तैयार हैं, यदि आप कुछ जरूरी सेवाएं ({leverage_summary_en}) इसी पैकेज में सम्मिलित कर लें।\n\n"
            f"यदि यह सब ₹{quoted_total:,.0f} के कुल बिल में शामिल हो जाता है, तो हम आज ही बुकिंग अग्रिम राशि जारी कर देंगे।\n\nसादर,\nहोस्ट परिवार"
        )

        return {
            "polite": {"english": polite_en, "hindi": polite_hi},
            "firm": {"english": firm_en, "hindi": firm_hi},
            "bundle_ask": {"english": bundle_en, "hindi": bundle_hi}
        }


def get_quote_extraction_provider() -> BaseQuoteExtractionProvider:
    """
    Factory returning real LLM extraction provider if API key exists in environment,
    otherwise returning the deterministic stub provider for testability & offline execution.
    """
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        try:
            from backend.app.services.providers.gemini_provider import GeminiQuoteExtractionProvider
            return GeminiQuoteExtractionProvider(api_key=gemini_key)
        except Exception:
            pass

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            from backend.app.services.providers.openai_provider import OpenAIQuoteExtractionProvider
            return OpenAIQuoteExtractionProvider(api_key=openai_key)
        except Exception:
            pass

    return DeterministicStubQuoteExtractionProvider()


def get_negotiation_draft_provider() -> BaseNegotiationDraftProvider:
    """
    Factory returning negotiation draft generator provider.
    """
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        try:
            from backend.app.services.providers.gemini_provider import GeminiNegotiationDraftProvider
            return GeminiNegotiationDraftProvider(api_key=gemini_key)
        except Exception:
            pass

    return DeterministicStubNegotiationDraftProvider()
