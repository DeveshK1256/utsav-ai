import base64
import json
import logging
import time
from typing import Any, cast

import httpx
from pydantic import ValidationError

from backend.app.schemas.quotes import (
    QuoteExtractionPayloadSchema,
)
from backend.app.schemas.vibe import (
    ThemeGenerationPayloadSchema,
    VibeExtractionPayloadSchema,
)
from backend.app.services.llm_provider import (
    BaseNegotiationDraftProvider,
    BaseQuoteExtractionProvider,
    BaseReplanningExplanationProvider,
    BaseThemeGenerationProvider,
    BaseVibeExtractionProvider,
    DeterministicStubNegotiationDraftProvider,
    DeterministicStubQuoteExtractionProvider,
    DeterministicStubReplanningExplanationProvider,
    DeterministicStubVibeProvider,
    ExtractionValidationError,
)

logger = logging.getLogger(__name__)

GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent"
)


class GeminiQuoteExtractionProvider(BaseQuoteExtractionProvider):
    """
    Real Google Gemini provider for multi-modal document extraction (PDF, images, text).
    Strictly schema-validated via Pydantic with 2-attempt retry logic.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.fallback_stub = DeterministicStubQuoteExtractionProvider()

    def extract_quote_from_document(
        self, file_bytes: bytes, file_name: str, mime_type: str, category_hint: str | None = None
    ) -> QuoteExtractionPayloadSchema:
        if not self.api_key:
            logger.warning("No GEMINI_API_KEY provided; falling back to deterministic stub.")
            return self.fallback_stub.extract_quote_from_document(
                file_bytes, file_name, mime_type, category_hint
            )

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
            "    {\n"
            '      "name": "item description",\n'
            '      "qty": 1.0,\n'
            '      "unit": "plate/day/package/units",\n'
            '      "unit_price": 0.0,\n'
            '      "total": 0.0,\n'
            '      "category_tag": "tag or null",\n'
            '      "notes": "string or null"\n'
            "    }\n"
            "  ]\n"
            "}"
        )

        # Prepare request payload
        encoded_data = base64.b64encode(file_bytes).decode("utf-8")
        parts: list[dict[str, Any]] = [
            {
                "text": f"Document category hint: {category_hint or 'unknown'}. File name: {file_name}.\n\n{prompt_system}"
            },
            {
                "inline_data": {
                    "mime_type": mime_type
                    if mime_type != "application/octet-stream"
                    else "application/pdf",
                    "data": encoded_data,
                }
            },
        ]

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.1},
        }

        # Up to 2 retries on validation failure
        attempts = 0
        last_error = None
        while attempts < 3:
            attempts += 1
            try:
                with httpx.Client(timeout=45.0) as client:
                    resp = client.post(f"{GEMINI_API_URL}?key={self.api_key}", json=payload)
                    resp.raise_for_status()
                    data = resp.json()

                    parts = data["candidates"][0]["content"]["parts"]
                    candidate_text = "".join(p.get("text", "") for p in parts).strip()
                    cleaned_json = candidate_text
                    cleaned_json = cleaned_json.removeprefix("```json")
                    cleaned_json = cleaned_json.removeprefix("```")
                    cleaned_json = cleaned_json.removesuffix("```")

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
        raise ExtractionValidationError(
            f"Schema validation failed after 2 retries (3 total attempts): {last_error}"
        )


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
        leverage_points: list[str],
        competing_vendor_name: str | None = None,
        competing_quote_total: float | None = None,
    ) -> dict[str, dict[str, str]]:
        if not self.api_key:
            return self.fallback_stub.generate_negotiation_drafts(
                vendor_name,
                category,
                quoted_total,
                target_discount_pct,
                leverage_points,
                competing_vendor_name,
                competing_quote_total,
            )

        target_amount = round(quoted_total * (1.0 - target_discount_pct / 100.0), 2)
        leverage_desc = (
            "\n".join(f"- {lp}" for lp in leverage_points)
            if leverage_points
            else "Standard seasonal benchmarks"
        )

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
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.2},
        }

        attempts = 0
        while attempts < 3:
            attempts += 1
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(f"{GEMINI_API_URL}?key={self.api_key}", json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    parts = data["candidates"][0]["content"]["parts"]
                    text = "".join(p.get("text", "") for p in parts).strip()
                    text = text.removeprefix("```json")
                    text = text.removeprefix("```")
                    text = text.removesuffix("```")
                    parsed = json.loads(text.strip())
                    if "polite" in parsed and "firm" in parsed and "bundle_ask" in parsed:
                        return cast(dict[str, dict[str, str]], parsed)
            except (
                httpx.HTTPError,
                KeyError,
                IndexError,
                json.JSONDecodeError,
                ValidationError,
                TypeError,
                ValueError,
            ) as e:
                logger.warning(f"Gemini negotiation draft attempt {attempts} failed: {e}")
                if attempts < 3:
                    time.sleep(2.0 * attempts)

        logger.warning(
            "All Gemini negotiation draft attempts failed; falling back to deterministic stub."
        )
        return self.fallback_stub.generate_negotiation_drafts(
            vendor_name,
            category,
            quoted_total,
            target_discount_pct,
            leverage_points,
            competing_vendor_name,
            competing_quote_total,
        )


class GeminiReplanningExplanationProvider(BaseReplanningExplanationProvider):
    """
    Real Google Gemini provider for generating plain-language replanning explanations and mitigations.
    Grounded strictly in pre-computed figures. Falls back gracefully to deterministic stub.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.fallback_stub = DeterministicStubReplanningExplanationProvider()

    def generate_explanation_and_mitigations(
        self, change_type: str, diff_summary: dict[str, Any], total_budget: float
    ) -> dict[str, Any]:
        if not self.api_key:
            return self.fallback_stub.generate_explanation_and_mitigations(
                change_type, diff_summary, total_budget
            )

        delta = diff_summary.get("budget_total_delta", 0.0)
        new_total = diff_summary.get("budget_total_new", 0.0)
        over_budget = new_total > total_budget
        over_amount = round(new_total - total_budget, 2) if over_budget else 0.0

        prompt = (
            f"You are an expert Indian wedding and cultural event planning advisor (Plan B replanning engine).\n"
            f"A change event was processed with final computed numbers:\n"
            f"- Change Type: {change_type}\n"
            f"- Original Budget Total: ₹{diff_summary.get('budget_total_old', 0.0):,.2f}\n"
            f"- Revised Budget Total: ₹{new_total:,.2f}\n"
            f"- Net Budget Delta: ₹{delta:+,.2f}\n"
            f"- Event Ceiling Budget: ₹{total_budget:,.2f}\n"
            f"- Over Budget: {'YES (by ₹' + f'{over_amount:,.2f}' + ')' if over_budget else 'NO'}\n"
            f"- Capacity Exceeded: {diff_summary.get('capacity_exceeded', False)}\n"
            f"- Capacity Warning: {diff_summary.get('capacity_warning')}\n\n"
            f"CRITICAL RULES:\n"
            f"1. Zero invented numbers: only refer to the numbers given above.\n"
            f"2. Provide a reassuring, concise plain-language explanation of what changed.\n"
            f"3. If over budget, provide 2-3 concrete mitigation suggestions using standard categories (decor, photography, catering).\n"
            f"Return strictly JSON format:\n"
            "{\n"
            '  "explanation": "string explanation",\n'
            '  "mitigation_suggestions": ["suggestion 1", "suggestion 2"]\n'
            "}"
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.2},
        }

        attempts = 0
        while attempts < 3:
            attempts += 1
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(f"{GEMINI_API_URL}?key={self.api_key}", json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    parts = data["candidates"][0]["content"]["parts"]
                    text = "".join(p.get("text", "") for p in parts).strip()
                    text = text.removeprefix("```json")
                    text = text.removeprefix("```")
                    text = text.removesuffix("```")
                    parsed = json.loads(text.strip())
                    if "explanation" in parsed and "mitigation_suggestions" in parsed:
                        return {
                            "explanation": parsed["explanation"],
                            "mitigation_suggestions": parsed["mitigation_suggestions"],
                            "provider_used": "gemini-3-flash-preview",
                            "fallback_warning": None,
                            "reasoning": {
                                "source": "gemini-3-flash-preview",
                                "change_type": change_type,
                                "budget_total_delta": delta,
                                "is_over_budget": over_budget,
                                "overage_amount": over_amount,
                            },
                        }
            except (
                httpx.HTTPError,
                KeyError,
                IndexError,
                json.JSONDecodeError,
                ValidationError,
                TypeError,
                ValueError,
            ) as e:
                last_err = e
                is_429 = "429" in str(e) or (
                    hasattr(e, "response") and getattr(e.response, "status_code", None) == 429
                )
                logger.error(
                    f"CRITICAL: Gemini replanning explanation attempt {attempts} failed with {type(e).__name__}: {e}. "
                    f"Quota exhausted: {is_429}."
                )
                if attempts < 3:
                    time.sleep(2.0 * attempts)

        fallback_reason = (
            "stub_fallback_quota_exhausted (HTTP 429)"
            if ("429" in str(last_err))
            else f"stub_fallback_error ({type(last_err).__name__})"
        )
        warning_msg = (
            f"LOUD ALERT: Live LLM explanation failed after 3 attempts due to {last_err}. "
            f"Output safely degraded to deterministic rule-based template ({fallback_reason})."
        )
        logger.error(warning_msg)
        stub_res = self.fallback_stub.generate_explanation_and_mitigations(
            change_type, diff_summary, total_budget
        )
        stub_res["provider_used"] = fallback_reason
        stub_res["fallback_warning"] = warning_msg
        return stub_res


class GeminiVibeProvider(BaseVibeExtractionProvider, BaseThemeGenerationProvider):
    """
    Real Google Gemini provider for multi-image aesthetic vibe extraction and theme generation (M3).
    Batches up to 10 images into a single generateContent call per DEC-023.
    Enforces Zero LLM Math: LLM produces only quantity formulas and cost tiers.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.fallback_stub = DeterministicStubVibeProvider()
        self.last_provider_used: str = "gemini-3-flash-preview"
        self.last_fallback_warning: str | None = None

    def extract_vibe_from_images(
        self, images: list[dict[str, Any]], text_description: str | None = None
    ) -> VibeExtractionPayloadSchema:
        if not self.api_key:
            logger.warning(
                "No GEMINI_API_KEY provided; falling back to deterministic stub for vibe extraction."
            )
            self.last_provider_used = "deterministic_stub"
            return self.fallback_stub.extract_vibe_from_images(images, text_description)

        system_instruction = (
            "You are an expert Indian wedding and cultural event aesthetic stylist and visual designer.\n"
            "Analyze the provided inspiration image(s) and accompanying aesthetic description.\n"
            "Extract the visual and cultural essence into structured JSON with:\n"
            "{\n"
            '  "images": [\n'
            "    {\n"
            '      "palette": ["#FF9933", "#800020", "#FFD700", "#2E8B57", "#FFF8DC"],\n'
            '      "style_tags": ["royal_rajasthani", "heritage_palace", "traditional"],\n'
            '      "materials": ["brass", "raw_silk", "marigold", "terracotta"],\n'
            '      "lighting_mood": "warm_candlelight_ambient",\n'
            '      "flower_types": ["genda_marigold", "rajnigandha", "rose"]\n'
            "    }\n"
            "  ],\n"
            '  "overall_mood_words": ["regal", "vibrant", "traditional", "festive", "auspicious"]\n'
            "}\n\n"
            "CRITICAL RULES:\n"
            "1. If N images are provided, the 'images' array MUST contain exactly N items corresponding to each image in order.\n"
            "2. Each palette must have exactly 5 valid hex color codes starting with #.\n"
            "3. Ground all tags, materials, and flowers in Indian event design traditions.\n"
            "4. Return strictly valid JSON."
        )

        parts: list[dict[str, Any]] = [
            {
                "text": f"{system_instruction}\n\nUser Vision Description: {text_description or 'None provided'}"
            }
        ]

        # Batched multi-image inlineData injection (DEC-023)
        for img in images:
            raw_bytes = img.get("bytes", b"")
            m_type = img.get("mime_type") or "image/jpeg"
            if m_type == "application/octet-stream":
                m_type = "image/jpeg"
            encoded = base64.b64encode(raw_bytes).decode("utf-8")
            parts.append({"inline_data": {"mime_type": m_type, "data": encoded}})

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.2},
        }

        attempts = 0
        last_err = None
        while attempts < 3:
            attempts += 1
            try:
                with httpx.Client(timeout=45.0) as client:
                    resp = client.post(f"{GEMINI_API_URL}?key={self.api_key}", json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    res_parts = data["candidates"][0]["content"]["parts"]
                    text = "".join(p.get("text", "") for p in res_parts).strip()
                    text = text.removeprefix("```json")
                    text = text.removeprefix("```")
                    text = text.removesuffix("```")
                    parsed = json.loads(text.strip())
                    validated = VibeExtractionPayloadSchema.model_validate(parsed)
                    self.last_provider_used = "gemini-3-flash-preview"
                    self.last_fallback_warning = None
                    return validated
            except (
                httpx.HTTPError,
                KeyError,
                IndexError,
                json.JSONDecodeError,
                ValidationError,
                TypeError,
                ValueError,
            ) as e:
                last_err = e
                is_429 = "429" in str(e) or (
                    hasattr(e, "response") and getattr(e.response, "status_code", None) == 429
                )
                logger.error(
                    f"CRITICAL: Gemini vibe extraction attempt {attempts} failed with {type(e).__name__}: {e}. "
                    f"Quota exhausted: {is_429}."
                )
                if attempts < 3:
                    time.sleep(2.0 * attempts)

        fallback_reason = (
            "stub_fallback_quota_exhausted (HTTP 429)"
            if ("429" in str(last_err))
            else f"stub_fallback_error ({type(last_err).__name__})"
        )
        warning_msg = (
            f"LOUD ALERT: Live LLM vibe extraction failed after 3 attempts due to {last_err}. "
            f"Output safely degraded to deterministic fixture ({fallback_reason})."
        )
        logger.error(warning_msg)
        self.last_provider_used = fallback_reason
        self.last_fallback_warning = warning_msg
        return self.fallback_stub.extract_vibe_from_images(images, text_description)

    def generate_theme_proposal(
        self, style_profile: dict[str, Any], event_details: dict[str, Any]
    ) -> ThemeGenerationPayloadSchema:
        if not self.api_key:
            logger.warning(
                "No GEMINI_API_KEY provided; falling back to deterministic stub for theme generation."
            )
            self.last_provider_used = "deterministic_stub"
            return self.fallback_stub.generate_theme_proposal(style_profile, event_details)

        prompt = (
            "You are an expert Indian wedding and cultural event creative director and theme designer.\n"
            "Based on the extracted style profile and event parameters, design a comprehensive, cohesive theme.\n\n"
            f"Event Parameters:\n"
            f"- Event Type: {event_details.get('event_type', 'Wedding')}\n"
            f"- City: {event_details.get('city', 'Jaipur')}\n"
            f"- Guest Count: {event_details.get('guest_count', 250)}\n"
            f"- Total Budget: ₹{event_details.get('total_budget', 1500000):,.2f}\n"
            f"- Extracted Dominant Palette: {style_profile.get('extracted_palette', [])}\n"
            f"- Style Tags: {style_profile.get('style_tags', [])}\n"
            f"- Mood Keywords: {style_profile.get('mood_words', [])}\n"
            f"- User Vision Notes: {style_profile.get('text_description') or 'None'}\n\n"
            "CRITICAL RULES:\n"
            "1. ZERO LLM MATH: Do NOT compute rupee amounts or multiply quantities. Only specify the formula string and cost_tier.\n"
            "2. Return AT LEAST 10 distinct, culturally rich decor items covering:\n"
            "   - stage_backdrop (formula: '1 fixed')\n"
            "   - mandap (formula: '1 fixed')\n"
            "   - entrance_arch (formula: '2 units' or '1 fixed')\n"
            "   - table_centerpiece (formula: '1 per table')\n"
            "   - lighting (formula: '1 per 10 guests')\n"
            "   - ceiling_drapes (formula: '1 fixed')\n"
            "   - photobooth (formula: '1 fixed')\n"
            "   - seating_lounges (formula: '1 per 25 guests')\n"
            "   - cultural_performance (formula: '1 fixed', e.g. traditional welcome nagada/shehnai troupe or welcome folk dancers)\n"
            "   - default/accents (formulas: '1 fixed', '1 per 15 guests', etc. for physical displays, torans, petal carpets)\n"
            "   CATEGORY RULES: Live musical acts or welcome performers MUST be categorized as 'cultural_performance' (not 'default'). Full-venue overhead rigging/fabric treatments MUST be categorized as 'ceiling_drapes' (not 'default').\n"
            "3. cost_tier must be strictly 'low', 'medium', or 'high'.\n"
            "4. sourcing_type must be strictly 'rent', 'diy', or 'buy'.\n"
            "5. Return strictly valid JSON matching this schema:\n"
            "{\n"
            '  "theme_name": "string",\n'
            '  "palette": ["#...", "#...", "#...", "#...", "#..."],\n'
            '  "menu_direction": "string",\n'
            '  "playlist_genres": ["genre 1", "genre 2", "genre 3"],\n'
            '  "dress_code_suggestion": "string",\n'
            '  "invitation_design_brief": "string",\n'
            '  "decor_items": [\n'
            "    {\n"
            '      "category": "stage_backdrop | entrance_arch | table_centerpiece | lighting | photobooth | seating_lounges | mandap | ceiling_drapes | cultural_performance | default",\n'
            '      "name": "item title",\n'
            '      "quantity_formula": "1 fixed | 1 per table | 1 per 10 guests | 2 units",\n'
            '      "cost_tier": "low | medium | high",\n'
            '      "sourcing_type": "rent | diy | buy",\n'
            '      "reasoning": {"aesthetic": "brief reason"}\n'
            "    }\n"
            "  ]\n"
            "}"
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.2},
        }

        attempts = 0
        last_err = None
        while attempts < 3:
            attempts += 1
            try:
                with httpx.Client(timeout=45.0) as client:
                    resp = client.post(f"{GEMINI_API_URL}?key={self.api_key}", json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    res_parts = data["candidates"][0]["content"]["parts"]
                    text = "".join(p.get("text", "") for p in res_parts).strip()
                    text = text.removeprefix("```json")
                    text = text.removeprefix("```")
                    text = text.removesuffix("```")
                    parsed = json.loads(text.strip())
                    validated = ThemeGenerationPayloadSchema.model_validate(parsed)
                    if len(validated.decor_items) >= 10:
                        self.last_provider_used = "gemini-3-flash-preview"
                        self.last_fallback_warning = None
                        return validated
                    else:
                        logger.warning(
                            f"Gemini returned only {len(validated.decor_items)} decor items (< 10). Retrying..."
                        )
            except (
                httpx.HTTPError,
                KeyError,
                IndexError,
                json.JSONDecodeError,
                ValidationError,
                TypeError,
                ValueError,
            ) as e:
                last_err = e
                is_429 = "429" in str(e) or (
                    hasattr(e, "response") and getattr(e.response, "status_code", None) == 429
                )
                logger.error(
                    f"CRITICAL: Gemini theme generation attempt {attempts} failed with {type(e).__name__}: {e}. "
                    f"Quota exhausted: {is_429}."
                )
                if attempts < 3:
                    time.sleep(2.0 * attempts)

        fallback_reason = (
            "stub_fallback_quota_exhausted (HTTP 429)"
            if ("429" in str(last_err))
            else f"stub_fallback_error ({type(last_err).__name__})"
        )
        warning_msg = (
            f"LOUD ALERT: Live LLM theme generation failed after 3 attempts due to {last_err}. "
            f"Output safely degraded to deterministic fixture ({fallback_reason})."
        )
        logger.error(warning_msg)
        self.last_provider_used = fallback_reason
        self.last_fallback_warning = warning_msg
        return self.fallback_stub.generate_theme_proposal(style_profile, event_details)
