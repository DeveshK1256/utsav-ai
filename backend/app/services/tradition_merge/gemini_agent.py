import json
import logging
from datetime import date

import google.generativeai as genai
from pydantic import ValidationError

from backend.app.models.models import Tradition
from backend.app.services.tradition_merge.schemas import (
    MergedRunOfShowSchema,
)
from backend.app.services.tradition_merge.stub_agent import (
    BaseTraditionMergeAgent,
    DeterministicStubTraditionMergeAgent,
)

logger = logging.getLogger(__name__)


class GeminiTraditionMergeAgent(BaseTraditionMergeAgent):
    """
    GenAI-powered cultural merge agent using Gemini.
    Synthesizes custom harmonized schedules while validating strictly against MergedRunOfShowSchema.
    Falls back gracefully to DeterministicStubTraditionMergeAgent on error.
    """

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.stub_fallback = DeterministicStubTraditionMergeAgent()

    def generate_merged_run_of_show(
        self, primary: Tradition, secondary: Tradition, start_date: date, notes: str | None = None
    ) -> MergedRunOfShowSchema:
        try:
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel("gemini-2.0-flash")

            prompt = f"""
You are Utsav's Senior Cultural & Ritual Intelligence Agent.
Synthesize a harmonious, respectful cross-cultural wedding run-of-show merging two Indian
traditions:
1. Primary Tradition: {primary.regional_name} ({primary.description})
2. Secondary Tradition: {secondary.regional_name} ({secondary.description})
Event Start Date: {start_date.isoformat()}
Additional Family Context: {notes or "None"}

RULES:
1. Merge the ceremonies chronologically into a 2-day or 3-day timeline.
2. For EVERY ceremony, explicitly specify 'origin_tradition' as either '{primary.regional_name}',
   '{secondary.regional_name}', or 'Shared / Combined'.
3. Highlight potential cultural friction points (e.g. food, attire, ritual sequence) and
   provide respectful recommendations in 'family_alignment_points'.
4. Respond ONLY with valid JSON conforming to the schema below.

JSON SCHEMA:
{{
  "fusion_title": "string",
  "primary_tradition": "{primary.regional_name}",
  "secondary_tradition": "{secondary.regional_name}",
  "ceremonies": [
    {{
      "name": "string",
      "origin_tradition": "string",
      "day_offset": 0,
      "start_time": "HH:MM",
      "duration_hours": 2.5,
      "venue_type": "string",
      "is_outdoor": false,
      "is_muhurat_locked": false,
      "cultural_significance": "string",
      "family_guidance": "string"
    }}
  ],
  "family_alignment_points": [
    {{
      "issue": "string",
      "description": "string",
      "recommendation": "string"
    }}
  ],
  "disclaimer": "AI-drafted baseline sequence based on general cultural customs.\n"
                "Review with community priest before finalizing."
}}
"""
            response = model.generate_content(
                prompt, generation_config={"response_mime_type": "application/json"}
            )
            raw_text = response.text
            parsed = json.loads(raw_text)
            if "content_accuracy_disclaimer" not in parsed:
                parsed["content_accuracy_disclaimer"] = (
                    f"This sequence was AI-drafted as a starting point based on general "
                    f"knowledge of {primary.regional_name} and {secondary.regional_name} customs. "
                    "It has not been reviewed by a priest or community elder and may contain "
                    "errors, omissions, or regionally inappropriate details. "
                    "Please review carefully with your family and officiant before finalizing."
                )
            if "timing_disclaimer" not in parsed:
                parsed["timing_disclaimer"] = (
                    "Panchang calculations are astronomical estimates based on Drik Ganita and "
                    "Ephemeris models. Muhurat dates and ritual sequences must always be confirmed "
                    "with your family's trusted priest, pandit, or religious officiant."
                )
            return MergedRunOfShowSchema(**parsed)
        except (
            ValueError,
            KeyError,
            json.JSONDecodeError,
            TypeError,
            ValidationError,
            RuntimeError,
            OSError,
            AttributeError,
        ) as e:
            logger.warning(
                "Gemini multi-tradition merge agent failed, using deterministic stub fallback: %s",
                e,
            )
            return self.stub_fallback.generate_merged_run_of_show(
                primary, secondary, start_date, notes
            )
