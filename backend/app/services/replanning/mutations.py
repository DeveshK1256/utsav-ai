from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.models import (
    AISuggestion,
    BudgetItem,
    ChangeEvent,
    Event,
    SubEvent,
    Task,
)


class ProposalMutations:
    @classmethod
    def _apply_budget_diffs(
        cls, db: Session, event_id: str, budget_diff: list[dict[str, Any]]
    ) -> None:
        for item_diff in budget_diff:
            b_id = item_diff.get("budget_item_id")
            new_amt = item_diff.get("new_amount")
            rule = item_diff.get("scaling_rule")
            if b_id and new_amt is not None:
                b_item = (
                    db.query(BudgetItem)
                    .filter(BudgetItem.id == b_id, BudgetItem.event_id == event_id)
                    .first()
                )
                if b_item:
                    b_item.planned_amount = new_amt
                    if rule and b_item.scaling_rule != rule:
                        b_item.scaling_rule = rule

    @classmethod
    def _apply_task_diffs(
        cls, db: Session, event_id: str, task_diff: dict[str, list[dict[str, Any]]]
    ) -> None:
        for moved in task_diff.get("moved_tasks", []):
            t_id = moved.get("task_id")
            t_record = db.query(Task).filter(Task.id == t_id, Task.event_id == event_id).first()
            if t_record:
                if moved.get("new_start"):
                    t_record.scheduled_start = datetime.fromisoformat(moved["new_start"])
                if moved.get("new_end"):
                    t_record.scheduled_end = datetime.fromisoformat(moved["new_end"])

        for added in task_diff.get("added_tasks", []):
            new_t = Task(
                event_id=event_id,
                title=added.get("title", "New Task"),
                description=added.get("description"),
                status="pending",
                duration_minutes=added.get("duration_minutes", 60),
                assigned_role=added.get("assigned_role", "Coordinator"),
                dependency_task_ids=[],
            )
            db.add(new_t)

    @classmethod
    def _apply_sub_event_diffs(
        cls, db: Session, event_id: str, sub_event_diffs: list[dict[str, Any]]
    ) -> None:
        for se_diff in sub_event_diffs:
            se_id = se_diff.get("sub_event_id")
            se_record = (
                db.query(SubEvent)
                .filter(SubEvent.id == se_id, SubEvent.event_id == event_id)
                .first()
            )
            if se_record:
                if se_diff.get("new_start"):
                    se_record.start_time = datetime.fromisoformat(se_diff["new_start"])
                if se_diff.get("new_end"):
                    se_record.end_time = datetime.fromisoformat(se_diff["new_end"])

    @classmethod
    def _apply_event_mutations(
        cls, event: Event, change_type: str, payload: dict[str, Any]
    ) -> None:
        if change_type == "guest_count_changed":
            to_g = payload.get("to_guest_count")
            if to_g:
                event.guest_count = int(to_g)
        elif change_type == "date_moved":
            to_d_str = payload.get("to_date")
            from_d_str = payload.get("from_date")
            if to_d_str and from_d_str:
                from_d = date.fromisoformat(str(from_d_str))
                to_d = date.fromisoformat(str(to_d_str))
                days_delta = (to_d - from_d).days
                event.start_date = to_d
                event.end_date = event.end_date + timedelta(days=days_delta)
        elif change_type == "budget_cut":
            to_b = payload.get("to_budget")
            if to_b is not None:
                event.total_budget = float(to_b)

    @classmethod
    def _promote_next_queued(cls, db: Session, event_id: str) -> None:
        next_queued = (
            db.query(ChangeEvent)
            .filter(ChangeEvent.event_id == event_id, ChangeEvent.status == "queued")
            .order_by(ChangeEvent.created_at.asc())
            .first()
        )
        if next_queued:
            next_queued.status = "pending"
            next_sugg = (
                db.query(AISuggestion)
                .filter(AISuggestion.change_event_id == next_queued.id)
                .first()
            )
            if next_sugg:
                next_sugg.status = "pending"
                if next_sugg.proposal_payload:
                    payload = dict(next_sugg.proposal_payload)
                    payload["status"] = "pending"
                    next_sugg.proposal_payload = payload

    @classmethod
    def _apply_budget_overrides(
        cls, budget_diff: list[dict[str, Any]], overrides: dict[str, float]
    ) -> None:
        for item in budget_diff:
            b_id = item.get("budget_item_id")
            if b_id in overrides:
                overridden_amt = round(float(overrides[b_id]), 2)
                old_amt = item.get("old_amount", 0.0)
                item["new_amount"] = overridden_amt
                item["difference"] = round(overridden_amt - old_amt, 2)
                item["formula"] = (
                    f"{item.get('category')}: User manual override = {overridden_amt:.2f}"
                )
