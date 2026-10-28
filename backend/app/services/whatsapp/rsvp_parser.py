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
        "yes", "attending", "attend", "coming", "haan", "ha", "aayenge", "ayenge",
        "pakka", "confirmed", "confirm", "joining", "be there", "looking forward",
        "definitely", "present", "zaroor"
    }

    DECLINED_TOKENS: ClassVar[set[str]] = {
        "no", "declined", "decline", "sorry", "cannot", "cant", "can't", "unable",
        "nahi", "na", "miss", "wont", "won't", "not able", "regret"
    }

    MAYBE_TOKENS: ClassVar[set[str]] = {
        "maybe", "tentative", "not sure", "try", "trying", "koshish", "shayad",
        "shyd", "let you know", "will update"
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
                parsing_method="quick_reply"
            )
        elif "no" in bid or "decline" in bid or "reject" in bid:
            return ParsedRSVP(
                rsvp_status="declined",
                headcount=0,
                confidence=1.0,
                needs_host_review=False,
                parsing_method="quick_reply"
            )
        elif "maybe" in bid or "tentative" in bid:
            return ParsedRSVP(
                rsvp_status="maybe",
                headcount=1,
                confidence=1.0,
                needs_host_review=False,
                parsing_method="quick_reply"
            )

        return ParsedRSVP(
            rsvp_status="unknown",
            headcount=1,
            confidence=0.4,
            needs_host_review=True,
            parsing_method="quick_reply"
        )

    @classmethod
    def parse_free_text(cls, text: str) -> ParsedRSVP:
        """
        Deterministic parser for free-text RSVP responses.
        Extracts status, headcount, diet, and computes deterministic confidence score.
        """
        raw = text.strip()
        lower = raw.lower()
        tokens_set = set(re.findall(r"\b[a-zA-Z']+\b", lower))

        def _has_token(token: str) -> bool:
            if " " in token:
                return bool(re.search(rf"\b{re.escape(token)}\b", lower))
            return token in tokens_set

        has_attending = any(_has_token(token) for token in cls.ATTENDING_TOKENS)
        has_declined = any(_has_token(token) for token in cls.DECLINED_TOKENS)
        has_maybe = any(_has_token(token) for token in cls.MAYBE_TOKENS)

        # 1. Resolve Status
        if has_attending and not has_declined and not has_maybe:
            status = "attending"
        elif has_declined and not has_attending:
            status = "declined"
        elif has_maybe and not has_declined:
            status = "maybe"
        elif has_attending and has_declined:
            # Ambiguous conflict (e.g. "I want to come yes, but sorry no I can't")
            status = "unknown"
        else:
            status = "unknown"

        # 2. Extract Headcount
        headcount = 1
        explicit_headcount_found = False

        if status == "declined":
            headcount = 0
        else:
            # Pattern: "total 3", "family of 4", "party of 5"
            total_match = re.search(r"\b(?:total|family of|party of)\s*(\d{1,2})\b", lower)
            if total_match:
                headcount = int(total_match.group(1))
                explicit_headcount_found = True
            else:
                # Count self + relatives + specified kids/plus counts
                additional = 0
                kids_match = re.search(r"\b(\d{1,2})\s*(?:kids?|children|child)\b", lower)
                if kids_match:
                    additional += int(kids_match.group(1))
                    explicit_headcount_found = True

                relatives = 0
                for rel in ["wife", "husband", "spouse", "partner", "mother", "father", "brother", "sister", "bhabhi", "bhaiya"]:
                    if rel in lower:
                        relatives += 1
                if relatives > 0:
                    additional += relatives
                    explicit_headcount_found = True

                plus_match = re.search(r"\b(?:plus|\+)\s*(\d{1,2})\b", lower)
                if plus_match:
                    additional += int(plus_match.group(1))
                    explicit_headcount_found = True

                num_people_match = re.search(r"\b(\d{1,2})\s*(?:people|persons|guests|members)\b", lower)
                if num_people_match and additional == 0:
                    headcount = int(num_people_match.group(1))
                    explicit_headcount_found = True
                elif additional > 0:
                    headcount = 1 + additional

        # 3. Extract Diet
        diet = None
        if "jain" in lower:
            diet = "jain"
        elif "vegan" in lower:
            diet = "vegan"
        elif "non veg" in lower or "non-veg" in lower or "chicken" in lower or "mutton" in lower or "fish" in lower:
            diet = "non_veg"
        elif "pure veg" in lower or "vegetarian" in lower or "veg" in lower:
            diet = "veg"

        # 4. Deterministic Confidence Gating (DEC-002)
        confidence = 0.0
        if status in ("attending", "declined"):
            confidence += 0.6  # Base score for unambiguous status token
            if explicit_headcount_found and 1 <= headcount <= 15:
                confidence += 0.25
            elif status == "declined":
                confidence += 0.35
            else:
                confidence += 0.15  # Default single-attendee inference

            if diet is not None:
                confidence += 0.05
        elif status == "maybe":
            confidence = 0.55  # Tentative status requires host review per DEC-002
        else:
            confidence = 0.35  # Ambiguous or no clear intent

        # Cap confidence between 0.0 and 1.0
        confidence = round(min(max(confidence, 0.0), 1.0), 2)
        needs_host_review = (confidence < 0.70) or (status == "unknown") or (headcount > 15)

        return ParsedRSVP(
            rsvp_status=status if not needs_host_review else ("attending" if status == "attending" else "unknown"),
            headcount=headcount,
            diet=diet,
            notes=raw if len(raw) <= 255 else raw[:252] + "...",
            confidence=confidence,
            needs_host_review=needs_host_review,
            parsing_method="deterministic_nlp"
        )
