"""
Multi-Tradition Merge Agent (F2 Cultural & Ritual Intelligence).
Combines two distinct cultural traditions (e.g., Tamil Brahmin + Punjabi, Maharashtrian + Marwari)
into a unified itinerary and reconciled samagri checklist.
Tags source traditions, combines shared sacred items, detects schedule/custom conflicts,
and produces actionable family alignment prompts.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.models.models import Tradition, RitualItem, Event


class TraditionMergeService:
    """
    Reconciles two distinct cultural traditions into an integrated schedule and samagri list.
    Enforces deterministic deduplication and source attribution.
    """

    # Shared base items that commonly appear across Indian Vedic rites
    SHARED_KEYWORDS = {
        "ghee": ("Pure Cow Ghee", "puja_samagri", "Oblations into sacred Agni for Vivah Homam"),
        "akshata": ("Sacred Akshata Rice", "puja_samagri", "Elder blessings showered over couple during vows"),
        "rice": ("Sacred Akshata Rice", "puja_samagri", "Elder blessings showered over couple during vows"),
        "coconut": ("Shriphal (Auspicious Coconuts)", "offerings", "Sacred offerings to Varuna and divine witnesses"),
        "supari": ("Betel Nuts (Supari)", "offerings", "Invocation of Lord Ganesha and planetary deities"),
        "betel": ("Betel Leaves & Nuts", "offerings", "Auspicious welcome and invocation"),
        "haldi": ("Raw Turmeric (Haldi)", "cleansing_pastes", "Auspicious purification for bride and groom"),
        "turmeric": ("Raw Turmeric (Haldi)", "cleansing_pastes", "Auspicious purification for bride and groom"),
        "sindoor": ("Sacred Sindoor / Kumkum", "sacred_ornaments", "Marital sanctity applied in parting hair"),
        "kumkum": ("Sacred Sindoor / Kumkum", "sacred_ornaments", "Auspicious tilak and invocation"),
    }

    # Known cross-cultural conflict pairs and harmonization strategies
    KNOWN_DIVERGENCES = [
        {
            "pair": {"south_indian_iyer", "punjabi_sikh"},
            "issue": "Ritual Timing & Venue Sequence",
            "description": "Tamil Brahmin muhurats traditionally happen at dawn/early morning (Brahma Muhurtam/Udaya), while Anand Karaj traditionally takes place mid-morning followed by festive Langar. Evening receptions with Bhangra/DJ contrast with traditional classical Carnatic Nadaswaram.",
            "recommendation": "Host early-morning Tamil Brahmin Mangalya Dharanam & Saptapadi, followed by mid-morning Anand Karaj at Gurdwara with Karah Parshad, culminating in a combined evening festive Sangeet & Reception."
        },
        {
            "pair": {"south_indian_iyer", "punjabi_sikh"},
            "issue": "Dietary Expectations",
            "description": "Tamil Brahmin Kalyanam requires strictly satvik vegetarian catering (often no onion, no garlic), while Punjabi celebrations traditionally feature rich North Indian dairy curries or non-vegetarian options at evening functions.",
            "recommendation": "Keep the sacred wedding day lunch strictly traditional satvik vegetarian served on banana leaves. Transition to lavish North Indian cuisine at the evening cocktail/reception."
        },
        {
            "pair": {"maharashtrian_vedic", "marwari_traditional"},
            "issue": "Attire and Welcome Customs (Toran vs. Simant Pujan)",
            "description": "Marwari groom entrance features Toran Bandhan where the groom touches a carved wooden arch with a sword/stick. Maharashtrian custom begins with Simant Pujan where the bride's parents wash the groom's feet and present traditional gifts.",
            "recommendation": "Integrate sequentially: perform Simant Pujan first at the outer welcome threshold, followed by the groom's ceremonial Toran touching before entering the main Mandap."
        },
        {
            "pair": {"gujarati_hindu", "south_indian_iyer"},
            "issue": "Pheras Count & Sacred Knots",
            "description": "Gujarati weddings feature 4 Mangal Pheras around the sacred fire (representing Dharma, Artha, Kama, Moksha). Tamil Brahmin Kalyanam emphasizes the 3 knots of the Thali (Mangalya Dharanam) followed by full 7 steps (Saptapadi).",
            "recommendation": "Perform Thali tying (3 knots) first, followed by the Vedic Saptapadi (7 steps) and 4 celebratory Gujarati pheras so both ancestral lineages feel honored."
        },
        {
            "pair": {"bengali_vedic", "punjabi_sikh"},
            "issue": "Bridal Entrance & Gaze Custom",
            "description": "Bengali bride enters seated on a Pidi carried by brothers with face veiled by betel leaves (Saat Paake Ghomar / Shubho Drishti). Punjabi wedding emphasizes bride entering under a floral Phoolon Ki Chaadar escorted by brothers.",
            "recommendation": "Bride enters under an ornate Phoolon Ki Chaadar (Punjabi honor), then mounts the Pidi for the traditional seven circles and dramatic betel-leaf reveal (Shubho Drishti)."
        }
    ]

    def __init__(self, db: Session):
        self.db = db

    def get_tradition(self, code: str) -> Optional[Tradition]:
        return self.db.query(Tradition).filter(Tradition.code == code).first()

    def merge_traditions(
        self,
        primary_code: str,
        secondary_code: str,
        event_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes a dual-tradition merge.
        Returns unified metadata, reconciled samagri with source provenance, and alignment checklist.
        """
        primary = self.get_tradition(primary_code)
        secondary = self.get_tradition(secondary_code)

        if not primary or not secondary:
            raise ValueError(f"Invalid tradition codes: primary={primary_code}, secondary={secondary_code}")

        # Fetch items
        primary_items = self.db.query(RitualItem).filter(RitualItem.tradition_code == primary_code).all()
        secondary_items = self.db.query(RitualItem).filter(RitualItem.tradition_code == secondary_code).all()

        # Reconcile samagri items with provenance tracking
        reconciled_items = []
        shared_lookup = {}

        # 1. Process primary items
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
                reconciled_items.append({
                    "item_name": item.item_name,
                    "regional_name": item.regional_name,
                    "standard_quantity": item.standard_quantity,
                    "category": item.category,
                    "spiritual_purpose": item.spiritual_purpose,
                    "source_tradition": primary.regional_name,
                    "ritual_name": item.ritual_name,
                    "is_verified": item.is_verified and primary.is_verified,
                    "provenance": [primary.regional_name],
                })

        # 2. Process secondary items
        for item in secondary_items:
            category_key = self._detect_shared_key(item.item_name)
            if category_key and category_key in shared_lookup:
                # Merge into existing shared item
                shared_entry = shared_lookup[category_key]
                shared_entry["provenance"].append(secondary.regional_name)
                shared_entry["regional_name"] += f" / {item.regional_name or item.item_name}"
                shared_entry["standard_quantity"] = f"{shared_entry['standard_quantity']} (combined envelope)"
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
                reconciled_items.append({
                    "item_name": item.item_name,
                    "regional_name": item.regional_name,
                    "standard_quantity": item.standard_quantity,
                    "category": item.category,
                    "spiritual_purpose": item.spiritual_purpose,
                    "source_tradition": secondary.regional_name,
                    "ritual_name": item.ritual_name,
                    "is_verified": item.is_verified and secondary.is_verified,
                    "provenance": [secondary.regional_name],
                })

        # Add shared items to final list
        final_samagri = list(shared_lookup.values()) + reconciled_items

        # Identify cultural divergences and family alignment points
        alignment_points = self._detect_divergences(primary_code, secondary_code)

        return {
            "status": "success",
            "event_name": event_name,
            "fusion_title": f"{primary.regional_name} + {secondary.regional_name} Cultural Fusion",
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
            "reconciled_samagri_summary": {
                "total_unique_items": len(final_samagri),
                "shared_common_items_count": len(shared_lookup),
                "primary_specific_count": len([i for i in final_samagri if i["source_tradition"] == primary.regional_name]),
                "secondary_specific_count": len([i for i in final_samagri if i["source_tradition"] == secondary.regional_name]),
            },
            "samagri_items": final_samagri,
            "family_alignment_points": alignment_points,
            "priest_coordination_note": (
                f"Both traditions have been reconciled into a single ceremonial guide. "
                f"Priests from both sides ({primary.regional_name} and {secondary.regional_name}) "
                f"should review the flagged alignment points together 2 weeks before the ceremony."
            ),
            "disclaimer": (
                "Regional customs and family practices vary. This merged run-of-show provides a respectful "
                "harmonization framework but must be validated with the family elders and priests."
            )
        }

    def _detect_shared_key(self, item_name: str) -> Optional[str]:
        lower_name = item_name.lower()
        for key in self.SHARED_KEYWORDS:
            if key in lower_name:
                return key
        return None

    def _detect_divergences(self, code_a: str, code_b: str) -> List[Dict[str, str]]:
        active_set = {code_a, code_b}
        matches = []
        for divergence in self.KNOWN_DIVERGENCES:
            if divergence["pair"] == active_set:
                matches.append({
                    "issue": divergence["issue"],
                    "description": divergence["description"],
                    "recommendation": divergence["recommendation"]
                })

        # Generic default alignment if no specific pair is pre-indexed
        if not matches:
            matches.append({
                "issue": "Ceremonial Language & Priesthood Coordination",
                "description": "Ceremonies will feature mantras and shlokas in both regional languages and Sanskrit. Family pandits should coordinate the sequence of main vows.",
                "recommendation": "Arrange a 30-minute joint briefing between the two officiating priests to allocate responsibilities for Saptapadi, Mangalsutra, and Kanyadaan."
            })
            matches.append({
                "issue": "Attire and Styling Transition",
                "description": "Couple may wear traditional attire from one culture for the morning vidhi and the second culture for the reception.",
                "recommendation": "Plan a dedicated 90-minute dress change and refresh window in the run-of-show between ceremonies."
            })

        return matches
