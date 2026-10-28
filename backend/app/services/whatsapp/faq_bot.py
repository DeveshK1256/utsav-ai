import logging
from typing import Any, ClassVar

from pydantic import BaseModel

from backend.app.models.models import Event, EventFactSheet

logger = logging.getLogger(__name__)

HARD_FALLBACK_REFUSAL = (
    "I don't have that information in the event details. I'll check with the host and get back to you!"
)


class FAQResponse(BaseModel):
    answer: str
    is_in_scope: bool
    notified_host: bool
    source_field: str | None = None
    provider_used: str = "deterministic_retriever"
    fallback_warning: str | None = None


class FAQBotService:
    """
    Guest concierge FAQ answerer strictly grounded in the event's EventFactSheet.
    Strict architectural boundary: Answers ONLY from verified fact sheet fields.
    Refuses any question whose factual basis is missing from the sheet with
    HARD_FALLBACK_REFUSAL and sets notified_host = True.
    """

    KEYWORD_MAPPINGS: ClassVar[dict[str, list[str]]] = {
        "venue_address": [
            "where",
            "address",
            "venue",
            "location",
            "hall",
            "reach",
            "how to get",
            "place",
        ],
        "map_link": ["map", "google map", "gps", "directions", "link"],
        "parking_info": ["parking", "park", "valet", "car", "vehicle"],
        "dress_code": [
            "dress",
            "wear",
            "attire",
            "outfit",
            "clothes",
            "code",
            "color code",
            "theme",
        ],
        "timing_notes": [
            "when",
            "time",
            "timing",
            "start",
            "begins",
            "schedule",
            "entry",
            "muhurat",
            "hours",
        ],
    }

    @classmethod
    def _format_standard_field_answer(
        cls, field: str, val: Any, fact_sheet: EventFactSheet
    ) -> str:
        if field == "venue_address":
            ans = f"The celebration is at: {val}."
            if fact_sheet.map_link:
                ans += f" Google Maps: {fact_sheet.map_link}"
            return ans
        if field == "parking_info":
            return f"Parking Information: {val}"
        if field == "dress_code":
            return f"Dress Code & Attire: {val}"
        if field == "timing_notes":
            return f"Schedule & Timings: {val}"
        if field == "map_link":
            return f"Location directions link: {val}"
        return str(val)

    @classmethod
    def _match_standard_field(
        cls, fact_sheet: EventFactSheet, q_clean: str
    ) -> FAQResponse | None:
        for field, keywords in cls.KEYWORD_MAPPINGS.items():
            if any(kw in q_clean for kw in keywords):
                val = getattr(fact_sheet, field, None)
                if val and str(val).strip():
                    ans = cls._format_standard_field_answer(field, val, fact_sheet)
                    return FAQResponse(
                        answer=ans, is_in_scope=True, notified_host=False, source_field=field
                    )
        return None

    @classmethod
    def _match_other_facts(
        cls, fact_sheet: EventFactSheet, q_clean: str
    ) -> FAQResponse | None:
        other_facts = fact_sheet.other_facts or {}
        for fact_key, fact_val in other_facts.items():
            clean_key = str(fact_key).lower().replace("_", " ")
            has_match = clean_key in q_clean or any(word in q_clean for word in clean_key.split())
            if has_match and fact_val and str(fact_val).strip():
                return FAQResponse(
                    answer=f"{str(fact_key).replace('_', ' ').title()}: {fact_val}",
                    is_in_scope=True,
                    notified_host=False,
                    source_field=f"other_facts.{fact_key}",
                )
        return None

    @classmethod
    def _match_event_date(cls, event: Event, q_clean: str) -> FAQResponse | None:
        if any(w in q_clean for w in ["date", "day", "which day"]):
            return FAQResponse(
                answer=f"{event.name} will be celebrated on {event.start_date.strftime('%A, %d %B %Y')} in {event.city}.",
                is_in_scope=True,
                notified_host=False,
                source_field="event.start_date",
            )
        return None

    @classmethod
    def answer_question(
        cls, event: Event, fact_sheet: EventFactSheet | None, question: str, use_llm: bool = False
    ) -> FAQResponse:
        """
        Determines if the question can be answered from the fact sheet.
        If yes, formats a polite answer. If no, refuses and flags host.
        """
        q_clean = question.strip().lower()
        if not q_clean:
            return FAQResponse(
                answer="Could you please tell me how I can help you with the celebration details?",
                is_in_scope=True,
                notified_host=False,
                source_field="greeting",
            )

        if not fact_sheet:
            return FAQResponse(
                answer=HARD_FALLBACK_REFUSAL,
                is_in_scope=False,
                notified_host=True,
                source_field=None,
                fallback_warning="Fact sheet empty for this event",
            )

        # 1. Check Standard Structured Fields
        resp = cls._match_standard_field(fact_sheet, q_clean)
        if resp:
            return resp

        # 2. Check Custom Key-Value other_facts
        resp = cls._match_other_facts(fact_sheet, q_clean)
        if resp:
            return resp

        # 3. Check General Event Attributes
        resp = cls._match_event_date(event, q_clean)
        if resp:
            return resp

        # 4. Strict Boundary Enforcement
        return FAQResponse(
            answer=HARD_FALLBACK_REFUSAL,
            is_in_scope=False,
            notified_host=True,
            source_field=None,
            fallback_warning="Question outside ground truth scope",
        )
