import json
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel

from backend.app.models.models import BudgetItem

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "tier_breakpoints.json"


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
    items: list[BudgetItemDiff]
    total_old: float
    total_new: float
    total_delta: float
    venue_capacity: int | None = None
    capacity_exceeded: bool = False
    capacity_delta: int = 0
    capacity_warning: str | None = None


class BudgetRescalingEngine:
    _tiers_cache: ClassVar[dict[str, Any]] = {}

    @classmethod
    def load_tier_config(cls) -> dict[str, Any]:
        if not cls._tiers_cache:
            if CONFIG_PATH.exists():
                with CONFIG_PATH.open(encoding="utf-8") as f:
                    cls._tiers_cache = json.load(f)
            else:
                cls._tiers_cache = {}
        return cls._tiers_cache

    @classmethod
    def resolve_scaling_rule(cls, category: str) -> str:
        """
        Canonical mapping of event budget categories to deterministic scaling rules per DEC-018.
        - Fixed: venue, photography, entertainment, rituals, ritual_priest
        - Tiered: decor, sound_light, sound_and_lighting
        - Per-guest: catering, rentals, wardrobe, logistics, gifts_favors, invitations, contingency
        """
        cat = (category or "").lower().strip()
        if cat in {
            "venue",
            "photography",
            "entertainment",
            "rituals",
            "ritual_priest",
            "security_and_permits",
        }:
            return "fixed"
        if cat in {"decor", "sound_light", "sound_and_lighting", "pandal_and_stage"}:
            return "tiered"
        return "per_guest"

    @classmethod
    def get_tier_info(cls, category: str, guest_count: int) -> tuple[float, str]:
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
    def _rescale_single_guest_item(
        cls, b: BudgetItem, old_guest_count: int, new_guest_count: int
    ) -> BudgetItemDiff:
        b_id = getattr(b, "id", "")
        cat = (getattr(b, "category", "") or "other").lower()
        name = getattr(b, "name", "")
        stored_rule = getattr(b, "scaling_rule", None)

        canonical_rule = cls.resolve_scaling_rule(cat)
        if not stored_rule or (
            stored_rule.lower() == "per_guest" and canonical_rule != "per_guest"
        ):
            rule = canonical_rule
        else:
            rule = stored_rule.lower()

        old_amt = float(getattr(b, "planned_amount", 0.0) or 0.0)

        if rule == "per_guest":
            ratio = new_guest_count / old_guest_count
            new_amt = round(old_amt * ratio, 2)
            formula = (
                f"{cat}: {old_amt:.2f} * ({new_guest_count}/{old_guest_count}) = {new_amt:.2f}"
            )
        elif rule == "tiered":
            old_mult, old_tier = cls.get_tier_info(cat, old_guest_count)
            new_mult, new_tier = cls.get_tier_info(cat, new_guest_count)
            step_ratio = new_mult / old_mult if old_mult > 0 else 1.0
            new_amt = round(old_amt * step_ratio, 2)
            if old_tier != new_tier:
                formula = (
                    f"{cat}: Stepped from '{old_tier}' to '{new_tier}' "
                    f"({old_guest_count}→{new_guest_count} guests, "
                    f"{old_mult:.2f}x→{new_mult:.2f}x) = ₹{new_amt:,.2f}"
                )
            else:
                formula = (
                    f"{cat}: Remains in '{old_tier}' "
                    f"({old_guest_count}→{new_guest_count} guests), no change (₹{new_amt:,.2f})"
                )
        else:
            new_amt = old_amt
            formula = f"{cat}: {old_amt:.2f} * (Fixed contract rate) = {new_amt:.2f}"

        return BudgetItemDiff(
            budget_item_id=b_id,
            category=cat,
            name=name,
            scaling_rule=rule,
            old_amount=old_amt,
            new_amount=new_amt,
            difference=round(new_amt - old_amt, 2),
            formula=formula,
        )

    @classmethod
    def rescale_for_guest_count_change(
        cls,
        old_guest_count: int,
        new_guest_count: int,
        budget_items: list[Any],
        venue_capacity: int | None = None,
    ) -> BudgetRescalingResult:
        """
        Deterministic recomputation of budget items when guest count changes.
        Zero LLM math. Formula strictly exposed per item.
        """
        if old_guest_count <= 0:
            err_msg = f"old_guest_count must be > 0 (received {old_guest_count})"
            raise ValueError(err_msg)
        if new_guest_count <= 0:
            err_msg = f"new_guest_count must be > 0 (received {new_guest_count})"
            raise ValueError(err_msg)

        diffs = [
            cls._rescale_single_guest_item(b, old_guest_count, new_guest_count)
            for b in budget_items
        ]
        total_old = round(sum(d.old_amount for d in diffs), 2)
        total_new = round(sum(d.new_amount for d in diffs), 2)
        total_delta = round(total_new - total_old, 2)

        capacity_exceeded = False
        capacity_delta = 0
        capacity_warning = None

        if venue_capacity is not None and venue_capacity > 0 and new_guest_count > venue_capacity:
            capacity_exceeded = True
            capacity_delta = new_guest_count - venue_capacity
            capacity_warning = (
                f"CRITICAL CAPACITY ALERT: Revised guest count ({new_guest_count}) exceeds "
                f"venue capacity ({venue_capacity}) by {capacity_delta} guests. "
                "Risk of fire-code violation and overcrowding."
            )

        return BudgetRescalingResult(
            items=diffs,
            total_old=total_old,
            total_new=total_new,
            total_delta=total_delta,
            venue_capacity=venue_capacity,
            capacity_exceeded=capacity_exceeded,
            capacity_delta=capacity_delta,
            capacity_warning=capacity_warning,
        )

    @classmethod
    def _calculate_cut_ratio(
        cls, from_budget: float, to_budget: float, budget_items: list[Any]
    ) -> float:
        committed_total = 0.0
        flexible_items = []
        for b in budget_items:
            amt = float(getattr(b, "planned_amount", 0.0) or 0.0)
            is_paid = getattr(b, "is_paid", False)
            actual_amt = float(getattr(b, "actual_amount", 0.0) or 0.0)
            if is_paid or actual_amt > 0:
                committed_total += amt
            else:
                flexible_items.append(b)

        flexible_old_total = sum(
            float(getattr(b, "planned_amount", 0.0) or 0.0) for b in flexible_items
        )
        target_flexible_total = max(0.0, to_budget - committed_total)
        if flexible_old_total > 0:
            return target_flexible_total / flexible_old_total
        return to_budget / from_budget

    @classmethod
    def _rescale_single_cut_item(cls, b: BudgetItem, cut_ratio: float) -> BudgetItemDiff:
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

        return BudgetItemDiff(
            budget_item_id=b_id,
            category=cat,
            name=name,
            scaling_rule=rule,
            old_amount=old_amt,
            new_amount=new_amt,
            difference=round(new_amt - old_amt, 2),
            formula=formula,
        )

    @classmethod
    def rescale_for_budget_cut(
        cls, from_budget: float, to_budget: float, budget_items: list[Any]
    ) -> BudgetRescalingResult:
        """
        Proportionally scales down flexible/unpaid budget items when a budget cut is declared.
        Protects committed/paid items.
        """
        if to_budget >= from_budget:
            err_msg = (
                f"to_budget ({to_budget}) must be strictly less than from_budget ({from_budget})"
            )
            raise ValueError(err_msg)
        if to_budget <= 0:
            err_msg = f"to_budget must be positive (received {to_budget})"
            raise ValueError(err_msg)

        cut_ratio = cls._calculate_cut_ratio(from_budget, to_budget, budget_items)
        diffs = [cls._rescale_single_cut_item(b, cut_ratio) for b in budget_items]

        total_old = round(sum(d.old_amount for d in diffs), 2)
        total_new = round(sum(d.new_amount for d in diffs), 2)
        total_delta = round(total_new - total_old, 2)

        return BudgetRescalingResult(
            items=diffs,
            total_old=total_old,
            total_new=total_new,
            total_delta=total_delta,
            venue_capacity=None,
            capacity_exceeded=False,
            capacity_delta=0,
            capacity_warning=None,
        )
