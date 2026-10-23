from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from backend.app.models.models import Event, BudgetItem, Task, SubEvent, ChangeEvent, AISuggestion, EventLog
from backend.app.schemas.replanning import (
    ChangeRequestSchema,
    BudgetItemDiffSchema,
    TaskDiffSchema,
    ChangeProposalResponseSchema,
    PatchChangeProposalSchema
)
from backend.app.services.budget_rescaling_engine import BudgetRescalingEngine
from backend.app.services.dag_scheduler import DAGScheduler
from backend.app.services.llm_provider import get_replanning_explanation_provider


class ReplanningService:

    @classmethod
    def create_change_proposal(
        cls,
        db: Session,
        event_id: str,
        change_req: ChangeRequestSchema,
        actor_id: Optional[str] = None
    ) -> ChangeProposalResponseSchema:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise ValueError(f"Event with id '{event_id}' not found.")

        payload = change_req.payload or {}
        change_type = change_req.change_type

        # 1. Infeasibility validations
        infeasibility_reason = cls._check_infeasibility(event, change_type, payload)
        if infeasibility_reason:
            change_event = ChangeEvent(
                event_id=event_id,
                change_type=change_type,
                payload=payload,
                status="blocked_infeasible"
            )
            db.add(change_event)
            db.flush()

            proposal_payload = {
                "change_id": change_event.id,
                "event_id": event_id,
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
                "explanation": f"This change proposal cannot be applied because it is infeasible: {infeasibility_reason}",
                "mitigation_suggestions": ["Revise parameters to valid ranges (e.g. valid future dates, positive guest counts, budget above committed costs)."],
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            suggestion = AISuggestion(
                event_id=event_id,
                change_event_id=change_event.id,
                agent_name="replanning_agent_f1",
                proposal_payload=proposal_payload,
                reasoning={"infeasible": True, "reason": infeasibility_reason},
                status="blocked_infeasible"
            )
            db.add(suggestion)
            db.commit()

            return ChangeProposalResponseSchema(
                change_id=change_event.id,
                event_id=event_id,
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
                created_at=change_event.created_at
            )

        # 2. Determine initial status: queued if another change is pending, else pending
        pending_existing = (
            db.query(ChangeEvent)
            .filter(ChangeEvent.event_id == event_id, ChangeEvent.status == "pending")
            .first()
        )
        current_status = "queued" if pending_existing else "pending"

        # 3. Dispatch deterministic math & scheduling handler
        budget_diffs: List[Dict[str, Any]] = []
        task_diff = {"added_tasks": [], "moved_tasks": [], "cancelled_tasks": []}
        sub_event_diffs: List[Dict[str, Any]] = []
        vendor_re_quote_cats: List[str] = []
        capacity_warning: Optional[str] = None
        budget_old = float(event.total_budget)
        budget_new = float(event.total_budget)
        budget_delta = 0.0

        if change_type == "guest_count_changed":
            from_g = int(payload.get("from_guest_count", event.guest_count))
            to_g = int(payload.get("to_guest_count"))
            result = BudgetRescalingEngine.rescale_for_guest_count_change(
                old_guest_count=from_g,
                new_guest_count=to_g,
                budget_items=event.budget_items,
                venue_capacity=event.venue_capacity
            )
            budget_diffs = [item.model_dump() for item in result.items]
            budget_old = result.total_old
            budget_new = result.total_new
            budget_delta = result.total_delta
            capacity_warning = result.capacity_warning
            if to_g > from_g:
                vendor_re_quote_cats = [
                    d["category"] for d in budget_diffs if d["scaling_rule"] in ("per_guest", "tiered") and d["difference"] > 0
                ]

        elif change_type == "vendor_cancelled":
            cat = payload.get("category", "vendor")
            v_name = payload.get("vendor_name", "Vendor")
            vendor_re_quote_cats = [cat]
            task_diff["added_tasks"].append({
                "title": f"Urgent: Settle replacement for {cat} ({v_name})",
                "description": f"Vendor {v_name} cancelled. Procure replacement quotes for {cat} immediately.",
                "assigned_role": "Procurement Lead",
                "duration_minutes": 120
            })
            for b in event.budget_items:
                if (b.category or "").lower() == cat.lower():
                    b_amt = float(b.planned_amount or 0.0)
                    budget_diffs.append({
                        "budget_item_id": b.id,
                        "category": b.category,
                        "name": b.name,
                        "scaling_rule": b.scaling_rule or "fixed",
                        "old_amount": b_amt,
                        "new_amount": b_amt,
                        "difference": 0.0,
                        "formula": f"{cat}: Replacement required — original planned allocation ₹{b_amt:,.2f} preserved for re-contracting"
                    })

        elif change_type == "date_moved":
            from_d = date.fromisoformat(str(payload.get("from_date")))
            to_d = date.fromisoformat(str(payload.get("to_date")))
            days_delta = (to_d - from_d).days
            payload["days_shifted"] = days_delta

            task_diff["moved_tasks"] = DAGScheduler.shift_tasks_for_date_moved(event.tasks, days_delta)
            sub_event_diffs = DAGScheduler.shift_sub_events_for_date_moved(event.sub_events, days_delta)

        elif change_type == "budget_cut":
            from_b = float(payload.get("from_budget", float(event.total_budget)))
            to_b = float(payload.get("to_budget"))
            result = BudgetRescalingEngine.rescale_for_budget_cut(
                from_budget=from_b,
                to_budget=to_b,
                budget_items=event.budget_items
            )
            budget_diffs = [item.model_dump() for item in result.items]
            budget_old = result.total_old
            budget_new = result.total_new
            budget_delta = result.total_delta

        elif change_type == "venue_unavailable":
            v_name = payload.get("venue_name", "Primary Venue")
            vendor_re_quote_cats = ["venue"]
            task_diff["added_tasks"].extend([
                {
                    "title": f"Emergency: Scout replacement venues for {v_name}",
                    "description": f"Target capacity: {event.venue_capacity or event.guest_count} guests in {event.city}.",
                    "assigned_role": "Host",
                    "duration_minutes": 240
                },
                {
                    "title": "Conduct emergency replacement venue site inspections",
                    "description": "Verify acoustics, fire safety, and stage layout for muhurat timings.",
                    "assigned_role": "Logistics Lead",
                    "duration_minutes": 180
                }
            ])
            for b in event.budget_items:
                if (b.category or "").lower() == "venue":
                    b_amt = float(b.planned_amount or 0.0)
                    budget_diffs.append({
                        "budget_item_id": b.id,
                        "category": b.category,
                        "name": b.name,
                        "scaling_rule": b.scaling_rule or "fixed",
                        "old_amount": b_amt,
                        "new_amount": b_amt,
                        "difference": 0.0,
                        "formula": f"venue: Replacement venue required — current budget allocation ₹{b_amt:,.2f} preserved for new contract"
                    })

        # 4. Generate plain-language explanation and mitigation suggestions
        diff_summary = {
            "budget_total_old": budget_old,
            "budget_total_delta": budget_delta,
            "budget_total_new": budget_new,
            "capacity_exceeded": bool(capacity_warning),
            "capacity_warning": capacity_warning,
            "from_guest_count": payload.get("from_guest_count"),
            "to_guest_count": payload.get("to_guest_count"),
            "from_date": payload.get("from_date"),
            "to_date": payload.get("to_date"),
            "days_shifted": payload.get("days_shifted", 0),
            "vendor_category": payload.get("category"),
            "vendor_name": payload.get("vendor_name"),
            "cut_amount": abs(budget_delta) if change_type == "budget_cut" else 0.0,
            "venue_name": payload.get("venue_name")
        }

        explanation_provider = get_replanning_explanation_provider()
        ai_resp = explanation_provider.generate_explanation_and_mitigations(
            change_type=change_type,
            diff_summary=diff_summary,
            total_budget=float(event.total_budget)
        )

        summary_text = f"Change proposal for {change_type.replace('_', ' ').title()}"
        if current_status == "queued":
            summary_text += " (Queued behind active pending proposal)"

        # 5. Persist ChangeEvent and AISuggestion
        change_event = ChangeEvent(
            event_id=event_id,
            change_type=change_type,
            payload=payload,
            status=current_status
        )
        db.add(change_event)
        db.flush()

        proposal_payload = {
            "change_id": change_event.id,
            "event_id": event_id,
            "change_type": change_type,
            "status": current_status,
            "summary": summary_text,
            "budget_diff": budget_diffs,
            "budget_total_old": budget_old,
            "budget_total_new": budget_new,
            "budget_total_delta": budget_delta,
            "task_diff": task_diff,
            "sub_event_diffs": sub_event_diffs,
            "vendor_re_quote_categories": vendor_re_quote_cats,
            "capacity_warning": capacity_warning,
            "infeasibility_reason": None,
            "explanation": ai_resp.get("explanation"),
            "mitigation_suggestions": ai_resp.get("mitigation_suggestions", []),
            "provider_used": ai_resp.get("provider_used", "deterministic_stub"),
            "fallback_warning": ai_resp.get("fallback_warning"),
            "created_at": change_event.created_at.isoformat()
        }

        suggestion = AISuggestion(
            event_id=event_id,
            change_event_id=change_event.id,
            agent_name="replanning_agent_f1",
            proposal_payload=proposal_payload,
            reasoning=ai_resp.get("reasoning", {}),
            status=current_status
        )
        db.add(suggestion)
        db.commit()
        db.refresh(change_event)

        return ChangeProposalResponseSchema(
            change_id=change_event.id,
            event_id=event_id,
            change_type=change_type,
            status=current_status,
            summary=summary_text,
            budget_diff=[BudgetItemDiffSchema(**d) for d in budget_diffs],
            budget_total_old=budget_old,
            budget_total_new=budget_new,
            budget_total_delta=budget_delta,
            task_diff=TaskDiffSchema(**task_diff),
            vendor_re_quote_categories=vendor_re_quote_cats,
            capacity_warning=capacity_warning,
            infeasibility_reason=None,
            explanation=proposal_payload["explanation"],
            mitigation_suggestions=proposal_payload["mitigation_suggestions"],
            provider_used=proposal_payload["provider_used"],
            fallback_warning=proposal_payload["fallback_warning"],
            created_at=change_event.created_at
        )

    @classmethod
    def get_change_proposal(cls, db: Session, event_id: str, change_id: str) -> ChangeProposalResponseSchema:
        change_event = (
            db.query(ChangeEvent)
            .filter(ChangeEvent.id == change_id, ChangeEvent.event_id == event_id)
            .first()
        )
        if not change_event:
            raise ValueError(f"Change event '{change_id}' not found for event '{event_id}'.")

        sugg = (
            db.query(AISuggestion)
            .filter(AISuggestion.change_event_id == change_id)
            .first()
        )
        if not sugg or not sugg.proposal_payload:
            raise ValueError(f"AI proposal not found for change event '{change_id}'.")

        p = sugg.proposal_payload
        return ChangeProposalResponseSchema(
            change_id=change_event.id,
            event_id=event_id,
            change_type=change_event.change_type,
            status=change_event.status,
            summary=p.get("summary", ""),
            budget_diff=[BudgetItemDiffSchema(**d) for d in p.get("budget_diff", [])],
            budget_total_old=float(p.get("budget_total_old", 0.0)),
            budget_total_new=float(p.get("budget_total_new", 0.0)),
            budget_total_delta=float(p.get("budget_total_delta", 0.0)),
            task_diff=TaskDiffSchema(**p.get("task_diff", {"added_tasks": [], "moved_tasks": [], "cancelled_tasks": []})),
            vendor_re_quote_categories=p.get("vendor_re_quote_categories", []),
            capacity_warning=p.get("capacity_warning"),
            infeasibility_reason=p.get("infeasibility_reason"),
            explanation=p.get("explanation"),
            mitigation_suggestions=p.get("mitigation_suggestions", []),
            provider_used=p.get("provider_used", "deterministic_stub"),
            fallback_warning=p.get("fallback_warning"),
            created_at=change_event.created_at
        )

    @classmethod
    def accept_change(
        cls,
        db: Session,
        event_id: str,
        change_id: str,
        actor_id: Optional[str] = None
    ) -> ChangeProposalResponseSchema:
        change_event = (
            db.query(ChangeEvent)
            .filter(ChangeEvent.id == change_id, ChangeEvent.event_id == event_id)
            .first()
        )
        if not change_event:
            raise ValueError(f"Change event '{change_id}' not found for event '{event_id}'.")

        if change_event.status == "blocked_infeasible":
            raise ValueError("Cannot accept an infeasible change proposal.")
        if change_event.status != "pending":
            raise ValueError(f"Cannot accept change event in status '{change_event.status}'. Must be 'pending'.")

        sugg = (
            db.query(AISuggestion)
            .filter(AISuggestion.change_event_id == change_id)
            .first()
        )
        if not sugg or not sugg.proposal_payload:
            raise ValueError("Proposal payload missing.")

        event = db.query(Event).filter(Event.id == event_id).first()
        payload = sugg.proposal_payload

        # 1. Mutate Budget Items
        for item_diff in payload.get("budget_diff", []):
            b_id = item_diff.get("budget_item_id")
            new_amt = item_diff.get("new_amount")
            rule = item_diff.get("scaling_rule")
            if b_id and new_amt is not None:
                b_item = db.query(BudgetItem).filter(BudgetItem.id == b_id, BudgetItem.event_id == event_id).first()
                if b_item:
                    b_item.planned_amount = new_amt
                    if rule and b_item.scaling_rule != rule:
                        b_item.scaling_rule = rule

        # 2. Mutate Tasks
        task_diff = payload.get("task_diff", {})
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
                dependency_task_ids=[]
            )
            db.add(new_t)

        # 3. Mutate SubEvents
        for se_diff in payload.get("sub_event_diffs", []):
            se_id = se_diff.get("sub_event_id")
            se_record = db.query(SubEvent).filter(SubEvent.id == se_id, SubEvent.event_id == event_id).first()
            if se_record:
                if se_diff.get("new_start"):
                    se_record.start_time = datetime.fromisoformat(se_diff["new_start"])
                if se_diff.get("new_end"):
                    se_record.end_time = datetime.fromisoformat(se_diff["new_end"])

        # 4. Mutate Event top-level fields
        if change_event.change_type == "guest_count_changed":
            to_g = change_event.payload.get("to_guest_count")
            if to_g:
                event.guest_count = int(to_g)
        elif change_event.change_type == "date_moved":
            to_d_str = change_event.payload.get("to_date")
            from_d_str = change_event.payload.get("from_date")
            if to_d_str and from_d_str:
                from_d = date.fromisoformat(str(from_d_str))
                to_d = date.fromisoformat(str(to_d_str))
                days_delta = (to_d - from_d).days
                event.start_date = to_d
                event.end_date = event.end_date + timedelta(days=days_delta)
        elif change_event.change_type == "budget_cut":
            to_b = change_event.payload.get("to_budget")
            if to_b is not None:
                event.total_budget = float(to_b)

        # 5. Mark ChangeEvent and AISuggestion as applied
        change_event.status = "applied"
        sugg.status = "applied"
        payload["status"] = "applied"
        sugg.proposal_payload = dict(payload)
        flag_modified(sugg, "proposal_payload")

        # 6. Write EventLog record
        event_log = EventLog(
            event_id=event_id,
            action_type=f"change_proposal_applied:{change_event.change_type}",
            diff_payload=payload,
            actor_id=actor_id
        )
        db.add(event_log)

        # 7. Promote next queued change event if present
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
                    next_sugg.proposal_payload["status"] = "pending"

        db.commit()
        db.refresh(change_event)

        return cls.get_change_proposal(db, event_id, change_id)

    @classmethod
    def reject_change(
        cls,
        db: Session,
        event_id: str,
        change_id: str,
        actor_id: Optional[str] = None
    ) -> ChangeProposalResponseSchema:
        change_event = (
            db.query(ChangeEvent)
            .filter(ChangeEvent.id == change_id, ChangeEvent.event_id == event_id)
            .first()
        )
        if not change_event:
            raise ValueError(f"Change event '{change_id}' not found for event '{event_id}'.")

        if change_event.status not in ("pending", "queued"):
            raise ValueError(f"Cannot reject change event in status '{change_event.status}'. Must be pending or queued.")

        was_pending = change_event.status == "pending"

        change_event.status = "rejected"
        sugg = (
            db.query(AISuggestion)
            .filter(AISuggestion.change_event_id == change_id)
            .first()
        )
        if sugg:
            sugg.status = "rejected"
            if sugg.proposal_payload:
                sugg.proposal_payload["status"] = "rejected"

        # Log rejection
        event_log = EventLog(
            event_id=event_id,
            action_type=f"change_proposal_rejected:{change_event.change_type}",
            diff_payload={"change_id": change_id, "status": "rejected"},
            actor_id=actor_id
        )
        db.add(event_log)

        # Promote next queued if the rejected proposal was the active pending one
        if was_pending:
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
                        next_sugg.proposal_payload["status"] = "pending"

        db.commit()
        db.refresh(change_event)

        return cls.get_change_proposal(db, event_id, change_id)

    @classmethod
    def patch_change(
        cls,
        db: Session,
        event_id: str,
        change_id: str,
        patch_data: PatchChangeProposalSchema
    ) -> ChangeProposalResponseSchema:
        change_event = (
            db.query(ChangeEvent)
            .filter(ChangeEvent.id == change_id, ChangeEvent.event_id == event_id)
            .first()
        )
        if not change_event:
            raise ValueError(f"Change event '{change_id}' not found.")

        if change_event.status != "pending":
            raise ValueError(f"Cannot edit proposal in status '{change_event.status}'. Must be pending.")

        sugg = (
            db.query(AISuggestion)
            .filter(AISuggestion.change_event_id == change_id)
            .first()
        )
        if not sugg or not sugg.proposal_payload:
            raise ValueError("Proposal payload missing.")

        payload = sugg.proposal_payload
        budget_diff = payload.get("budget_diff", [])

        if patch_data.budget_overrides:
            for item in budget_diff:
                b_id = item.get("budget_item_id")
                if b_id in patch_data.budget_overrides:
                    overridden_amt = round(float(patch_data.budget_overrides[b_id]), 2)
                    old_amt = item.get("old_amount", 0.0)
                    item["new_amount"] = overridden_amt
                    item["difference"] = round(overridden_amt - old_amt, 2)
                    item["formula"] = f"{item.get('category')}: User manual override = {overridden_amt:.2f}"

            # Recalculate totals
            new_total = round(sum(i.get("new_amount", 0.0) for i in budget_diff), 2)
            old_total = round(sum(i.get("old_amount", 0.0) for i in budget_diff), 2)
            delta = round(new_total - old_total, 2)

            payload["budget_total_new"] = new_total
            payload["budget_total_old"] = old_total
            payload["budget_total_delta"] = delta
            payload["budget_diff"] = budget_diff

            sugg.proposal_payload = dict(payload)
            flag_modified(sugg, "proposal_payload")
            db.commit()

        return cls.get_change_proposal(db, event_id, change_id)

    @classmethod
    def _check_infeasibility(cls, event: Event, change_type: str, payload: Dict[str, Any]) -> Optional[str]:
        if change_type == "guest_count_changed":
            to_g = payload.get("to_guest_count")
            if to_g is None or not isinstance(to_g, (int, float)) or int(to_g) <= 0:
                return f"Target guest count must be a positive integer (received {to_g})."
            if int(to_g) > 10000:
                return f"Target guest count ({to_g}) exceeds maximum supported event scale (10,000)."

        elif change_type == "date_moved":
            to_d_raw = payload.get("to_date")
            from_d_raw = payload.get("from_date", event.start_date.isoformat() if event.start_date else None)
            if not to_d_raw:
                return "Target date 'to_date' is required."
            try:
                to_d = date.fromisoformat(str(to_d_raw))
                from_d = date.fromisoformat(str(from_d_raw))
            except Exception as e:
                return f"Invalid date format (must be YYYY-MM-DD): {e}"

            if to_d < date.today():
                return f"Cannot move event date to the past ({to_d.isoformat()} is earlier than today {date.today().isoformat()})."
            if to_d == from_d:
                return f"Target date ({to_d.isoformat()}) is identical to current date."

        elif change_type == "budget_cut":
            to_b_raw = payload.get("to_budget")
            if to_b_raw is None:
                return "Target budget 'to_budget' is required."
            try:
                to_b = float(to_b_raw)
            except Exception:
                return f"Invalid target budget amount: {to_b_raw}"

            from_b = float(payload.get("from_budget", float(event.total_budget)))
            if to_b <= 0:
                return f"Target budget must be strictly positive (received ₹{to_b:,.2f})."
            if to_b >= from_b:
                return f"Budget cut target (₹{to_b:,.2f}) must be strictly less than current budget (₹{from_b:,.2f})."

            committed_total = sum(
                float(b.planned_amount or 0.0)
                for b in event.budget_items
                if getattr(b, "is_paid", False) or float(getattr(b, "actual_amount", 0.0) or 0.0) > 0
            )
            if to_b < committed_total:
                return (
                    f"Target budget (₹{to_b:,.2f}) cannot be less than already committed/paid vendor contracts "
                    f"(₹{committed_total:,.2f})."
                )

        elif change_type == "vendor_cancelled":
            cat = payload.get("category")
            if not cat:
                return "Vendor category is required in change payload."

        elif change_type == "venue_unavailable":
            v_name = payload.get("venue_name")
            if not v_name:
                return "Venue name is required in change payload."

        return None
