import os
import json
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
from pydantic import BaseModel, Field

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "tier_breakpoints.json")


class BudgetItemDiff(BaseModel):
    budget_item_id: str
    category: str
    name: str
    scaling_rule: str  # per_guest, fixed, tiered
    old_amount: float
    new_amount: float
    difference: float
    formula: str


class BudgetRescalingResult(BaseModel):
    items: List[BudgetItemDiff]
    total_old: float
    total_new: float
    total_delta: float
    venue_capacity: Optional[int] = None
    capacity_exceeded: bool = False
    capacity_delta: int = 0
    capacity_warning: Optional[str] = None


class BudgetRescalingEngine:
    _tiers_cache: Dict[str, Any] = {}

    @classmethod
    def load_tier_config(cls) -> Dict[str, Any]:
        if not cls._tiers_cache:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cls._tiers_cache = json.load(f)
            else:
                cls._tiers_cache = {}
        return cls._tiers_cache

    @classmethod
    def get_tier_info(cls, category: str, guest_count: int) -> Tuple[float, str]:
        cfg = cls.load_tier_config().get(category.lower())
        if not cfg or "tiers" not in cfg:
            return 1.0, f"Standard ({guest_count} guests)"

        for t in cfg["tiers"]:
            if guest_count <= t["max_guests"]:
                return float(t["multiplier"]), t["tier_name"]

        # Default fallback to last tier
        last = cfg["tiers"][-1]
        return float(last["multiplier"]), last["tier_name"]

    @classmethod
    def rescale_for_guest_count_change(
        cls,
        old_guest_count: int,
        new_guest_count: int,
        budget_items: List[Any],
        venue_capacity: Optional[int] = None
    ) -> BudgetRescalingResult:
        """
        Deterministic recomputation of budget items when guest count changes.
        Zero LLM math. Formula strictly exposed per item.
        """
        if old_guest_count <= 0:
            raise ValueError(f"old_guest_count must be > 0 (received {old_guest_count})")
        if new_guest_count <= 0:
            raise ValueError(f"new_guest_count must be > 0 (received {new_guest_count})")

        diffs: List[BudgetItemDiff] = []
        total_old = 0.0
        total_new = 0.0

        for b in budget_items:
            b_id = getattr(b, "id", "")
            cat = (getattr(b, "category", "") or "other").lower()
            name = getattr(b, "name", "")
            rule = (getattr(b, "scaling_rule", "") or "per_guest").lower()
            old_amt = float(getattr(b, "planned_amount", 0.0) or 0.0)
            total_old += old_amt

            if rule == "per_guest":
                ratio = new_guest_count / old_guest_count
                new_amt = round(old_amt * ratio, 2)
                formula = f"{cat}: {old_amt:.2f} * ({new_guest_count}/{old_guest_count}) = {new_amt:.2f}"
            elif rule == "tiered":
                old_mult, old_tier = cls.get_tier_info(cat, old_guest_count)
                new_mult, new_tier = cls.get_tier_info(cat, new_guest_count)
                step_ratio = new_mult / old_mult if old_mult > 0 else 1.0
                new_amt = round(old_amt * step_ratio, 2)
                if old_tier != new_tier:
                    formula = f"{cat}: {old_amt:.2f} * ({new_mult:.2f}/{old_mult:.2f}) = {new_amt:.2f} (Stepped from '{old_tier}' to '{new_tier}')"
                else:
                    formula = f"{cat}: {old_amt:.2f} * ({new_mult:.2f}/{old_mult:.2f}) = {new_amt:.2f} (Remains in '{old_tier}')"
            else:  # fixed or unknown
                new_amt = old_amt
                formula = f"{cat}: {old_amt:.2f} * (Fixed contract rate) = {new_amt:.2f}"

            diff_val = round(new_amt - old_amt, 2)
            total_new += new_amt

            diffs.append(
                BudgetItemDiff(
                    budget_item_id=b_id,
                    category=cat,
                    name=name,
                    scaling_rule=rule,
                    old_amount=old_amt,
                    new_amount=new_amt,
                    difference=diff_val,
                    formula=formula
                )
            )

        total_old = round(total_old, 2)
        total_new = round(total_new, 2)
        total_delta = round(total_new - total_old, 2)

        # Capacity check
        capacity_exceeded = False
        capacity_delta = 0
        capacity_warning = None
        if venue_capacity is not None and venue_capacity > 0:
            if new_guest_count > venue_capacity:
                capacity_exceeded = True
                capacity_delta = new_guest_count - venue_capacity
                capacity_warning = (
                    f"CRITICAL CAPACITY ALERT: Revised guest count ({new_guest_count}) exceeds venue capacity "
                    f"({venue_capacity}) by {capacity_delta} guests. Risk of fire-code violation and overcrowding."
                )

        return BudgetRescalingResult(
            items=diffs,
            total_old=total_old,
            total_new=total_new,
            total_delta=total_delta,
            venue_capacity=venue_capacity,
            capacity_exceeded=capacity_exceeded,
            capacity_delta=capacity_delta,
            capacity_warning=capacity_warning
        )

    @classmethod
    def rescale_for_budget_cut(
        cls,
        from_budget: float,
        to_budget: float,
        budget_items: List[Any]
    ) -> BudgetRescalingResult:
        """
        Proportionally scales down flexible/unpaid budget items when a budget cut is declared.
        Protects committed/paid items.
        """
        if to_budget >= from_budget:
            raise ValueError(f"to_budget ({to_budget}) must be strictly less than from_budget ({from_budget})")
        if to_budget <= 0:
            raise ValueError(f"to_budget must be positive (received {to_budget})")

        diffs: List[BudgetItemDiff] = []
        total_old = 0.0
        total_new = 0.0

        # Calculate committed vs flexible pools
        flexible_items = []
        committed_total = 0.0
        for b in budget_items:
            amt = float(getattr(b, "planned_amount", 0.0) or 0.0)
            total_old += amt
            is_paid = getattr(b, "is_paid", False)
            actual_amt = float(getattr(b, "actual_amount", 0.0) or 0.0)
            if is_paid or actual_amt > 0:
                committed_total += amt
            else:
                flexible_items.append(b)

        flexible_old_total = sum(float(getattr(b, "planned_amount", 0.0) or 0.0) for b in flexible_items)
        target_flexible_total = max(0.0, to_budget - committed_total)
        cut_ratio = target_flexible_total / flexible_old_total if flexible_old_total > 0 else (to_budget / from_budget)

        for b in budget_items:
            b_id = getattr(b, "id", "")
            cat = (getattr(b, "category", "") or "other").lower()
            name = getattr(b, "name", "")
            rule = (getattr(b, "scaling_rule", "") or "fixed").lower()
            old_amt = float(getattr(b, "planned_amount", 0.0) or 0.0)
            is_paid = getattr(b, "is_paid", False)
            actual_amt = float(getattr(b, "actual_amount", 0.0) or 0.0)

            if is_paid or actual_amt > 0:
                new_amt = old_amt
                formula = f"{cat}: {old_amt:.2f} * (Locked/Paid item - non-reducible) = {new_amt:.2f}"
            else:
                new_amt = round(old_amt * cut_ratio, 2)
                formula = f"{cat}: {old_amt:.2f} * (Flexible cut ratio {cut_ratio:.4f}) = {new_amt:.2f}"

            diff_val = round(new_amt - old_amt, 2)
            total_new += new_amt

            diffs.append(
                BudgetItemDiff(
                    budget_item_id=b_id,
                    category=cat,
                    name=name,
                    scaling_rule=rule,
                    old_amount=old_amt,
                    new_amount=new_amt,
                    difference=diff_val,
                    formula=formula
                )
            )

        total_old = round(total_old, 2)
        total_new = round(total_new, 2)
        total_delta = round(total_new - total_old, 2)

        return BudgetRescalingResult(
            items=diffs,
            total_old=total_old,
            total_new=total_new,
            total_delta=total_delta
        )
