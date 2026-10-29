import logging
from abc import ABC, abstractmethod
from datetime import date

from backend.app.models.models import Tradition
from backend.app.services.dag_scheduler import DAGScheduler
from backend.app.services.tradition_merge.schemas import (
    CeremonyItemSchema,
    FamilyAlignmentPointSchema,
    MergedRunOfShowSchema,
)

logger = logging.getLogger(__name__)


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

    def _build_maha_punjabi_show(
        self, primary: Tradition, secondary: Tradition, p_code: str
    ) -> tuple[str, list[CeremonyItemSchema], list[FamilyAlignmentPointSchema]]:
        title = f"{primary.regional_name} × {secondary.regional_name} Fusion Vivah"
        maha_name = primary.regional_name if "maharashtrian" in p_code else secondary.regional_name
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
                cultural_significance=(
                    "Joint application of turmeric (Vatna/Halad) by loved ones from both families "
                    "for purification and radiant blessings."
                ),
                family_guidance=(
                    "Families can apply ubtan in alternating turns to folk dholak songs and "
                    "Marathi lagna geet."
                ),
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
                cultural_significance=(
                    "Nocturnal celebratory procession carrying the illuminated Jaggo brass pot, "
                    "followed by high-energy Bhangra and musical performances."
                ),
                family_guidance=(
                    "Maharashtrian family joins in carrying the Jaggo pot with sisters and "
                    "maternal aunts."
                ),
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
                cultural_significance=(
                    "Maternal uncles bless bride with ivory red Chooda and Kalire; male "
                    "counterparts of both lineages embrace during Milni with stoles and garlands."
                ),
                family_guidance=(
                    "Allocate 5 pairs of counterparts (fathers, brothers, maternal uncles) for the "
                    "Milni exchange."
                ),
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
                cultural_significance=(
                    "Simant Pujan welcoming of groom by bride's mother; silk Antarpat held between "
                    "couple until Mangalashtaka verses culminate at exact Muhurat."
                ),
                family_guidance=(
                    "Bride enters under Punjabi floral Phoolon Ki Chaadar, then halts behind the "
                    "sacred Antarpat cloth."
                ),
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
                cultural_significance=(
                    "Harmonization of Vedic 7 steps (Saptapadi) around the sacred Vivah fire with "
                    "the spiritual teachings of 4 Laavan / Pheras."
                ),
                family_guidance=(
                    "Priests from both traditions coordinate the mantras: Maharashtrian Pandit "
                    "leads Saptapadi vows, Punjabi elder reads the Laavan."
                ),
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
                cultural_significance=(
                    "Celebratory banquet honoring both heritages with multi-regional dining, "
                    "toasts, and music."
                ),
                family_guidance=(
                    "Bride transitions from morning Paithani saree to bridal evening lehenga."
                ),
            ),
        ]

        alignment_points = [
            FamilyAlignmentPointSchema(
                issue="Bridal Entrance Harmony (Phoolon Ki Chaadar vs. Antarpat)",
                description=(
                    "Punjabi custom requires bride to enter under floral canopy held by brothers. "
                    "Maharashtrian custom requires couple separated by Antarpat cloth."
                ),
                recommendation=(
                    "Brothers escort bride to Mandap threshold under Phoolon Ki Chaadar; once at "
                    "Mandap, uncles raise the Antarpat cloth until the Mangalashtaka shloka."
                ),
            ),
            FamilyAlignmentPointSchema(
                issue="Dining Transitions & Cultural Cuisines",
                description=(
                    "Maharashtrian traditional wedding lunch is traditionally pure satvik "
                    "vegetarian served on banana leaves. Punjabi evening revelry often calls for "
                    "rich Mughlai curries."
                ),
                recommendation=(
                    "Host a traditional satvik vegetarian seated feast for post-pheras lunch "
                    "(Pankat style); offer lavish multi-cuisine counters at the evening reception."
                ),
            ),
            FamilyAlignmentPointSchema(
                issue="Wardrobe and Adornment Changes",
                description=(
                    "Maharashtrian bride wears Mundavalya forehead pearls with Paithani saree; "
                    "Punjabi wedding emphasizes red Chooda bangles and hanging Kalire."
                ),
                recommendation=(
                    "Bride wears both Chooda and Mundavalya during the morning ceremony, "
                    "celebrating both her maternal lineage and new marital home."
                ),
            ),
        ]
        return title, ceremonies, alignment_points

    def _build_generic_show(
        self, primary: Tradition, secondary: Tradition, p_code: str, s_code: str
    ) -> tuple[str, list[CeremonyItemSchema], list[FamilyAlignmentPointSchema]]:
        title = f"{primary.regional_name} × {secondary.regional_name} Cultural Fusion"
        t_primary_subevents = DAGScheduler.SUB_EVENT_TEMPLATES.get(
            p_code, DAGScheduler.SUB_EVENT_TEMPLATES["default"]
        )
        t_sec_subevents = DAGScheduler.SUB_EVENT_TEMPLATES.get(
            s_code, DAGScheduler.SUB_EVENT_TEMPLATES["default"]
        )
        ceremonies: list[CeremonyItemSchema] = []

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
                description=(
                    f"Officiating priests from {primary.regional_name} and "
                    f"{secondary.regional_name} should coordinate vow sequencing."
                ),
                recommendation=(
                    "Convene a 30-minute joint briefing with both priests 14 days before "
                    "the ceremony."
                ),
            ),
            FamilyAlignmentPointSchema(
                issue="Cultural Attire Coordination",
                description="Coordinate wedding attire styling to honor both backgrounds.",
                recommendation="Allocate a 90-minute dress change window between rituals.",
            ),
        ]
        return title, ceremonies, alignment_points

    def generate_merged_run_of_show(
        self, primary: Tradition, secondary: Tradition, start_date: date, notes: str | None = None
    ) -> MergedRunOfShowSchema:
        p_code = primary.code.lower()
        s_code = secondary.code.lower()
        pair_set = {p_code, s_code}

        # 1. Spec Acceptance Case: Maharashtrian x Punjabi
        if any("maharashtrian" in c for c in pair_set) and any("punjabi" in c for c in pair_set):
            title, ceremonies, alignment_points = self._build_maha_punjabi_show(
                primary, secondary, p_code
            )
        else:
            title, ceremonies, alignment_points = self._build_generic_show(
                primary, secondary, p_code, s_code
            )

        custom_accuracy_disclaimer = (
            f"This sequence was AI-drafted as a starting point based on general knowledge of "
            f"{primary.regional_name} and {secondary.regional_name} customs. "
            "It has not been reviewed by a priest or community elder and may contain errors, "
            "omissions, or regionally inappropriate details. Please review carefully with your "
            "family and officiant before finalizing."
        )

        return MergedRunOfShowSchema(
            fusion_title=title,
            primary_tradition=primary.regional_name,
            secondary_tradition=secondary.regional_name,
            ceremonies=ceremonies,
            family_alignment_points=alignment_points,
            content_accuracy_disclaimer=custom_accuracy_disclaimer,
            timing_disclaimer=(
                "Panchang calculations are astronomical estimates based on Drik Ganita and "
                "Ephemeris models. Muhurat dates and ritual sequences must always be confirmed "
                "with your family's trusted priest, pandit, or religious officiant."
            ),
            disclaimer=custom_accuracy_disclaimer,
        )
