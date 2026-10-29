from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from backend.app.models.models import (
    AISuggestion,
    ChangeEvent,
    Event,
    EventLog,
)
from backend.app.schemas.replanning import (
    BudgetItemDiffSchema,
    ChangeProposalResponseSchema,
    ChangeRequestSchema,
    PatchChangeProposalSchema,
    TaskDiffSchema,
)
from backend.app.services.llm_provider import get_replanning_explanation_provider
from backend.app.services.replanning.infeasibility import ReplanningInfeasibilityChecker
from backend.app.services.replanning.mutations import ProposalMutations
from backend.app.services.replanning.proposals import ProposalBuilders


class ReplanningService:
    """
    State machine for proposing, queueing, previewing, and applying dynamic
    re-planning changes (e.g., guest count +/- 50, date moves, vendor cancellations).
    """

    _check_infeasibility = ReplanningInfeasibilityChecker._check_infeasibility
    _handle_infeasible_proposal = ReplanningInfeasibilityChecker._handle_infeasible_proposal
    _dispatch_proposal_builder = ProposalBuilders._dispatch_proposal_builder
    _apply_budget_overrides = ProposalMutations._apply_budget_overrides
    _apply_budget_diffs = ProposalMutations._apply_budget_diffs
    _apply_task_diffs = ProposalMutations._apply_task_diffs
    _apply_sub_event_diffs = ProposalMutations._apply_sub_event_diffs
    _apply_event_mutations = ProposalMutations._apply_event_mutations
    _promote_next_queued = ProposalMutations._promote_next_queued

    @classmethod
    def create_change_proposal(
        cls,
        db: Session,
        event_id: str,
        change_req: ChangeRequestSchema,
        _actor_id: str | None = None,
    ) -> ChangeProposalResponseSchema:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            err_msg = f"Event with id '{event_id}' not found."
            raise ValueError(err_msg)

        payload = change_req.payload or {}
        change_type = change_req.change_type

        # 1. Infeasibility validations
        infeasibility_reason = cls._check_infeasibility(event, change_type, payload)
        if infeasibility_reason:
            return cls._handle_infeasible_proposal(
                db, event, change_type, payload, infeasibility_reason
            )

        # 2. Determine initial status
        pending_existing = (
            db.query(ChangeEvent)
            .filter(ChangeEvent.event_id == event_id, ChangeEvent.status == "pending")
            .first()
        )
        current_status = "queued" if pending_existing else "pending"

        # 3. Dispatch deterministic math & scheduling handler
        plan = cls._dispatch_proposal_builder(event, change_type, payload)
        budget_diffs = plan["budget_diffs"]
        budget_old = plan["budget_old"]
        budget_new = plan["budget_new"]
        budget_delta = plan["budget_delta"]
        task_diff = plan["task_diff"]
        sub_event_diffs = plan["sub_event_diffs"]
        vendor_re_quote_cats = plan["vendor_re_quote_cats"]
        capacity_warning = plan["capacity_warning"]

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
            "venue_name": payload.get("venue_name"),
        }

        explanation_provider = get_replanning_explanation_provider()
        ai_resp = explanation_provider.generate_explanation_and_mitigations(
            change_type=change_type,
            diff_summary=diff_summary,
            total_budget=float(event.total_budget),
        )

        summary_text = f"Change proposal for {change_type.replace('_', ' ').title()}"
        if current_status == "queued":
            summary_text += " (Queued behind active pending proposal)"

        # 5. Persist ChangeEvent and AISuggestion
        change_event = ChangeEvent(
            event_id=event_id, change_type=change_type, payload=payload, status=current_status
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
            "created_at": change_event.created_at.isoformat(),
        }

        suggestion = AISuggestion(
            event_id=event_id,
            change_event_id=change_event.id,
            agent_name="replanning_agent_f1",
            proposal_payload=proposal_payload,
            reasoning=ai_resp.get("reasoning", {}),
            status=current_status,
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
            created_at=change_event.created_at,
        )

    @classmethod
    def get_change_proposal(
        cls, db: Session, event_id: str, change_id: str
    ) -> ChangeProposalResponseSchema:
        change_event = (
            db.query(ChangeEvent)
            .filter(ChangeEvent.id == change_id, ChangeEvent.event_id == event_id)
            .first()
        )
        if not change_event:
            err_msg = f"Change event '{change_id}' not found for event '{event_id}'."
            raise ValueError(err_msg)

        sugg = db.query(AISuggestion).filter(AISuggestion.change_event_id == change_id).first()
        if not sugg or not sugg.proposal_payload:
            err_msg = f"AI proposal not found for change event '{change_id}'."
            raise ValueError(err_msg)

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
            task_diff=TaskDiffSchema(
                **p.get("task_diff", {"added_tasks": [], "moved_tasks": [], "cancelled_tasks": []})
            ),
            vendor_re_quote_categories=p.get("vendor_re_quote_categories", []),
            capacity_warning=p.get("capacity_warning"),
            infeasibility_reason=p.get("infeasibility_reason"),
            explanation=p.get("explanation"),
            mitigation_suggestions=p.get("mitigation_suggestions", []),
            provider_used=p.get("provider_used", "deterministic_stub"),
            fallback_warning=p.get("fallback_warning"),
            created_at=change_event.created_at,
        )

    @classmethod
    def accept_change(
        cls, db: Session, event_id: str, change_id: str, actor_id: str | None = None
    ) -> ChangeProposalResponseSchema:
        change_event = (
            db.query(ChangeEvent)
            .filter(ChangeEvent.id == change_id, ChangeEvent.event_id == event_id)
            .first()
        )
        if not change_event:
            err_msg = f"Change event '{change_id}' not found for event '{event_id}'."
            raise ValueError(err_msg)

        if change_event.status == "blocked_infeasible":
            err_msg = "Cannot accept an infeasible change proposal."
            raise ValueError(err_msg)
        if change_event.status != "pending":
            err_msg = (
                f"Cannot accept change event in status '{change_event.status}'. Must be 'pending'."
            )
            raise ValueError(err_msg)

        sugg = db.query(AISuggestion).filter(AISuggestion.change_event_id == change_id).first()
        if not sugg or not sugg.proposal_payload:
            err_msg = "Proposal payload missing."
            raise ValueError(err_msg)

        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            err_msg = "Event not found."
            raise ValueError(err_msg)
        payload = sugg.proposal_payload

        # 1. Mutate Budget Items
        cls._apply_budget_diffs(db, event_id, payload.get("budget_diff", []))

        # 2. Mutate Tasks
        cls._apply_task_diffs(db, event_id, payload.get("task_diff", {}))

        # 3. Mutate SubEvents
        cls._apply_sub_event_diffs(db, event_id, payload.get("sub_event_diffs", []))

        # 4. Mutate Event top-level fields
        cls._apply_event_mutations(event, change_event.change_type, change_event.payload or {})

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
            actor_id=actor_id,
        )
        db.add(event_log)

        # 7. Promote next queued change event if present
        cls._promote_next_queued(db, event_id)

        db.commit()
        db.refresh(change_event)

        return cls.get_change_proposal(db, event_id, change_id)

    @classmethod
    def reject_change(
        cls, db: Session, event_id: str, change_id: str, actor_id: str | None = None
    ) -> ChangeProposalResponseSchema:
        change_event = (
            db.query(ChangeEvent)
            .filter(ChangeEvent.id == change_id, ChangeEvent.event_id == event_id)
            .first()
        )
        if not change_event:
            err_msg = f"Change event '{change_id}' not found for event '{event_id}'."
            raise ValueError(err_msg)

        if change_event.status not in ("pending", "queued"):
            err_msg = (
                f"Cannot reject change event in status '{change_event.status}'. "
                "Must be pending or queued."
            )
            raise ValueError(err_msg)

        was_pending = change_event.status == "pending"

        change_event.status = "rejected"
        sugg = db.query(AISuggestion).filter(AISuggestion.change_event_id == change_id).first()
        if sugg:
            sugg.status = "rejected"
            if sugg.proposal_payload:
                sugg.proposal_payload["status"] = "rejected"

        # Log rejection
        event_log = EventLog(
            event_id=event_id,
            action_type=f"change_proposal_rejected:{change_event.change_type}",
            diff_payload={"change_id": change_id, "status": "rejected"},
            actor_id=actor_id,
        )
        db.add(event_log)

        # Promote next queued if the rejected proposal was the active pending one
        if was_pending:
            cls._promote_next_queued(db, event_id)

        db.commit()
        db.refresh(change_event)

        return cls.get_change_proposal(db, event_id, change_id)

    @classmethod
    def patch_change(
        cls, db: Session, event_id: str, change_id: str, patch_data: PatchChangeProposalSchema
    ) -> ChangeProposalResponseSchema:
        change_event = (
            db.query(ChangeEvent)
            .filter(ChangeEvent.id == change_id, ChangeEvent.event_id == event_id)
            .first()
        )
        if not change_event:
            err_msg = f"Change event '{change_id}' not found."
            raise ValueError(err_msg)

        if change_event.status != "pending":
            err_msg = f"Cannot edit proposal in status '{change_event.status}'. Must be pending."
            raise ValueError(err_msg)

        sugg = db.query(AISuggestion).filter(AISuggestion.change_event_id == change_id).first()
        if not sugg or not sugg.proposal_payload:
            err_msg = "Proposal payload missing."
            raise ValueError(err_msg)

        payload = sugg.proposal_payload
        budget_diff = payload.get("budget_diff", [])

        if patch_data.budget_overrides:
            cls._apply_budget_overrides(budget_diff, patch_data.budget_overrides)

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
