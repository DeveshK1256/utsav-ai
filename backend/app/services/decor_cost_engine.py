import json
import math
import re
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "city_tiers.json"


def get_city_multiplier(city: str) -> float:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
            c_norm = (city or "").strip().lower()
            tier_name = cfg.get("city_to_tier", {}).get(c_norm, cfg.get("city_to_tier", {}).get("default", "tier_2"))
            return float(cfg.get("multipliers", {}).get(tier_name, 0.68))
    return 0.68


class DecorCostEngine:
    """
    Deterministic quantity and cost resolution engine for decor items.
    Translates LLM-suggested formulas and cost tiers into exact INR ranges.
    Zero LLM math. All monetary calculations are performed in code.
    """

    STRUCTURAL_CATEGORIES = {"mandap", "stage_backdrop", "entrance_arch", "photobooth", "ceiling_drapes"}
    SERVICE_CATEGORIES = {"cultural_performance"}
    DISTRIBUTED_CATEGORIES = {"lighting", "seating_lounges", "table_centerpiece", "default"}

    BASE_UNIT_COSTS: dict[str, dict[str, tuple[float, float]]] = {
        # Structural Installations (typically 1-2 fixed units per celebration)
        "mandap": {
            "low": (25000.0, 45000.0),
            "medium": (45000.0, 75000.0),
            "high": (85000.0, 150000.0),
        },
        "stage_backdrop": {
            "low": (15000.0, 25000.0),
            "medium": (28000.0, 45000.0),
            "high": (55000.0, 95000.0),
        },
        "entrance_arch": {
            "low": (8000.0, 14000.0),
            "medium": (16000.0, 26000.0),
            "high": (30000.0, 50000.0),
        },
        "photobooth": {
            "low": (7000.0, 12000.0),
            "medium": (14000.0, 22000.0),
            "high": (28000.0, 45000.0),
        },
        "ceiling_drapes": {
            "low": (8000.0, 15000.0),
            "medium": (16000.0, 28000.0),
            "high": (32000.0, 55000.0),
        },

        # Cultural Services & Live Traditional Welcome Acts
        "cultural_performance": {
            "low": (4000.0, 8000.0),
            "medium": (8000.0, 15000.0),
            "high": (16000.0, 30000.0),
        },

        # Distributed Per-Unit Items (scale with guest count, tables, or counts)
        "lighting": {
            "low": (400.0, 800.0),
            "medium": (900.0, 1600.0),
            "high": (2000.0, 3600.0),
        },
        "seating_lounges": {
            "low": (800.0, 1500.0),
            "medium": (1800.0, 3200.0),
            "high": (3500.0, 6000.0),
        },
        "table_centerpiece": {
            "low": (400.0, 750.0),
            "medium": (1000.0, 1800.0),
            "high": (2200.0, 4200.0),
        },
        "default": {
            "low": (350.0, 700.0),
            "medium": (800.0, 1500.0),
            "high": (1800.0, 3200.0),
        }
    }

    # Rates for standalone fixed accent/display items when categorized under 'default'
    # Prevents 1-off focal pieces (e.g. welcome easel, brass display) from resolving to 1x distributed trinket rates
    STANDALONE_DEFAULT_COSTS: dict[str, tuple[float, float]] = {
        "low": (1800.0, 3200.0),
        "medium": (3500.0, 6500.0),
        "high": (7500.0, 14000.0),
    }

    # Defensive absolute floors for any standalone/fixed line item before city multiplier
    MIN_STANDALONE_FLOOR: dict[str, tuple[float, float]] = {
        "low": (1200.0, 2200.0),
        "medium": (2400.0, 4200.0),
        "high": (4800.0, 8500.0),
    }

    LIGHTING_PACKAGE_COSTS: dict[str, tuple[float, float]] = {
        "low": (12000.0, 20000.0),
        "medium": (22000.0, 38000.0),
        "high": (45000.0, 75000.0),
    }

    @classmethod
    def resolve_quantity_formula(cls, formula_str: str, guest_count: int, table_size: int = 10) -> int:
        """
        Parses formula string and calculates integer quantity from event guest_count.
        Examples:
          "1 per 10 guests" -> ceil(guest_count / 10)
          "1 per table" -> ceil(guest_count / table_size)
          "2 units" or "2 fixed" -> 2
        """
        if not formula_str or not isinstance(formula_str, str):
            return 1

        f_lower = formula_str.lower().strip()

        # Check "1 per X guests" or "X per Y guests"
        per_guest_match = re.search(r"(\d+)\s*per\s*(\d+)\s*guest", f_lower)
        if per_guest_match:
            qty_mult = int(per_guest_match.group(1))
            step = int(per_guest_match.group(2))
            if step > 0:
                return max(1, math.ceil(guest_count / step) * qty_mult)

        # Check "1 per table"
        if "table" in f_lower:
            tables = max(1, math.ceil(guest_count / table_size))
            return tables

        # Check explicit integer e.g. "4 units", "2 fixed", "3 backdrops"
        unit_match = re.search(r"^(\d+)", f_lower)
        if unit_match:
            return max(1, int(unit_match.group(1)))

        return 1

    @classmethod
    def resolve_cost_range(
        cls,
        category: str,
        cost_tier: str,
        computed_quantity: int = 1,
        city: str = "pune",
        quantity: int | None = None,
        formula_str: str | None = None
    ) -> tuple[float, float]:
        """
        Resolves unit cost based on category and tier, applies city multiplier,
        and multiplies by computed quantity.
        Enforces defensive sanity floors so standalone items never collapse below minimum viable market rates.
        """
        qty = quantity if quantity is not None else computed_quantity
        cat_clean = (category or "").lower().strip()
        tier_clean = (cost_tier or "medium").lower().strip()
        if tier_clean not in ("low", "medium", "high"):
            tier_clean = "medium"

        formula_lower = (formula_str or "").lower().strip()
        is_fixed = (qty == 1) or ("fixed" in formula_lower)

        # 1. Package lighting
        if cat_clean == "lighting" and is_fixed and any(w in formula_lower for w in ("package", "venue", "full")):
            cat_costs = cls.LIGHTING_PACKAGE_COSTS
            low_unit, high_unit = cat_costs.get(tier_clean, cat_costs["medium"])
        # 2. Standalone fixed default items (focal displays, welcome accents)
        elif cat_clean == "default" and is_fixed:
            low_unit, high_unit = cls.STANDALONE_DEFAULT_COSTS.get(tier_clean, cls.STANDALONE_DEFAULT_COSTS["medium"])
        # 3. Standard category resolution
        else:
            cat_costs = cls.BASE_UNIT_COSTS.get(cat_clean, cls.BASE_UNIT_COSTS["default"])
            low_unit, high_unit = cat_costs.get(tier_clean, cat_costs["medium"])

        city_mult = get_city_multiplier(city)

        total_low = round(low_unit * city_mult * qty, 2)
        total_high = round(high_unit * city_mult * qty, 2)

        # 4. Defensive floor guard: ensure fixed/standalone items never collapse below viable vendor cost
        if is_fixed:
            min_floor_low, min_floor_high = cls.MIN_STANDALONE_FLOOR.get(tier_clean, cls.MIN_STANDALONE_FLOOR["medium"])
            scaled_floor_low = round(min_floor_low * city_mult, 2)
            scaled_floor_high = round(min_floor_high * city_mult, 2)
            total_low = max(total_low, scaled_floor_low)
            total_high = max(total_high, scaled_floor_high)

        return (total_low, total_high)

    calculate_cost_range = resolve_cost_range
