"""
Multi-Tradition Merge Agent (F2 Cultural & Ritual Intelligence).
Combines two distinct cultural traditions (e.g. Maharashtrian x Punjabi, Tamil x Punjabi)
into a unified itinerary and reconciled samagri checklist.
Cites origin tradition per ceremony, validates against strict Pydantic schemas,
and implements the Gemini + deterministic fallback pattern.
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import date
from typing import Any, ClassVar

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from backend.app.models.models import RitualItem, Tradition
from backend.app.services.dag_scheduler import DAGScheduler

logger = logging.getLogger(__name__)


# Pydantic Schemas for Schema Validation
class CeremonyItemSchema(BaseModel):
    name: str = Field(..., description="Ceremony name")
    origin_tradition: str = Field(..., description="Origin cultural lineage or 'Shared / Combined'")
    day_offset: int = Field(0, description="Day offset (0, 1, 2) from event start")
    start_time: str = Field(..., description="Time string HH:MM")
    duration_hours: float = Field(..., description="Duration in hours")
    venue_type: str = Field(..., description="Recommended venue setting")
    is_outdoor: bool = Field(False, description="Whether event is outdoor")
    is_muhurat_locked: bool = Field(
        False, description="Whether ceremony requires auspicious timing"
    )
    cultural_significance: str = Field(..., description="Cultural meaning and purpose")
    family_guidance: str | None = Field(None, description="Actionable elder alignment note")


CEREMONY_CONTENT_ACCURACY_DISCLAIMER = (
    "This sequence was AI-drafted as a starting point based on general knowledge of customs. "
    "It has not been reviewed by a priest or community elder and may contain errors, omissions, or "
    "regionally inappropriate details. Please review carefully with your family and officiant before finalizing."
)


class FamilyAlignmentPointSchema(BaseModel):
    issue: str
    description: str
    recommendation: str


class MergedRunOfShowSchema(BaseModel):
    fusion_title: str
    primary_tradition: str
    secondary_tradition: str
    ceremonies: list[CeremonyItemSchema]
    family_alignment_points: list[FamilyAlignmentPointSchema]
    content_accuracy_disclaimer: str = Field(default=CEREMONY_CONTENT_ACCURACY_DISCLAIMER)
    timing_disclaimer: str = Field(
        default="Panchang calculations are astronomical estimates based on Drik Ganita and Ephemeris models. Muhurat dates and ritual sequences must always be confirmed with your family's trusted priest, pandit, or religious officiant."
    )
    disclaimer: str = Field(default=CEREMONY_CONTENT_ACCURACY_DISCLAIMER)


class BaseTraditionMergeAgent(ABC):
    """Abstract agent interface for multi-tradition merge synthesis."""

    @abstractmethod
    def generate_merged_run_of_show(
        self, primary: Tradition, secondary: Tradition, start_date: date, notes: str | None = None
    ) -> MergedRunOfShowSchema:
        pass


class DeterministicStubTraditionMergeAgent(BaseTraditionMergeAgent):
    """
    Deterministic rule-based reconciler.
    Guarantees 100% reproducible fixtures, offline resilience, and exact acceptance criteria.
    """

    def generate_merged_run_of_show(
        self, primary: Tradition, secondary: Tradition, start_date: date, notes: str | None = None
    ) -> MergedRunOfShowSchema:
        p_code = primary.code.lower()
        s_code = secondary.code.lower()
        pair_set = {p_code, s_code}

        ceremonies: list[CeremonyItemSchema] = []
        alignment_points: list[FamilyAlignmentPointSchema] = []

        # 1. Spec Acceptance Case: Maharashtrian x Punjabi
        if any("maharashtrian" in c for c in pair_set) and any("punjabi" in c for c in pair_set):
            title = f"{primary.regional_name} × {secondary.regional_name} Fusion Vivah"
            maha_name = (
                primary.regional_name if "maharashtrian" in p_code else secondary.regional_name
            )
            punj_name = primary.regional_name if "punjabi" in p_code else secondary.regional_name

            ceremonies = [
                CeremonyItemSchema(
                    name="Combined Haldi, Maiyan & Vatna Ceremony",
                    origin_tradition="Shared / Combined",
                    day_offset=0,
                    start_time="15:00",
                    duration_hours=3.0,
                    venue_type="Courtyard / Floral Lawn",
                    is_outdoor=True,
                    is_muhurat_locked=False,
                    cultural_significance="Joint application of turmeric (Vatna/Halad) by loved ones from both families for purification and radiant blessings.",
                    family_guidance="Families can apply ubtan in alternating turns to folk dholak songs and Marathi lagna geet.",
                ),
                CeremonyItemSchema(
                    name="Lively Jaggo Night & Sangeet Celebration",
                    origin_tradition=punj_name,
                    day_offset=0,
                    start_time="19:00",
                    duration_hours=5.0,
                    venue_type="Grand Ballroom",
                    is_outdoor=False,
                    is_muhurat_locked=False,
                    cultural_significance="Nocturnal celebratory procession carrying the illuminated Jaggo brass pot, followed by high-energy Bhangra and musical performances.",
                    family_guidance="Maharashtrian family joins in carrying the Jaggo pot with sisters and maternal aunts.",
                ),
                CeremonyItemSchema(
                    name="Chooda Ceremony & Milni Welcome",
                    origin_tradition=punj_name,
                    day_offset=1,
                    start_time="09:00",
                    duration_hours=1.5,
                    venue_type="Promenade Gateway",
                    is_outdoor=True,
                    is_muhurat_locked=False,
                    cultural_significance="Maternal uncles bless bride with ivory red Chooda and Kalire; male counterparts of both lineages embrace during Milni with stoles and garlands.",
                    family_guidance="Allocate 5 pairs of counterparts (fathers, brothers, maternal uncles) for the Milni exchange.",
                ),
                CeremonyItemSchema(
                    name="Simant Pujan & Antarpat Vivah Muhurat",
                    origin_tradition=maha_name,
                    day_offset=1,
                    start_time="10:30",
                    duration_hours=2.0,
                    venue_type="Sacred Mandap Hall",
                    is_outdoor=False,
                    is_muhurat_locked=True,
                    cultural_significance="Simant Pujan welcoming of groom by bride's mother; silk Antarpat held between couple until Mangalashtaka verses culminate at exact Muhurat.",
                    family_guidance="Bride enters under Punjabi floral Phoolon Ki Chaadar, then halts behind the sacred Antarpat cloth.",
                ),
                CeremonyItemSchema(
                    name="Saptapadi & 4 Laavan Circumambulation",
                    origin_tradition="Shared / Combined",
                    day_offset=1,
                    start_time="12:30",
                    duration_hours=2.0,
                    venue_type="Central Vivah Mandap",
                    is_outdoor=False,
                    is_muhurat_locked=True,
                    cultural_significance="Harmonization of Vedic 7 steps (Saptapadi) around the sacred Vivah fire with the spiritual teachings of 4 Laavan / Pheras.",
                    family_guidance="Priests from both traditions coordinate the mantras: Maharashtrian Pandit leads Saptapadi vows, Punjabi elder reads the Laavan.",
                ),
                CeremonyItemSchema(
                    name="Grand Royal Fusion Reception & Banquet",
                    origin_tradition="Shared / Combined",
                    day_offset=1,
                    start_time="19:30",
                    duration_hours=4.5,
                    venue_type="Imperial Lawn & Ballroom",
                    is_outdoor=True,
                    is_muhurat_locked=False,
                    cultural_significance="Celebratory banquet honoring both heritages with multi-regional dining, toasts, and music.",
                    family_guidance="Bride transitions from morning Paithani saree to bridal evening lehenga.",
                ),
            ]

            alignment_points = [
                FamilyAlignmentPointSchema(
                    issue="Bridal Entrance Harmony (Phoolon Ki Chaadar vs. Antarpat)",
                    description="Punjabi custom requires bride to enter under a floral canopy held by brothers. Maharashtrian custom requires groom and bride separated by the Antarpat cloth.",
                    recommendation="Brothers escort bride to Mandap threshold under Phoolon Ki Chaadar; once at Mandap, uncles raise the Antarpat cloth until the Mangalashtaka shloka.",
                ),
                FamilyAlignmentPointSchema(
                    issue="Dining Transitions & Cultural Cuisines",
                    description="Maharashtrian traditional wedding lunch is traditionally pure satvik vegetarian served on banana leaves. Punjabi evening revelry often calls for rich Mughlai curries.",
                    recommendation="Host a traditional satvik vegetarian seated feast for post-pheras lunch (Pankat style); offer lavish multi-cuisine counters at the evening reception.",
                ),
                FamilyAlignmentPointSchema(
                    issue="Wardrobe and Adornment Changes",
                    description="Maharashtrian bride wears Mundavalya forehead pearls with yellow/green Paithani saree; Punjabi wedding emphasizes red Chooda bangles and hanging Kalire.",
                    recommendation="Bride wears both Chooda and Mundavalya during the morning ceremony, celebrating both her maternal lineage and new marital home.",
                ),
            ]

        else:
            # Generic dual-tradition interweaving
            title = f"{primary.regional_name} × {secondary.regional_name} Cultural Fusion"
            t_primary_subevents = DAGScheduler.SUB_EVENT_TEMPLATES.get(
                p_code, DAGScheduler.SUB_EVENT_TEMPLATES["default"]
            )
            t_sec_subevents = DAGScheduler.SUB_EVENT_TEMPLATES.get(
                s_code, DAGScheduler.SUB_EVENT_TEMPLATES["default"]
            )

            for _idx, se in enumerate(t_primary_subevents):
                ceremonies.append(
                    CeremonyItemSchema(
                        name=str(se["name"]),
                        origin_tradition=primary.regional_name,
                        day_offset=int(str(se.get("day_offset", 0))),
                        start_time=f"{int(str(se.get('start_time_hour', 10))):02d}:00",
                        duration_hours=float(str(se.get("duration_hours", 3))),
                        venue_type=str(se.get("venue_type", "Main Celebration Hall")),
                        is_outdoor=bool(se.get("is_outdoor", False)),
                        is_muhurat_locked=bool(se.get("is_muhurat_locked", False)),
                        cultural_significance=f"Traditional rites of {primary.regional_name}.",
                        family_guidance=None,
                    )
                )

            for _idx, se in enumerate(t_sec_subevents):
                if not any(c.name == str(se["name"]) for c in ceremonies):
                    ceremonies.append(
                        CeremonyItemSchema(
                            name=str(se["name"]),
                            origin_tradition=secondary.regional_name,
                            day_offset=int(str(se.get("day_offset", 0))),
                            start_time=f"{int(str(se.get('start_time_hour', 14))):02d}:00",
                            duration_hours=float(str(se.get("duration_hours", 3))),
                            venue_type=str(se.get("venue_type", "Celebration Venue")),
                            is_outdoor=bool(se.get("is_outdoor", False)),
                            is_muhurat_locked=bool(se.get("is_muhurat_locked", False)),
                            cultural_significance=f"Sacred custom of {secondary.regional_name}.",
                            family_guidance=None,
                        )
                    )

            ceremonies.sort(key=lambda c: (c.day_offset, c.start_time))

            alignment_points = [
                FamilyAlignmentPointSchema(
                    issue="Priest and Protocol Coordination",
                    description=f"Officiating priests from {primary.regional_name} and {secondary.regional_name} should coordinate vow sequencing.",
                    recommendation="Convene a 30-minute joint briefing with both priests 14 days before the ceremony.",
                ),
                FamilyAlignmentPointSchema(
                    issue="Cultural Attire Coordination",
                    description="Coordinate wedding attire styling to honor both backgrounds.",
                    recommendation="Allocate a 90-minute dress change window between rituals.",
                ),
            ]

        custom_accuracy_disclaimer = (
            f"This sequence was AI-drafted as a starting point based on general knowledge of {primary.regional_name} and {secondary.regional_name} customs. "
            f"It has not been reviewed by a priest or community elder and may contain errors, omissions, or "
            f"regionally inappropriate details. Please review carefully with your family and officiant before finalizing."
        )

        return MergedRunOfShowSchema(
            fusion_title=title,
            primary_tradition=primary.regional_name,
            secondary_tradition=secondary.regional_name,
            ceremonies=ceremonies,
            family_alignment_points=alignment_points,
            content_accuracy_disclaimer=custom_accuracy_disclaimer,
            timing_disclaimer="Panchang calculations are astronomical estimates based on Drik Ganita and Ephemeris models. Muhurat dates and ritual sequences must always be confirmed with your family's trusted priest, pandit, or religious officiant.",
            disclaimer=custom_accuracy_disclaimer,
        )


class GeminiTraditionMergeAgent(BaseTraditionMergeAgent):
    """
    GenAI-powered cultural merge agent using Gemini.
    Synthesizes custom harmonized schedules while validating strictly against MergedRunOfShowSchema.
    Falls back gracefully to DeterministicStubTraditionMergeAgent on error.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.stub_fallback = DeterministicStubTraditionMergeAgent()

    def generate_merged_run_of_show(
        self, primary: Tradition, secondary: Tradition, start_date: date, notes: str | None = None
    ) -> MergedRunOfShowSchema:
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel("gemini-2.0-flash")

            prompt = f"""
You are Utsav's Senior Cultural & Ritual Intelligence Agent.
Synthesize a harmonious, respectful cross-cultural wedding run-of-show merging two Indian traditions:
1. Primary Tradition: {primary.regional_name} ({primary.description})
2. Secondary Tradition: {secondary.regional_name} ({secondary.description})
Event Start Date: {start_date.isoformat()}
Additional Family Context: {notes or "None"}

RULES:
1. Merge the ceremonies chronologically into a 2-day or 3-day timeline.
2. For EVERY ceremony, explicitly specify 'origin_tradition' as either '{primary.regional_name}', '{secondary.regional_name}', or 'Shared / Combined'.
3. Highlight potential cultural friction points (e.g. food, attire, ritual sequence) and provide respectful recommendations in 'family_alignment_points'.
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
  "disclaimer": "This sequence was AI-drafted as a starting point based on general knowledge of customs. It has not been reviewed by a priest or community elder and may contain errors, omissions, or regionally inappropriate details. Please review carefully with your family and officiant before finalizing."
}}
"""
            response = model.generate_content(
                prompt, generation_config={"response_mime_type": "application/json"}
            )
            raw_text = response.text
            parsed = json.loads(raw_text)
            if "content_accuracy_disclaimer" not in parsed:
                parsed["content_accuracy_disclaimer"] = (
                    f"This sequence was AI-drafted as a starting point based on general knowledge of {primary.regional_name} and {secondary.regional_name} customs. "
                    "It has not been reviewed by a priest or community elder and may contain errors, omissions, or regionally inappropriate details. "
                    "Please review carefully with your family and officiant before finalizing."
                )
            if "timing_disclaimer" not in parsed:
                parsed["timing_disclaimer"] = (
                    "Panchang calculations are astronomical estimates based on Drik Ganita and Ephemeris models. "
                    "Muhurat dates and ritual sequences must always be confirmed with your family's trusted priest, pandit, or religious officiant."
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


def get_tradition_merge_agent() -> BaseTraditionMergeAgent:
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        return GeminiTraditionMergeAgent(api_key=gemini_key)
    return DeterministicStubTraditionMergeAgent()


class TraditionMergeService:
    """
    Reconciles two distinct cultural traditions into an integrated schedule and samagri list.
    Enforces deterministic deduplication and source attribution.
    """

    SHARED_KEYWORDS: ClassVar[dict[str, tuple[str, str, str]]] = {
        "ghee": ("Pure Cow Ghee", "puja_samagri", "Oblations into sacred Agni for Vivah Homam"),
        "akshata": (
            "Sacred Akshata Rice",
            "puja_samagri",
            "Elder blessings showered over couple during vows",
        ),
        "rice": (
            "Sacred Akshata Rice",
            "puja_samagri",
            "Elder blessings showered over couple during vows",
        ),
        "coconut": (
            "Shriphal (Auspicious Coconuts)",
            "offerings",
            "Sacred offerings to Varuna and divine witnesses",
        ),
        "supari": (
            "Betel Nuts (Supari)",
            "offerings",
            "Invocation of Lord Ganesha and planetary deities",
        ),
        "betel": ("Betel Leaves & Nuts", "offerings", "Auspicious welcome and invocation"),
        "haldi": (
            "Raw Turmeric (Haldi)",
            "cleansing_pastes",
            "Auspicious purification for bride and groom",
        ),
        "turmeric": (
            "Raw Turmeric (Haldi)",
            "cleansing_pastes",
            "Auspicious purification for bride and groom",
        ),
        "sindoor": (
            "Sacred Sindoor / Kumkum",
            "sacred_ornaments",
            "Marital sanctity applied in parting hair",
        ),
        "kumkum": (
            "Sacred Sindoor / Kumkum",
            "sacred_ornaments",
            "Auspicious tilak and invocation",
        ),
    }

    def __init__(self, db: Session):
        self.db = db
        self.agent = get_tradition_merge_agent()

    def get_tradition(self, code: str) -> Tradition | None:
        return self.db.query(Tradition).filter(Tradition.code == code).first()

    def merge_traditions(
        self,
        primary_code: str,
        secondary_code: str,
        start_date: date | None = None,
        event_name: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """
        Executes a dual-tradition merge.
        Returns unified run-of-show with origin labels, reconciled samagri with provenance, and alignment checklist.
        """
        primary = self.get_tradition(primary_code)
        secondary = self.get_tradition(secondary_code)

        if not primary or not secondary:
            raise ValueError(
                f"Invalid tradition codes: primary={primary_code}, secondary={secondary_code}"
            )

        event_start = start_date or date.today()

        # Generate run of show via LLM / Fallback Agent
        run_of_show = self.agent.generate_merged_run_of_show(
            primary=primary, secondary=secondary, start_date=event_start, notes=notes
        )

        # Reconcile samagri items with provenance tracking
        primary_items = (
            self.db.query(RitualItem).filter(RitualItem.tradition_code == primary_code).all()
        )
        secondary_items = (
            self.db.query(RitualItem).filter(RitualItem.tradition_code == secondary_code).all()
        )

        reconciled_items = []
        shared_lookup = {}

        for item in primary_items:
            category_key = self._detect_shared_key(item.item_name)
            if category_key and category_key not in shared_lookup:
                shared_lookup[category_key] = {
                    "item_name": item.item_name,
                    "regional_name": f"{item.regional_name or item.item_name}",
                    "standard_quantity": item.standard_quantity,
                    "category": item.category,
                    "spiritual_purpose": item.spiritual_purpose,
                    "source_tradition": "Shared Vedic / Common",
                    "ritual_name": f"{item.ritual_name or 'Sacred Rites'}",
                    "is_verified": item.is_verified and primary.is_verified,
                    "provenance": [primary.regional_name],
                }
            else:
                reconciled_items.append(
                    {
                        "item_name": item.item_name,
                        "regional_name": item.regional_name,
                        "standard_quantity": item.standard_quantity,
                        "category": item.category,
                        "spiritual_purpose": item.spiritual_purpose,
                        "source_tradition": primary.regional_name,
                        "ritual_name": item.ritual_name,
                        "is_verified": item.is_verified and primary.is_verified,
                        "provenance": [primary.regional_name],
                    }
                )

        for item in secondary_items:
            category_key = self._detect_shared_key(item.item_name)
            if category_key and category_key in shared_lookup:
                shared_entry = shared_lookup[category_key]
                shared_entry["provenance"].append(secondary.regional_name)
                shared_entry["regional_name"] += f" / {item.regional_name or item.item_name}"
                shared_entry["standard_quantity"] = (
                    f"{shared_entry['standard_quantity']} (combined envelope)"
                )
                shared_entry["is_verified"] = shared_entry["is_verified"] and item.is_verified
            elif category_key and category_key not in shared_lookup:
                shared_lookup[category_key] = {
                    "item_name": item.item_name,
                    "regional_name": f"{item.regional_name or item.item_name}",
                    "standard_quantity": item.standard_quantity,
                    "category": item.category,
                    "spiritual_purpose": item.spiritual_purpose,
                    "source_tradition": "Shared Vedic / Common",
                    "ritual_name": f"{item.ritual_name or 'Sacred Rites'}",
                    "is_verified": item.is_verified and secondary.is_verified,
                    "provenance": [secondary.regional_name],
                }
            else:
                reconciled_items.append(
                    {
                        "item_name": item.item_name,
                        "regional_name": item.regional_name,
                        "standard_quantity": item.standard_quantity,
                        "category": item.category,
                        "spiritual_purpose": item.spiritual_purpose,
                        "source_tradition": secondary.regional_name,
                        "ritual_name": item.ritual_name,
                        "is_verified": item.is_verified and secondary.is_verified,
                        "provenance": [secondary.regional_name],
                    }
                )

        final_samagri = list(shared_lookup.values()) + reconciled_items

        return {
            "status": "success",
            "event_name": event_name,
            "fusion_title": run_of_show.fusion_title,
            "primary_tradition": {
                "code": primary.code,
                "name": primary.regional_name,
                "is_verified": primary.is_verified,
                "verification_source": primary.verification_source,
            },
            "secondary_tradition": {
                "code": secondary.code,
                "name": secondary.regional_name,
                "is_verified": secondary.is_verified,
                "verification_source": secondary.verification_source,
            },
            "run_of_show": [c.model_dump() for c in run_of_show.ceremonies],
            "reconciled_samagri_summary": {
                "total_unique_items": len(final_samagri),
                "shared_common_items_count": len(shared_lookup),
                "primary_specific_count": len(
                    [i for i in final_samagri if i["source_tradition"] == primary.regional_name]
                ),
                "secondary_specific_count": len(
                    [i for i in final_samagri if i["source_tradition"] == secondary.regional_name]
                ),
            },
            "samagri_items": final_samagri,
            "family_alignment_points": [
                p.model_dump() for p in run_of_show.family_alignment_points
            ],
            "priest_coordination_note": (
                f"Both traditions have been reconciled into a single ceremonial guide. "
                f"Priests from both sides ({primary.regional_name} and {secondary.regional_name}) "
                f"should review the flagged alignment points together 2 weeks before the ceremony."
            ),
            "content_accuracy_disclaimer": (
                f"This ceremonial sequence and ritual items list were AI-drafted as a starting point based on general cultural knowledge of "
                f"{primary.regional_name} and {secondary.regional_name} customs. "
                f"It has NOT been reviewed by any priest, pandit, community elder, or religious authority and may contain errors, omissions, or "
                f"regionally inappropriate details. Please review carefully with your family elders and officiant before finalizing."
            ),
            "timing_disclaimer": "Panchang calculations are astronomical estimates based on Drik Ganita and Ephemeris models. Muhurat dates and ritual sequences must always be confirmed with your family's trusted priest, pandit, or religious officiant.",
            "disclaimer": (
                f"This sequence was AI-drafted as a starting point based on general knowledge of {primary.regional_name} and {secondary.regional_name} customs. "
                f"It has not been reviewed by a priest or community elder and may contain errors, omissions, or regionally inappropriate details. "
                f"Please review carefully with your family and officiant before finalizing."
            ),
        }

    def _detect_shared_key(self, item_name: str) -> str | None:
        lower_name = item_name.lower()
        for key in self.SHARED_KEYWORDS:
            if key in lower_name:
                return key
        return None
