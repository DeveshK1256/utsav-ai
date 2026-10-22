import json
import time
import base64
import logging
from typing import Dict, Any, Optional, List
import httpx
from pydantic import ValidationError

from backend.app.schemas.quotes import QuoteExtractionPayloadSchema, ExtractedLineItemSchema
from backend.app.services.llm_provider import (
    BaseQuoteExtractionProvider,
    BaseNegotiationDraftProvider,
    DeterministicStubQuoteExtractionProvider,
    DeterministicStubNegotiationDraftProvider,
    ExtractionValidationError
)

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent"

class GeminiQuoteExtractionProvider(BaseQuoteExtractionProvider):
    """
    Real Google Gemini provider for multi-modal document extraction (PDF, images, text).
    Strictly schema-validated via Pydantic with 2-attempt retry logic.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.fallback_stub = DeterministicStubQuoteExtractionProvider()

    def extract_quote_from_document(
        self,
        file_bytes: bytes,
        file_name: str,
        mime_type: str,
        category_hint: Optional[str] = None
    ) -> QuoteExtractionPayloadSchema:
        if not self.api_key:
            logger.warning("No GEMINI_API_KEY provided; falling back to deterministic stub.")
            return self.fallback_stub.extract_quote_from_document(file_bytes, file_name, mime_type, category_hint)

        prompt_system = (
            "You are an expert Indian wedding and cultural event vendor quote extraction specialist. "
            "Extract all structured financial and contract information from the provided vendor quotation.\n\n"
            "CRITICAL RULES:\n"
            "1. Zero invented facts: only extract numbers, dates, terms, and items present in the document.\n"
            "2. Preserve currency as INR unless specified otherwise.\n"
            "3. Return ONLY a valid JSON object matching this schema:\n"
            "{\n"
            '  "vendor_name": "string",\n'
            '  "category": "caterer | venue | decorator | photographer | other",\n'
            '  "currency": "INR",\n'
            '  "subtotal": 0.0,\n'
            '  "tax_amount": 0.0,\n'
            '  "total_amount": 0.0,\n'
            '  "is_gst_included": true/false,\n'
            '  "validity_date": "YYYY-MM-DD or null",\n'
            '  "confidence_score": 0.95,\n'
            '  "terms_and_conditions": ["term 1", "term 2"],\n'
            '  "line_items": [\n'
            '    {\n'
            '      "name": "item description",\n'
            '      "qty": 1.0,\n'
            '      "unit": "plate/day/package/units",\n'
            '      "unit_price": 0.0,\n'
            '      "total": 0.0,\n'
            '      "category_tag": "tag or null",\n'
            '      "notes": "string or null"\n'
            '    }\n'
            '  ]\n'
            "}"
        )

        # Prepare request payload
        encoded_data = base64.b64encode(file_bytes).decode("utf-8")
        parts: List[Dict[str, Any]] = [
            {"text": f"Document category hint: {category_hint or 'unknown'}. File name: {file_name}.\n\n{prompt_system}"},
            {
                "inline_data": {
                    "mime_type": mime_type if mime_type != "application/octet-stream" else "application/pdf",
                    "data": encoded_data
                }
            }
        ]

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1
            }
        }

        # Up to 2 retries on validation failure
        attempts = 0
        last_error = None
        while attempts < 3:
            attempts += 1
            try:
                with httpx.Client(timeout=45.0) as client:
                    resp = client.post(
                        f"{GEMINI_API_URL}?key={self.api_key}",
                        json=payload
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    
                    parts = data["candidates"][0]["content"]["parts"]
                    candidate_text = "".join(p.get("text", "") for p in parts).strip()
                    cleaned_json = candidate_text
                    if cleaned_json.startswith("```json"):
                        cleaned_json = cleaned_json[7:]
                    if cleaned_json.startswith("```"):
                        cleaned_json = cleaned_json[3:]
                    if cleaned_json.endswith("```"):
                        cleaned_json = cleaned_json[:-3]
                    
                    parsed_dict = json.loads(cleaned_json.strip())
                    validated = QuoteExtractionPayloadSchema.model_validate(parsed_dict)
                    # Zero LLM self-reported math: compute confidence deterministically in Python
                    validated.confidence_score = validated.compute_deterministic_confidence()
                    return validated

            except (httpx.HTTPError, KeyError, json.JSONDecodeError, ValidationError) as e:
                last_error = e
                logger.warning(f"Gemini quote extraction attempt {attempts} failed: {e}")
                if attempts < 3:
                    # Exponential backoff on rate-limits (HTTP 429) or transient errors
                    sleep_sec = 2.0 * attempts
                    logger.info(f"Retrying Gemini extraction in {sleep_sec}s...")
                    time.sleep(sleep_sec)

        logger.error(f"Gemini quote extraction failed after 2 retries ({last_error}).")
        raise ExtractionValidationError(f"Schema validation failed after 2 retries (3 total attempts): {last_error}")


class GeminiNegotiationDraftProvider(BaseNegotiationDraftProvider):
    """
    Real Google Gemini provider for localized Hindi/English negotiation drafts.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.fallback_stub = DeterministicStubNegotiationDraftProvider()

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
        if not self.api_key:
            return self.fallback_stub.generate_negotiation_drafts(
                vendor_name, category, quoted_total, target_discount_pct, leverage_points, competing_vendor_name, competing_quote_total
            )

        target_amount = round(quoted_total * (1.0 - target_discount_pct / 100.0), 2)
        leverage_desc = "\n".join(f"- {lp}" for lp in leverage_points) if leverage_points else "Standard seasonal benchmarks"

        competing_info = ""
        if competing_vendor_name and competing_quote_total:
            competing_info = f"Alternative competitor quote: {competing_vendor_name} offering ₹{competing_quote_total:,.0f}."

        prompt = (
            f"You are an expert Indian wedding negotiator drafting respectful, culturally grounded negotiation messages for an Indian family.\n"
            f"Vendor: {vendor_name} ({category})\n"
            f"Quoted Total: ₹{quoted_total:,.0f}\n"
            f"Target Budget: ₹{target_amount:,.0f} ({target_discount_pct}% discount target)\n"
            f"Key Leverage Points & Detected Cost Alerts:\n{leverage_desc}\n"
            f"{competing_info}\n\n"
            f"Generate three distinct message variants: 'polite', 'firm', and 'bundle_ask'.\n"
            f"Each variant must have both an 'english' and a 'hindi' (Devanagari script) version.\n"
            f"Return JSON strictly with format:\n"
            "{\n"
            '  "polite": {"english": "...", "hindi": "..."},\n'
            '  "firm": {"english": "...", "hindi": "..."},\n'
            '  "bundle_ask": {"english": "...", "hindi": "..."}\n'
            "}"
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2
            }
        }

        attempts = 0
        while attempts < 3:
            attempts += 1
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(
                        f"{GEMINI_API_URL}?key={self.api_key}",
                        json=payload
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    parts = data["candidates"][0]["content"]["parts"]
                    text = "".join(p.get("text", "") for p in parts).strip()
                    if text.startswith("```json"):
                        text = text[7:]
                    if text.startswith("```"):
                        text = text[3:]
                    if text.endswith("```"):
                        text = text[:-3]
                    parsed = json.loads(text.strip())
                    if "polite" in parsed and "firm" in parsed and "bundle_ask" in parsed:
                        return parsed
            except Exception as e:
                logger.warning(f"Gemini negotiation draft attempt {attempts} failed: {e}")
                if attempts < 3:
                    time.sleep(2.0 * attempts)

        logger.warning("All Gemini negotiation draft attempts failed; falling back to deterministic stub.")
        return self.fallback_stub.generate_negotiation_drafts(
            vendor_name, category, quoted_total, target_discount_pct, leverage_points, competing_vendor_name, competing_quote_total
        )
