import os
import re
import math
import json
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "city_tiers.json"


def get_city_multiplier(city: str) -> float:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
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

    STRUCTURAL_CATEGORIES = {"mandap", "stage_backdrop", "entrance_arch", "photobooth"}
    DISTRIBUTED_CATEGORIES = {"lighting", "seating_lounges", "table_centerpiece", "default"}

    BASE_UNIT_COSTS: Dict[str, Dict[str, Tuple[float, float]]] = {
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

    LIGHTING_PACKAGE_COSTS: Dict[str, Tuple[float, float]] = {
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
        quantity: Optional[int] = None,
        formula_str: Optional[str] = None
    ) -> Tuple[float, float]:
        """
        Resolves unit cost based on category and tier, applies city multiplier,
        and multiplies by computed quantity.
        """
        qty = quantity if quantity is not None else computed_quantity
        cat_clean = (category or "").lower().strip()
        tier_clean = (cost_tier or "medium").lower().strip()
        if tier_clean not in ("low", "medium", "high"):
            tier_clean = "medium"

        # Check if lighting is a one-off full-venue package or a distributed fixture
        if cat_clean == "lighting" and qty == 1 and formula_str and any(w in formula_str.lower() for w in ("package", "venue", "full")):
            cat_costs = cls.LIGHTING_PACKAGE_COSTS
            low_unit, high_unit = cat_costs.get(tier_clean, cat_costs["medium"])
        else:
            cat_costs = cls.BASE_UNIT_COSTS.get(cat_clean, cls.BASE_UNIT_COSTS["default"])
            low_unit, high_unit = cat_costs.get(tier_clean, cat_costs["medium"])

        city_mult = get_city_multiplier(city)

        total_low = round(low_unit * city_mult * qty, 2)
        total_high = round(high_unit * city_mult * qty, 2)

        return (total_low, total_high)

    calculate_cost_range = resolve_cost_range
