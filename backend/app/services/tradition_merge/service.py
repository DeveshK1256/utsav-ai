import logging
import os
from datetime import date
from typing import Any, ClassVar

from sqlalchemy.orm import Session

from backend.app.models.models import RitualItem, Tradition
from backend.app.services.tradition_merge.gemini_agent import GeminiTraditionMergeAgent
from backend.app.services.tradition_merge.stub_agent import (
    BaseTraditionMergeAgent,
    DeterministicStubTraditionMergeAgent,
)

logger = logging.getLogger(__name__)


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

    def _process_primary_samagri_item(
        self,
        item: RitualItem,
        primary: Tradition,
        shared_lookup: dict[str, dict[str, Any]],
        reconciled_items: list[dict[str, Any]],
    ) -> None:
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
                "is_verified": bool(item.is_verified and primary.is_verified),
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
                    "is_verified": bool(item.is_verified and primary.is_verified),
                    "provenance": [primary.regional_name],
                }
            )

    def _append_secondary_to_shared(
        self,
        item: RitualItem,
        secondary: Tradition,
        shared_entry: dict[str, Any],
    ) -> None:
        shared_entry["provenance"].append(secondary.regional_name)
        shared_entry["regional_name"] += f" / {item.regional_name or item.item_name}"
        shared_entry["standard_quantity"] = (
            f"{shared_entry['standard_quantity']} (combined envelope)"
        )
        shared_entry["is_verified"] = bool(shared_entry["is_verified"] and item.is_verified)

    def _process_secondary_samagri_item(
        self,
        item: RitualItem,
        secondary: Tradition,
        shared_lookup: dict[str, dict[str, Any]],
        reconciled_items: list[dict[str, Any]],
    ) -> None:
        category_key = self._detect_shared_key(item.item_name)
        if category_key and category_key in shared_lookup:
            self._append_secondary_to_shared(item, secondary, shared_lookup[category_key])
        elif category_key and category_key not in shared_lookup:
            shared_lookup[category_key] = {
                "item_name": item.item_name,
                "regional_name": f"{item.regional_name or item.item_name}",
                "standard_quantity": item.standard_quantity,
                "category": item.category,
                "spiritual_purpose": item.spiritual_purpose,
                "source_tradition": "Shared Vedic / Common",
                "ritual_name": f"{item.ritual_name or 'Sacred Rites'}",
                "is_verified": bool(item.is_verified and secondary.is_verified),
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
                    "is_verified": bool(item.is_verified and secondary.is_verified),
                    "provenance": [secondary.regional_name],
                }
            )

    def _reconcile_samagri(
        self, primary: Tradition, secondary: Tradition
    ) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
        primary_items = (
            self.db.query(RitualItem).filter(RitualItem.tradition_code == primary.code).all()
        )
        secondary_items = (
            self.db.query(RitualItem).filter(RitualItem.tradition_code == secondary.code).all()
        )
        shared_lookup: dict[str, dict[str, Any]] = {}
        reconciled_items: list[dict[str, Any]] = []

        for item in primary_items:
            self._process_primary_samagri_item(item, primary, shared_lookup, reconciled_items)
        for item in secondary_items:
            self._process_secondary_samagri_item(item, secondary, shared_lookup, reconciled_items)

        final_samagri = list(shared_lookup.values()) + reconciled_items
        return final_samagri, shared_lookup

    def _build_merge_response(
        self,
        event_name: str | None,
        primary: Tradition,
        secondary: Tradition,
        run_of_show: Any,
        final_samagri: list[dict[str, Any]],
        shared_lookup: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
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
                f"This ceremonial sequence and ritual items list were AI-drafted as a starting "
                f"point based on general cultural knowledge of {primary.regional_name} and "
                f"{secondary.regional_name} customs. It has NOT been reviewed by any priest, "
                "pandit, community elder, or religious authority and may contain errors, "
                "omissions, or regionally inappropriate details. Please review carefully with your "
                "family elders and officiant before finalizing."
            ),
            "timing_disclaimer": (
                "Panchang calculations are astronomical estimates based on Drik Ganita and "
                "Ephemeris models. Muhurat dates and ritual sequences must always be confirmed "
                "with your family's trusted priest, pandit, or religious officiant."
            ),
            "disclaimer": (
                f"This sequence was AI-drafted as a starting point based on general knowledge of "
                f"{primary.regional_name} and {secondary.regional_name} customs. "
                "It has not been reviewed by a priest or community elder and may contain errors, "
                "omissions, or regionally inappropriate details. Please review carefully with your "
                "family and officiant before finalizing."
            ),
        }

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
        Returns unified run-of-show with origin labels, reconciled samagri with provenance,
        and alignment checklist.
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

        final_samagri, shared_lookup = self._reconcile_samagri(primary, secondary)

        return self._build_merge_response(
            event_name, primary, secondary, run_of_show, final_samagri, shared_lookup
        )

    def _detect_shared_key(self, item_name: str) -> str | None:
        lower_name = item_name.lower()
        for key in self.SHARED_KEYWORDS:
            if key in lower_name:
                return key
        return None
