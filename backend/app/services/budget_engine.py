import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any, ClassVar, cast

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "city_tiers.json"


def load_city_tiers_config() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open(encoding="utf-8") as f:
            return cast(dict[str, Any], json.load(f))
    # Default fallback
    return {
        "multipliers": {"tier_1": 1.0, "tier_2": 0.68, "tier_3": 0.45},
        "city_to_tier": {"default": "tier_2"},
    }


class BudgetScalingEngine:
    """
    Deterministic Budget Scaling Engine.
    Rules:
    - Zero LLM math. All monetary calculations are performed deterministically.
    - Zero floating point drift: computes exact 2-decimal rounded shares and balances
      any residual to contingency.
    - Loads calibrated city-tier cost multipliers from config/city_tiers.json at runtime,
      not hardcoded literals.
    """

    ALLOCATION_MODELS: ClassVar[dict[str, dict[str, Decimal]]] = {
        "wedding": {
            "venue": Decimal("0.22"),
            "catering": Decimal("0.28"),
            "decor": Decimal("0.16"),
            "photography": Decimal("0.09"),
            "entertainment": Decimal("0.07"),
            "rituals": Decimal("0.04"),
            "wardrobe": Decimal("0.06"),
            "logistics": Decimal("0.04"),
            "contingency": Decimal("0.04"),
        },
        "puja": {
            "rituals": Decimal("0.32"),
            "catering": Decimal("0.30"),
            "venue": Decimal("0.15"),
            "decor": Decimal("0.12"),
            "logistics": Decimal("0.05"),
            "contingency": Decimal("0.06"),
        },
        "community_festival": {
            "pandal_and_stage": Decimal("0.30"),
            "prasad_and_food": Decimal("0.24"),
            "sound_and_lighting": Decimal("0.18"),
            "security_and_permits": Decimal("0.10"),
            "decor": Decimal("0.10"),
            "contingency": Decimal("0.08"),
        },
        "birthday": {
            "venue": Decimal("0.20"),
            "catering": Decimal("0.32"),
            "decor": Decimal("0.16"),
            "entertainment": Decimal("0.12"),
            "cake_and_desserts": Decimal("0.08"),
            "photography": Decimal("0.06"),
            "contingency": Decimal("0.06"),
        },
        "milestone_anniversary": {
            "venue": Decimal("0.25"),
            "catering": Decimal("0.35"),
            "decor": Decimal("0.15"),
            "entertainment": Decimal("0.12"),
            "photography": Decimal("0.08"),
            "contingency": Decimal("0.05"),
        },
    }

    @classmethod
    def get_config(cls) -> dict[str, Any]:
        return load_city_tiers_config()

    @classmethod
    def resolve_city_tier(cls, city: str) -> str:
        cfg = cls.get_config()
        mapping = cfg.get("city_to_tier", {})
        cleaned = city.strip().lower()
        return str(mapping.get(cleaned, mapping.get("default", "tier_2")))

    @classmethod
    def get_city_tier(cls, city: str) -> str:
        return cls.resolve_city_tier(city)

    @classmethod
    def get_tier_multiplier(cls, tier: str) -> Decimal:
        cfg = cls.get_config()
        multipliers = cfg.get("multipliers", {})
        val = multipliers.get(tier, 1.0)
        return Decimal(str(val))

    @classmethod
    def _resolve_model_key(cls, event_type: str) -> str:
        raw_key = (event_type or "").lower().strip()
        if raw_key in cls.ALLOCATION_MODELS:
            return raw_key
        if "birthday" in raw_key:
            return "birthday"
        if any(
            k in raw_key for k in ("community", "festival", "mela", "society", "ganesh", "navratri")
        ):
            return "community_festival"
        if "anniversary" in raw_key:
            return "milestone_anniversary"
        if any(k in raw_key for k in ("puja", "pooja", "havan", "vrat", "griha")):
            return "puja"
        return "wedding"

    @classmethod
    def compute_budget_allocation(
        cls,
        total_envelope: float,
        event_type: str = "wedding",
        city: str = "Pune",
        guest_count: int = 350,
    ) -> list[dict[str, Any]]:
        if total_envelope <= 0:
            err_msg = "Total budget envelope must be strictly greater than 0"
            raise ValueError(err_msg)
        if guest_count <= 0:
            err_msg = "Guest count must be strictly greater than 0"
            raise ValueError(err_msg)

        tier = cls.resolve_city_tier(city)
        multiplier = cls.get_tier_multiplier(tier)
        model_key = cls._resolve_model_key(event_type)
        allocation_spec = cls.ALLOCATION_MODELS[model_key]

        envelope_dec = Decimal(str(total_envelope))
        scaled_envelope = (envelope_dec * multiplier).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        items = []
        running_total = Decimal("0.00")
        categories = list(allocation_spec.keys())

        # Allocate each category except the last (contingency), which absorbs any cent remainder
        for cat in categories[:-1]:
            percentage = allocation_spec[cat]
            amount = (scaled_envelope * percentage).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            running_total += amount
            items.append(
                {
                    "category": cat,
                    "percentage": float(percentage * 100),
                    "planned_amount": float(amount),
                    "city_tier": tier,
                    "city_tier_multiplier": float(multiplier),
                    "reasoning_spec": {
                        "formula": f"{float(scaled_envelope)} * {float(percentage)}",
                        "city_tier": tier,
                        "guest_count": guest_count,
                        "benchmark_basis": (
                            f"Standard Indian {model_key} allocation benchmark model"
                        ),
                    },
                }
            )

        # Final category absorbs residual difference
        last_cat = categories[-1]
        last_percentage = allocation_spec[last_cat]
        remainder_amount = scaled_envelope - running_total
        items.append(
            {
                "category": last_cat,
                "percentage": float(last_percentage * 100),
                "planned_amount": float(remainder_amount),
                "city_tier": tier,
                "city_tier_multiplier": float(multiplier),
                "reasoning_spec": {
                    "formula": f"Residual balance of {float(scaled_envelope)}",
                    "city_tier": tier,
                    "guest_count": guest_count,
                    "benchmark_basis": (
                        "Contingency buffer calibrated for unexpected "
                        "vendor overtime/generator fuel"
                    ),
                },
            }
        )

        return items
