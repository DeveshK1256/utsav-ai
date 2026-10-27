import json
import os
from typing import Any

from backend.app.schemas.quotes import ExtractedLineItemSchema, HiddenCostAlertSchema

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "hidden_cost_checklist.json")


class HiddenCostDetector:
    _checklist_cache: dict[str, list[dict[str, Any]]] = {}

    @classmethod
    def load_checklist(cls) -> dict[str, list[dict[str, Any]]]:
        if not cls._checklist_cache:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, encoding="utf-8") as f:
                    cls._checklist_cache = json.load(f)
            else:
                cls._checklist_cache = {}
        return cls._checklist_cache

    @classmethod
    def analyze_quote(
        cls,
        category: str,
        line_items: list[ExtractedLineItemSchema],
        terms_and_conditions: list[str] | None = None
    ) -> list[HiddenCostAlertSchema]:
        """
        Pure deterministic diff between extracted quote line items and the category checklist.
        Returns list of alerts with status 'missing_from_quote', 'explicitly_covered', or 'ambiguous'.
        Zero LLM calls.
        """
        checklist = cls.load_checklist().get(category.lower(), [])
        if not checklist:
            return []

        # Combine all extracted textual content for matching
        all_text = " ".join([
            f"{item.name} {item.category_tag or ''} {item.notes or ''}"
            for item in line_items
        ] + (terms_and_conditions or [])).lower()

        alerts = []
        for check in checklist:
            code = check["code"]
            name = check["name"]
            desc = check["description"]
            impact = check["typical_impact"]
            question = check["suggested_question"]

            # Match criteria based on code and name keywords
            keywords = cls._extract_keywords_for_check(code)
            is_covered = any(kw in all_text for kw in keywords)

            status = "explicitly_covered" if is_covered else "missing_from_quote"

            alerts.append(
                HiddenCostAlertSchema(
                    code=code,
                    name=name,
                    description=desc,
                    typical_impact=impact,
                    suggested_question=question,
                    status=status
                )
            )

        return alerts

    @classmethod
    def _extract_keywords_for_check(cls, code: str) -> list[str]:
        mapping = {
            "cat_overtime": ["overtime", "extra hour", "midnight", "late hour"],
            "cat_extra_plates": ["buffer", "floating", "extra plate", "excess plate"],
            "cat_gst": ["gst", "tax", "18%", "5% tax", "taxes included"],
            "cat_crockery_breakage": ["breakage", "crockery", "cutlery", "chinaware"],
            "cat_transport_chafing": ["transport", "tempo", "chafing", "fuel", "ice"],
            "cat_service_staff": ["server", "waiter", "staff", "gratuity", "service charge"],
            "venue_generator_fuel": ["generator", "diesel", "fuel", "dg set", "power backup"],
            "venue_corkage": ["corkage", "liquor", "outside liquor", "fl-4", "bar license"],
            "venue_cleaning": ["cleaning", "sanitation", "waste", "trash", "deep clean"],
            "venue_vendor_royalty": ["royalty", "outside vendor", "empanelled", "vendor fee"],
            "venue_aircon_overtime": ["air condition", "ac timing", "ac overtime", "cooling"],
            "venue_valet_parking": ["valet", "parking", "traffic marshal"],
            "dec_dismantling": ["dismantl", "teardown", "clearance", "strike down"],
            "dec_heavy_electricity": ["electrician", "3-phase", "cabling", "power hookup"],
            "dec_fresh_flower_fluctuation": ["mandi", "wholesale rate", "price fluctuation", "fixed floral"],
            "dec_transport_logistics": ["freight", "truck", "tempo", "loading", "unloading"],
            "dec_taxes": ["gst", "18%", "tax invoice", "taxes included"],
            "photo_overtime": ["overtime", "per hour", "extended hour", "hourly rate"],
            "photo_hard_drive": ["hard drive", "raw footage", "hdd", "ssd", "raw files"],
            "photo_drone_permissions": ["drone", "aerial", "pilot", "uav", "police noc"],
            "photo_album_shipping": ["album", "canvera", "courier", "flush mount", "photobook"],
            "photo_crew_travel": ["crew meal", "travel", "accommodation", "outstation", "cab"]
        }
        return mapping.get(code, [code.replace("_", " ")])
