from typing import Dict, List, Any, Optional
from decimal import Decimal, ROUND_HALF_UP


class BudgetScalingEngine:
    """
    Deterministic Budget Scaling Engine.
    Rules:
    - Zero LLM math. All monetary calculations are performed deterministically.
    - Zero floating point drift: computes exact 2-decimal rounded shares and balances any residual to contingency.
    - Applies calibrated city-tier cost multipliers.
    """

    CITY_TIER_MULTIPLIERS = {
        "tier_1": Decimal("1.00"),  # Mumbai, Delhi NCR, Bengaluru, Pune, Hyderabad, Chennai, Kolkata
        "tier_2": Decimal("0.68"),  # Ahmedabad, Jaipur, Lucknow, Indore, Chandigarh, Kochi, Surat
        "tier_3": Decimal("0.45")   # Smaller municipal centers, suburban & rural hubs
    }

    CITY_TO_TIER = {
        "mumbai": "tier_1",
        "delhi": "tier_1",
        "delhi ncr": "tier_1",
        "bengaluru": "tier_1",
        "bangalore": "tier_1",
        "pune": "tier_1",
        "hyderabad": "tier_1",
        "chennai": "tier_1",
        "kolkata": "tier_1",
        "ahmedabad": "tier_2",
        "jaipur": "tier_2",
        "lucknow": "tier_2",
        "indore": "tier_2",
        "chandigarh": "tier_2",
        "kochi": "tier_2",
        "surat": "tier_2",
        "nagpur": "tier_2",
        "bhopal": "tier_2",
        "patna": "tier_2",
        "vadodara": "tier_2",
    }

    ALLOCATION_MODELS: Dict[str, Dict[str, Decimal]] = {
        "wedding": {
            "venue": Decimal("0.22"),
            "catering": Decimal("0.28"),
            "decor": Decimal("0.16"),
            "photography": Decimal("0.09"),
            "entertainment": Decimal("0.07"),
            "rituals": Decimal("0.04"),
            "wardrobe": Decimal("0.06"),
            "logistics": Decimal("0.04"),
            "contingency": Decimal("0.04")
        },
        "puja": {
            "rituals": Decimal("0.32"),
            "catering": Decimal("0.30"),
            "venue": Decimal("0.15"),
            "decor": Decimal("0.12"),
            "logistics": Decimal("0.05"),
            "contingency": Decimal("0.06")
        },
        "community_festival": {
            "pandal_and_stage": Decimal("0.30"),
            "prasad_and_food": Decimal("0.24"),
            "sound_and_lighting": Decimal("0.18"),
            "security_and_permits": Decimal("0.10"),
            "decor": Decimal("0.10"),
            "contingency": Decimal("0.08")
        },
        "milestone_anniversary": {
            "venue": Decimal("0.25"),
            "catering": Decimal("0.35"),
            "decor": Decimal("0.15"),
            "entertainment": Decimal("0.12"),
            "photography": Decimal("0.08"),
            "contingency": Decimal("0.05")
        }
    }

    @classmethod
    def resolve_city_tier(cls, city: str) -> str:
        cleaned = city.strip().lower()
        return cls.CITY_TO_TIER.get(cleaned, "tier_2")

    @classmethod
    def compute_budget_allocation(
        cls,
        total_envelope: float,
        event_type: str = "wedding",
        city: str = "Pune",
        guest_count: int = 350
    ) -> List[Dict[str, Any]]:
        if total_envelope <= 0:
            raise ValueError("Total budget envelope must be strictly greater than 0")
        if guest_count <= 0:
            raise ValueError("Guest count must be strictly greater than 0")

        tier = cls.resolve_city_tier(city)
        multiplier = cls.CITY_TIER_MULTIPLIERS[tier]
        model_key = event_type.lower() if event_type.lower() in cls.ALLOCATION_MODELS else "wedding"
        allocation_spec = cls.ALLOCATION_MODELS[model_key]

        envelope_dec = Decimal(str(total_envelope))
        scaled_envelope = (envelope_dec * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        items = []
        running_total = Decimal("0.00")
        categories = list(allocation_spec.keys())

        # Allocate each category except the last (contingency), which absorbs any cent remainder
        for cat in categories[:-1]:
            percentage = allocation_spec[cat]
            amount = (scaled_envelope * percentage).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            running_total += amount
            items.append({
                "category": cat,
                "percentage": float(percentage * 100),
                "planned_amount": float(amount),
                "city_tier": tier,
                "city_tier_multiplier": float(multiplier),
                "reasoning_spec": {
                    "formula": f"{float(scaled_envelope)} * {float(percentage)}",
                    "city_tier": tier,
                    "guest_count": guest_count,
                    "benchmark_basis": f"Standard Indian {model_key} allocation benchmark model"
                }
            })

        # Final category absorbs residual difference
        last_cat = categories[-1]
        last_percentage = allocation_spec[last_cat]
        remainder_amount = scaled_envelope - running_total
        items.append({
            "category": last_cat,
            "percentage": float(last_percentage * 100),
            "planned_amount": float(remainder_amount),
            "city_tier": tier,
            "city_tier_multiplier": float(multiplier),
            "reasoning_spec": {
                "formula": f"Residual balance of {float(scaled_envelope)}",
                "city_tier": tier,
                "guest_count": guest_count,
                "benchmark_basis": "Contingency buffer calibrated for unexpected vendor overtime/generator fuel"
            }
        })

        return items
