from datetime import date
from typing import Any

from backend.app.models.models import Event
from backend.app.services.budget_rescaling_engine import BudgetRescalingEngine
from backend.app.services.dag import DAGScheduler


class ProposalBuilders:
    @classmethod
    def _build_guest_count_proposal(cls, event: Event, payload: dict[str, Any]) -> dict[str, Any]:
        from_g = int(payload.get("from_guest_count", event.guest_count))
        to_g = int(payload.get("to_guest_count") or event.guest_count or 100)
        result = BudgetRescalingEngine.rescale_for_guest_count_change(
            old_guest_count=from_g,
            new_guest_count=to_g,
            budget_items=event.budget_items,
            venue_capacity=event.venue_capacity,
        )
        budget_diffs = [item.model_dump() for item in result.items]
        vendor_re_quote_cats = []
        if to_g > from_g:
            vendor_re_quote_cats = [
                d["category"]
                for d in budget_diffs
                if d["scaling_rule"] in ("per_guest", "tiered") and d["difference"] > 0
            ]
        return {
            "budget_diffs": budget_diffs,
            "budget_old": result.total_old,
            "budget_new": result.total_new,
            "budget_delta": result.total_delta,
            "capacity_warning": result.capacity_warning,
            "task_diff": {"added_tasks": [], "moved_tasks": [], "cancelled_tasks": []},
            "sub_event_diffs": [],
            "vendor_re_quote_cats": vendor_re_quote_cats,
        }

    @classmethod
    def _build_vendor_cancelled_proposal(
        cls, event: Event, payload: dict[str, Any]
    ) -> dict[str, Any]:
        cat = payload.get("category", "vendor")
        v_name = payload.get("vendor_name", "Vendor")
        task_diff = {
            "added_tasks": [
                {
                    "title": f"Urgent: Settle replacement for {cat} ({v_name})",
                    "description": (
                        f"Vendor {v_name} cancelled. "
                        f"Procure replacement quotes for {cat} immediately."
                    ),
                    "assigned_role": "Procurement Lead",
                    "duration_minutes": 120,
                }
            ],
            "moved_tasks": [],
            "cancelled_tasks": [],
        }
        budget_diffs: list[dict[str, Any]] = []
        for b in event.budget_items:
            if (b.category or "").lower() == cat.lower():
                b_amt = float(b.planned_amount or 0.0)
                budget_diffs.append(
                    {
                        "budget_item_id": b.id,
                        "category": b.category,
                        "name": b.name,
                        "scaling_rule": b.scaling_rule or "fixed",
                        "old_amount": b_amt,
                        "new_amount": b_amt,
                        "difference": 0.0,
                        "formula": (
                            f"{cat}: Replacement required — original planned allocation "
                            f"₹{b_amt:,.2f} preserved for re-contracting"
                        ),
                    }
                )
        return {
            "budget_diffs": budget_diffs,
            "budget_old": float(event.total_budget),
            "budget_new": float(event.total_budget),
            "budget_delta": 0.0,
            "capacity_warning": None,
            "task_diff": task_diff,
            "sub_event_diffs": [],
            "vendor_re_quote_cats": [cat],
        }

    @classmethod
    def _build_date_moved_proposal(cls, event: Event, payload: dict[str, Any]) -> dict[str, Any]:
        from_d = date.fromisoformat(str(payload.get("from_date")))
        to_d = date.fromisoformat(str(payload.get("to_date")))
        days_delta = (to_d - from_d).days
        payload["days_shifted"] = days_delta

        moved_tasks = DAGScheduler.shift_tasks_for_date_moved(event.tasks, days_delta)
        sub_event_diffs = DAGScheduler.shift_sub_events_for_date_moved(event.sub_events, days_delta)
        return {
            "budget_diffs": [],
            "budget_old": float(event.total_budget),
            "budget_new": float(event.total_budget),
            "budget_delta": 0.0,
            "capacity_warning": None,
            "task_diff": {
                "added_tasks": [],
                "moved_tasks": moved_tasks,
                "cancelled_tasks": [],
            },
            "sub_event_diffs": sub_event_diffs,
            "vendor_re_quote_cats": [],
        }

    @classmethod
    def _build_budget_cut_proposal(cls, event: Event, payload: dict[str, Any]) -> dict[str, Any]:
        from_b = float(payload.get("from_budget", float(event.total_budget)))
        to_b = float(payload.get("to_budget") or float(event.total_budget))
        result = BudgetRescalingEngine.rescale_for_budget_cut(
            from_budget=from_b, to_budget=to_b, budget_items=event.budget_items
        )
        return {
            "budget_diffs": [item.model_dump() for item in result.items],
            "budget_old": result.total_old,
            "budget_new": result.total_new,
            "budget_delta": result.total_delta,
            "capacity_warning": None,
            "task_diff": {"added_tasks": [], "moved_tasks": [], "cancelled_tasks": []},
            "sub_event_diffs": [],
            "vendor_re_quote_cats": [],
        }

    @classmethod
    def _build_venue_unavailable_proposal(
        cls, event: Event, payload: dict[str, Any]
    ) -> dict[str, Any]:
        v_name = payload.get("venue_name", "Primary Venue")
        task_diff = {
            "added_tasks": [
                {
                    "title": f"Emergency: Scout replacement venues for {v_name}",
                    "description": (
                        f"Target capacity: {event.venue_capacity or event.guest_count} guests "
                        f"in {event.city}."
                    ),
                    "assigned_role": "Host",
                    "duration_minutes": 240,
                },
                {
                    "title": "Conduct emergency replacement venue site inspections",
                    "description": (
                        "Verify acoustics, fire safety, and stage layout for muhurat timings."
                    ),
                    "assigned_role": "Logistics Lead",
                    "duration_minutes": 180,
                },
            ],
            "moved_tasks": [],
            "cancelled_tasks": [],
        }
        budget_diffs: list[dict[str, Any]] = []
        for b in event.budget_items:
            if (b.category or "").lower() == "venue":
                b_amt = float(b.planned_amount or 0.0)
                budget_diffs.append(
                    {
                        "budget_item_id": b.id,
                        "category": b.category,
                        "name": b.name,
                        "scaling_rule": b.scaling_rule or "fixed",
                        "old_amount": b_amt,
                        "new_amount": b_amt,
                        "difference": 0.0,
                        "formula": (
                            "venue: Replacement venue required — current budget allocation "
                            f"₹{b_amt:,.2f} preserved for new contract"
                        ),
                    }
                )
        return {
            "budget_diffs": budget_diffs,
            "budget_old": float(event.total_budget),
            "budget_new": float(event.total_budget),
            "budget_delta": 0.0,
            "capacity_warning": None,
            "task_diff": task_diff,
            "sub_event_diffs": [],
            "vendor_re_quote_cats": ["venue"],
        }

    @classmethod
    def _dispatch_proposal_builder(
        cls, event: Event, change_type: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        builders = {
            "guest_count_changed": cls._build_guest_count_proposal,
            "vendor_cancelled": cls._build_vendor_cancelled_proposal,
            "date_moved": cls._build_date_moved_proposal,
            "budget_cut": cls._build_budget_cut_proposal,
            "venue_unavailable": cls._build_venue_unavailable_proposal,
        }
        builder = builders.get(change_type)
        if builder:
            return builder(event, payload)
        return {
            "budget_diffs": [],
            "budget_old": float(event.total_budget),
            "budget_new": float(event.total_budget),
            "budget_delta": 0.0,
            "capacity_warning": None,
            "task_diff": {"added_tasks": [], "moved_tasks": [], "cancelled_tasks": []},
            "sub_event_diffs": [],
            "vendor_re_quote_cats": [],
        }
