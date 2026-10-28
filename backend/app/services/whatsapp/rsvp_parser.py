import re
from typing import ClassVar

from pydantic import BaseModel


class ParsedRSVP(BaseModel):
    rsvp_status: str  # "attending", "declined", "maybe", "unknown"
    headcount: int
    diet: str | None = None  # "veg", "jain", "non_veg", "vegan"
    notes: str | None = None
    confidence: float  # Deterministically computed 0.0 - 1.0
    needs_host_review: bool
    parsing_method: str  # "quick_reply" or "deterministic_nlp"


class RSVPParser:
    """
    Parses WhatsApp guest replies into structured RSVP data.
    Enforces deterministic confidence gating per DEC-002:
    Confidence is NEVER self-reported by an LLM, but computed from token clarity and bounds.
    """

    ATTENDING_TOKENS: ClassVar[set[str]] = {
        "yes",
        "attending",
        "attend",
        "coming",
        "haan",
        "ha",
        "aayenge",
        "ayenge",
        "pakka",
        "confirmed",
        "confirm",
        "joining",
        "be there",
        "looking forward",
        "definitely",
        "present",
        "zaroor",
    }

    DECLINED_TOKENS: ClassVar[set[str]] = {
        "no",
        "declined",
        "decline",
        "sorry",
        "cannot",
        "cant",
        "can't",
        "unable",
        "nahi",
        "na",
        "miss",
        "wont",
        "won't",
        "not able",
        "regret",
    }

    MAYBE_TOKENS: ClassVar[set[str]] = {
        "maybe",
        "tentative",
        "not sure",
        "try",
        "trying",
        "koshish",
        "shayad",
        "shyd",
        "let you know",
        "will update",
    }

    @classmethod
    def parse_quick_reply(cls, button_id: str) -> ParsedRSVP:
        """Parses structured quick-reply button clicks (Zero LLM, 100% confidence)."""
        bid = button_id.lower().strip()
        if "yes" in bid or "attending" in bid or "accept" in bid:
            return ParsedRSVP(
                rsvp_status="attending",
                headcount=1,
                confidence=1.0,
                needs_host_review=False,
                parsing_method="quick_reply",
            )
        elif "no" in bid or "decline" in bid or "reject" in bid:
            return ParsedRSVP(
                rsvp_status="declined",
                headcount=0,
                confidence=1.0,
                needs_host_review=False,
                parsing_method="quick_reply",
            )
        elif "maybe" in bid or "tentative" in bid:
            return ParsedRSVP(
                rsvp_status="maybe",
                headcount=1,
                confidence=1.0,
                needs_host_review=False,
                parsing_method="quick_reply",
            )

        return ParsedRSVP(
            rsvp_status="unknown",
            headcount=1,
            confidence=0.4,
            needs_host_review=True,
            parsing_method="quick_reply",
        )

    @classmethod
    def _has_matching_token(cls, text: str, tokens_set: set[str], candidates: set[str]) -> bool:
        for t in candidates:
            if " " in t:
                if re.search(rf"\b{re.escape(t)}\b", text):
                    return True
            elif t in tokens_set:
                return True
        return False

    @classmethod
    def _extract_status(cls, lower: str, tokens_set: set[str]) -> str:
        has_att = cls._has_matching_token(lower, tokens_set, cls.ATTENDING_TOKENS)
        has_dec = cls._has_matching_token(lower, tokens_set, cls.DECLINED_TOKENS)
        has_may = cls._has_matching_token(lower, tokens_set, cls.MAYBE_TOKENS)

        if has_att and not has_dec and not has_may:
            return "attending"
        if has_dec and not has_att:
            return "declined"
        if has_may and not has_dec:
            return "maybe"
        return "unknown"

    @classmethod
    def _count_additional_guests(cls, lower: str) -> tuple[int, bool]:
        additional = 0
        explicit = False

        kids_match = re.search(r"\b(\d{1,2})\s*(?:kids?|children|child)\b", lower)
        if kids_match:
            additional += int(kids_match.group(1))
            explicit = True

        rel_terms = ["wife", "husband", "spouse", "partner", "mother", "father", "brother", "sister", "bhabhi", "bhaiya"]
        rel_count = sum(1 for rel in rel_terms if rel in lower)
        if rel_count > 0:
            additional += rel_count
            explicit = True

        plus_match = re.search(r"\b(?:plus|\+)\s*(\d{1,2})\b", lower)
        if plus_match:
            additional += int(plus_match.group(1))
            explicit = True

        return additional, explicit

    @classmethod
    def _extract_headcount(cls, lower: str, status: str) -> tuple[int, bool]:
        if status == "declined":
            return 0, False

        total_match = re.search(r"\b(?:total|family of|party of)\s*(\d{1,2})\b", lower)
        if total_match:
            return int(total_match.group(1)), True

        additional, explicit = cls._count_additional_guests(lower)
        num_people_match = re.search(r"\b(\d{1,2})\s*(?:people|persons|guests|members)\b", lower)
        if num_people_match and additional == 0:
            return int(num_people_match.group(1)), True

        return (1 + additional, True) if additional > 0 else (1, explicit)

    @classmethod
    def _extract_diet(cls, lower: str) -> str | None:
        if "jain" in lower:
            return "jain"
        if "vegan" in lower:
            return "vegan"
        if any(term in lower for term in ["non veg", "non-veg", "chicken", "mutton", "fish"]):
            return "non_veg"
        if any(term in lower for term in ["pure veg", "vegetarian", "veg"]):
            return "veg"
        return None

    @classmethod
    def _calculate_confidence(
        cls, status: str, headcount: int, explicit_headcount: bool, diet: str | None
    ) -> tuple[float, bool]:
        confidence = 0.0
        if status in ("attending", "declined"):
            confidence += 0.6
            if explicit_headcount and 1 <= headcount <= 15:
                confidence += 0.25
            elif status == "declined":
                confidence += 0.35
            else:
                confidence += 0.15

            if diet is not None:
                confidence += 0.05
        elif status == "maybe":
            confidence = 0.55
        else:
            confidence = 0.35

        confidence = round(min(max(confidence, 0.0), 1.0), 2)
        needs_host_review = (confidence < 0.70) or (status == "unknown") or (headcount > 15)
        return confidence, needs_host_review

    @classmethod
    def parse_free_text(cls, text: str) -> ParsedRSVP:
        """
        Deterministic parser for free-text RSVP responses.
        Extracts status, headcount, diet, and computes deterministic confidence score.
        """
        raw = text.strip()
        lower = raw.lower()
        tokens_set = set(re.findall(r"\b[a-zA-Z']+\b", lower))

        status = cls._extract_status(lower, tokens_set)
        headcount, explicit_headcount = cls._extract_headcount(lower, status)
        diet = cls._extract_diet(lower)
        confidence, needs_host_review = cls._calculate_confidence(
            status, headcount, explicit_headcount, diet
        )

        return ParsedRSVP(
            rsvp_status=status
            if not needs_host_review
            else ("attending" if status == "attending" else "unknown"),
            headcount=headcount,
            diet=diet,
            notes=raw if len(raw) <= 255 else raw[:252] + "...",
            confidence=confidence,
            needs_host_review=needs_host_review,
            parsing_method="deterministic_nlp",
        )
