"""
Invitation Text Composer Agent (F16 - Section 8.4, Agent #12).
Composes short, culturally resonant wording variants strictly from structured event inputs.
Never invents facts (dates, venues, ceremonies) not present in the data.
Provides a deterministic offline fallback stub when Gemini is unavailable.
"""

import json
import logging
import os

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class WordingVariant(BaseModel):
    id: str = Field(..., description="Variant identifier: traditional, contemporary, or formal")
    title: str = Field(..., description="Human-friendly variant label")
    body_text: str = Field(..., description="The invitation wording body")
    tone: str = Field(..., description="Tone description, e.g. Warm Traditional, Modern Joyful")


class InvitationWordingResponse(BaseModel):
    variants: list[WordingVariant]
    provider_used: str = Field("stub", description="gemini or stub")
    fallback_warning: str | None = None
    content_review_note: str = (
        "Ceremony details and wording are AI-assisted starting baselines; "
        "please verify with your family and elders before printing."
    )


class InvitationWordingAgent:
    """
    Produces 2-3 culturally warm wording options from confirmed event data.
    Guarantees zero invented details and provides deterministic fallback.
    """

    @classmethod
    def compose_wording(
        cls,
        event_name: str,
        host_name: str | None,
        event_type: str,
        date_str: str,
        venue_str: str | None,
        muhurat_time: str | None = None,
        ceremony_names: list[str] | None = None,
        design_brief: str | None = None,
    ) -> InvitationWordingResponse:
        # Check for Gemini API key
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

        if gemini_key:
            try:
                return cls._call_gemini(
                    gemini_key=gemini_key,
                    event_name=event_name,
                    host_name=host_name,
                    event_type=event_type,
                    date_str=date_str,
                    venue_str=venue_str,
                    muhurat_time=muhurat_time,
                    ceremony_names=ceremony_names,
                    design_brief=design_brief,
                )
            except (
                httpx.HTTPError,
                ValueError,
                KeyError,
                json.JSONDecodeError,
                RuntimeError,
                TypeError,
                OSError,
            ) as exc:
                logger.warning(
                    "Gemini invitation wording generation failed, invoking deterministic stub: %s",
                    exc,
                )
                stub_resp = cls._deterministic_fallback(
                    event_name=event_name,
                    host_name=host_name,
                    event_type=event_type,
                    date_str=date_str,
                    venue_str=venue_str,
                    muhurat_time=muhurat_time,
                    ceremony_names=ceremony_names,
                )
                stub_resp.fallback_warning = (
                    f"Live LLM composer unavailable ({exc}); deterministic template active."
                )
                return stub_resp

        return cls._deterministic_fallback(
            event_name=event_name,
            host_name=host_name,
            event_type=event_type,
            date_str=date_str,
            venue_str=venue_str,
            muhurat_time=muhurat_time,
            ceremony_names=ceremony_names,
        )

    @classmethod
    def _deterministic_fallback(
        cls,
        event_name: str,
        host_name: str | None,
        event_type: str,
        date_str: str,
        venue_str: str | None,
        muhurat_time: str | None = None,
        ceremony_names: list[str] | None = None,
    ) -> InvitationWordingResponse:
        """Deterministic non-LLM template options conforming strictly to facts."""
        clean_event = event_name.strip() or "Celebration"
        clean_date = date_str.strip() or "Date to be confirmed"
        clean_venue = venue_str.strip() if venue_str else "Venue to be confirmed"
        if host_name:
            host_intro = (
                f"The {host_name}" if "family" in host_name.lower() else f"The {host_name} family"
            )
        else:
            host_intro = "We"

        ceremony_clause = ""
        if ceremony_names and len(ceremony_names) > 0:
            ceremony_clause = f" Join us for {', '.join(ceremony_names[:3])}."

        muhurat_clause = f" (Auspicious Muhurat: {muhurat_time})" if muhurat_time else ""

        # Variant 1: Traditional & Warm
        v1_text = (
            f"With the blessings of our elders and the Divine, {host_intro} warmly invite you and your family "
            f"to celebrate the auspicious occasion of {clean_event} on {clean_date}{muhurat_clause} at {clean_venue}.{ceremony_clause} "
            f"Your gracious presence and blessings will bring great joy to our celebration."
        )

        # Variant 2: Modern & Celebratory
        v2_text = (
            f"Joy, love, and cherished beginnings! You are cordially invited to celebrate {clean_event} "
            f"with us on {clean_date} at {clean_venue}.{ceremony_clause} "
            f"Please join us in making this milestone truly unforgettable."
        )

        # Variant 3: Formal & Classic
        v3_text = (
            f"{host_intro} request the pleasure of your company at the celebration of {clean_event} "
            f"on {clean_date} at {clean_venue}.{muhurat_clause} "
            f"Festivities and dinner will follow the ceremony."
        )

        return InvitationWordingResponse(
            variants=[
                WordingVariant(
                    id="traditional",
                    title="Traditional & Auspicious",
                    body_text=v1_text,
                    tone="Warm, respectful, blessings-focused",
                ),
                WordingVariant(
                    id="contemporary",
                    title="Contemporary & Celebratory",
                    body_text=v2_text,
                    tone="Joyful, modern, welcoming",
                ),
                WordingVariant(
                    id="formal",
                    title="Formal & Elegant",
                    body_text=v3_text,
                    tone="Classic, formal, refined",
                ),
            ],
            provider_used="stub",
            fallback_warning=None,
        )

    @classmethod
    def _call_gemini(
        cls,
        gemini_key: str,
        event_name: str,
        host_name: str | None,
        event_type: str,
        date_str: str,
        venue_str: str | None,
        muhurat_time: str | None,
        ceremony_names: list[str] | None,
        design_brief: str | None,
    ) -> InvitationWordingResponse:
        import httpx

        prompt = f"""
You are the Utsav Invitation Text Composer Agent.
Write 3 distinct, culturally resonant invitation wording options for an Indian {event_type} celebration.

STRICT INVENTED-FACTS POLICY:
- Use ONLY the confirmed details provided below.
- Do NOT invent or assume venue addresses, dates, or ceremonies not listed.
- No placeholder tags like {{name}} or [date] in output.

EVENT DATA:
- Event Name: {event_name}
- Host: {host_name or "The Family"}
- Date: {date_str}
- Venue: {venue_str or "Venue to be confirmed"}
- Auspicious Muhurat: {muhurat_time or "None"}
- Ceremonies: {", ".join(ceremony_names) if ceremony_names else "Standard"}
- Aesthetic Brief: {design_brief or "Elegant Indian celebration"}

OUTPUT JSON FORMAT ONLY:
{{
  "variants": [
    {{
      "id": "traditional",
      "title": "Traditional & Auspicious",
      "body_text": "...",
      "tone": "Warm Traditional"
    }},
    {{
      "id": "contemporary",
      "title": "Contemporary & Joyful",
      "body_text": "...",
      "tone": "Modern Celebratory"
    }},
    {{
      "id": "formal",
      "title": "Formal & Elegant",
      "body_text": "...",
      "tone": "Classic Formal"
    }}
  ]
}}
"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4, "responseMimeType": "application/json"},
        }

        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw_text)

            variants = [
                WordingVariant(
                    id=v.get("id", f"v_{idx}"),
                    title=v.get("title", f"Option {idx + 1}"),
                    body_text=v.get("body_text", ""),
                    tone=v.get("tone", "Celebratory"),
                )
                for idx, v in enumerate(parsed.get("variants", []))
            ]

            if not variants:
                raise ValueError("Empty variants from Gemini")

            return InvitationWordingResponse(
                variants=variants, provider_used="gemini", fallback_warning=None
            )
