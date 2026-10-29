from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.models import AISuggestion, BudgetItem, ChangeEvent, Event
from backend.app.schemas.replanning import ChangeProposalResponseSchema, TaskDiffSchema


class ReplanningInfeasibilityChecker:
    @classmethod
    def _handle_infeasible_proposal(
        cls,
        db: Session,
        event: Event,
        change_type: str,
        payload: dict[str, Any],
        infeasibility_reason: str,
    ) -> ChangeProposalResponseSchema:
        change_event = ChangeEvent(
            event_id=event.id,
            change_type=change_type,
            payload=payload,
            status="blocked_infeasible",
        )
        db.add(change_event)
        db.flush()

        proposal_payload = {
            "change_id": change_event.id,
            "event_id": event.id,
            "change_type": change_type,
            "status": "blocked_infeasible",
            "summary": f"Infeasible change request: {infeasibility_reason}",
            "budget_diff": [],
            "budget_total_old": float(event.total_budget),
            "budget_total_new": float(event.total_budget),
            "budget_total_delta": 0.0,
            "task_diff": {"added_tasks": [], "moved_tasks": [], "cancelled_tasks": []},
            "vendor_re_quote_categories": [],
            "capacity_warning": None,
            "infeasibility_reason": infeasibility_reason,
            "explanation": (
                f"This change proposal cannot be applied because it is infeasible: "
                f"{infeasibility_reason}"
            ),
            "mitigation_suggestions": [
                (
                    "Revise parameters to valid ranges (e.g. valid future dates, "
                    "positive guest counts, budget above committed costs)."
                )
            ],
            "created_at": datetime.now(UTC).isoformat(),
        }

        suggestion = AISuggestion(
            event_id=event.id,
            change_event_id=change_event.id,
            agent_name="replanning_agent_f1",
            proposal_payload=proposal_payload,
            reasoning={"infeasible": True, "reason": infeasibility_reason},
            status="blocked_infeasible",
        )
        db.add(suggestion)
        db.commit()

        return ChangeProposalResponseSchema(
            change_id=change_event.id,
            event_id=event.id,
            change_type=change_type,
            status="blocked_infeasible",
            summary=proposal_payload["summary"],
            budget_diff=[],
            budget_total_old=float(event.total_budget),
            budget_total_new=float(event.total_budget),
            budget_total_delta=0.0,
            task_diff=TaskDiffSchema(),
            vendor_re_quote_categories=[],
            capacity_warning=None,
            infeasibility_reason=infeasibility_reason,
            explanation=proposal_payload["explanation"],
            mitigation_suggestions=proposal_payload["mitigation_suggestions"],
            created_at=change_event.created_at,
        )

    @classmethod
    def _check_guest_count_infeasibility(cls, payload: dict[str, Any]) -> str | None:
        to_g = payload.get("to_guest_count")
        if to_g is None or not isinstance(to_g, (int, float)) or int(to_g) <= 0:
            return f"Target guest count must be a positive integer (received {to_g})."
        if int(to_g) > 10000:
            return f"Target guest count ({to_g}) exceeds maximum supported event scale (10,000)."
        return None

    @classmethod
    def _check_date_moved_infeasibility(cls, event: Event, payload: dict[str, Any]) -> str | None:
        to_d_raw = payload.get("to_date")
        from_d_raw = payload.get(
            "from_date", event.start_date.isoformat() if event.start_date else None
        )
        if not to_d_raw:
            return "Target date 'to_date' is required."
        try:
            to_d = date.fromisoformat(str(to_d_raw))
            from_d = date.fromisoformat(str(from_d_raw))
        except (ValueError, TypeError) as e:
            return f"Invalid date format (must be YYYY-MM-DD): {e}"

        if to_d < date.today():
            return (
                f"Cannot move event date to the past ({to_d.isoformat()} is earlier than today "
                f"{date.today().isoformat()})."
            )
        if to_d == from_d:
            return f"Target date ({to_d.isoformat()}) is identical to current date."
        return None

    @classmethod
    def _calculate_committed_total(cls, budget_items: list[BudgetItem]) -> float:
        total = 0.0
        for b in budget_items:
            is_paid = bool(getattr(b, "is_paid", False))
            actual = float(getattr(b, "actual_amount", 0.0) or 0.0)
            if is_paid or actual > 0.0:
                total += float(b.planned_amount or 0.0)
        return total

    @classmethod
    def _check_budget_cut_infeasibility(cls, event: Event, payload: dict[str, Any]) -> str | None:
        to_b_raw = payload.get("to_budget")
        if to_b_raw is None:
            return "Target budget 'to_budget' is required."
        try:
            to_b = float(to_b_raw)
        except (ValueError, TypeError):
            return f"Invalid target budget amount: {to_b_raw}"

        from_b = float(payload.get("from_budget", float(event.total_budget)))
        if to_b <= 0:
            return f"Target budget must be strictly positive (received ₹{to_b:,.2f})."
        if to_b >= from_b:
            return (
                f"Budget cut target (₹{to_b:,.2f}) must be strictly less than current budget "
                f"(₹{from_b:,.2f})."
            )

        committed_total = cls._calculate_committed_total(event.budget_items)
        if to_b < committed_total:
            return (
                f"Target budget (₹{to_b:,.2f}) cannot be less than already committed/paid "
                f"vendor contracts (₹{committed_total:,.2f})."
            )
        return None

    @classmethod
    def _check_infeasibility(
        cls, event: Event, change_type: str, payload: dict[str, Any]
    ) -> str | None:
        if change_type == "guest_count_changed":
            return cls._check_guest_count_infeasibility(payload)
        if change_type == "date_moved":
            return cls._check_date_moved_infeasibility(event, payload)
        if change_type == "budget_cut":
            return cls._check_budget_cut_infeasibility(event, payload)
        if change_type == "vendor_cancelled":
            if not payload.get("category"):
                return "Vendor category is required in change payload."
            return None
        if change_type == "venue_unavailable":
            if not payload.get("venue_name"):
                return "Venue name is required in change payload."
            return None
        return None
