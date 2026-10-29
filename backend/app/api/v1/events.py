from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.core.security import generate_owner_token, verify_event_owner_token
from backend.app.db.session import get_db
from backend.app.models.models import Event, User
from backend.app.schemas.events import (
    ComposeUpdateSchema,
    EventCreateSchema,
    EventDetailResponseSchema,
    EventResponseSchema,
)
from backend.app.schemas.intake import (
    BudgetItemResponseSchema,
    SubEventResponseSchema,
    TaskResponseSchema,
)
from backend.app.services.budget_engine import BudgetScalingEngine
from backend.app.services.event_composer_service import (
    handle_compose_timing_selection,
    handle_compose_venue_selection,
)

router = APIRouter(prefix="/events", tags=["Events"])


@router.post("", response_model=EventResponseSchema, status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreateSchema, db: Session = Depends(get_db)) -> EventResponseSchema:
    user = db.query(User).filter(User.phone_number == payload.host_phone).first()
    if not user:
        user = User(
            phone_number=payload.host_phone,
            full_name=payload.host_name,
            role="host",
            preferred_language="en",
        )
        db.add(user)
        db.flush()

    owner_token = generate_owner_token()
    event = Event(
        owner_id=user.id,
        name=payload.name,
        event_type=payload.event_type,
        guest_count=payload.guest_count,
        total_budget=payload.total_budget,
        city=payload.city,
        pincode=payload.pincode or "400001",
        start_date=payload.start_date or date.today(),
        end_date=payload.end_date or date.today(),
        status="planning",
        owner_token=owner_token,
        metadata_json={"owner_token": owner_token, "host_name": payload.host_name},
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return EventResponseSchema.model_validate(event)


def _build_sub_event_schemas(sub_events: list[Any]) -> list[SubEventResponseSchema]:
    return [
        SubEventResponseSchema(
            id=se.id,
            name=se.name,
            start_time=se.start_time,
            end_time=se.end_time,
            venue_name=se.venue_name,
            is_outdoor=se.is_outdoor,
            is_muhurat_locked=se.is_muhurat_locked,
            muhurat_notes=se.muhurat_notes,
            sort_order=se.sort_order,
        )
        for se in sub_events
    ]


def _build_budget_schemas(
    budget_items: list[Any], total_budget: float
) -> list[BudgetItemResponseSchema]:
    budget_list = []
    tot = total_budget if total_budget > 0 else 1.0
    for b in budget_items:
        pct = round((float(b.planned_amount) / tot) * 100, 1) if tot > 0 else 0.0
        budget_list.append(
            BudgetItemResponseSchema(
                id=b.id,
                category=b.category,
                name=b.name,
                planned_amount=float(b.planned_amount),
                actual_amount=float(b.actual_amount or 0.0),
                percentage=pct,
                reasoning_spec=b.reasoning_spec,
            )
        )
    return budget_list


def _build_task_schemas(tasks: list[Any]) -> list[TaskResponseSchema]:
    return [
        TaskResponseSchema(
            id=t.id,
            title=t.title,
            status=t.status,
            scheduled_start=t.scheduled_start,
            scheduled_end=t.scheduled_end,
            duration_minutes=t.duration_minutes,
            assigned_role=t.assigned_role,
        )
        for t in tasks
    ]


@router.get("/{event_id}", response_model=EventDetailResponseSchema)
def get_event(
    event_id: str, event: Event = Depends(verify_event_owner_token), db: Session = Depends(get_db)
) -> EventDetailResponseSchema:
    returned_token = event.owner_token or (event.metadata_json or {}).get("owner_token")
    tier = BudgetScalingEngine.resolve_city_tier(event.city)
    owner_name = (
        event.owner.full_name
        if event.owner
        else (event.metadata_json.get("host_name") if event.metadata_json else "Host")
    )
    tot_budget = float(event.total_budget) if event.total_budget else 0.0

    return EventDetailResponseSchema(
        id=event.id,
        owner_id=event.owner_id,
        name=event.name,
        event_type=event.event_type,
        guest_count=event.guest_count,
        total_budget=tot_budget,
        city=event.city,
        pincode=event.pincode,
        status=event.status,
        owner_name=owner_name,
        city_tier=tier,
        tradition_code=event.tradition_code,
        start_date=event.start_date,
        end_date=event.end_date,
        created_at=event.created_at,
        sub_events=_build_sub_event_schemas(event.sub_events),
        budget_breakdown=_build_budget_schemas(event.budget_items, tot_budget),
        tasks=_build_task_schemas(event.tasks),
        owner_token=returned_token,
        metadata_json=event.metadata_json or {},
    )


@router.post("/{event_id}/compose", response_model=EventDetailResponseSchema)
def update_event_compose_progress(
    event_id: str,
    payload: ComposeUpdateSchema,
    event: Event = Depends(verify_event_owner_token),
    db: Session = Depends(get_db),
) -> EventDetailResponseSchema:
    """
    Orchestration progress persistence for the Compose Celebration flow.
    - Saves current step and shortlist venue picks to metadata_json.
    - If muhurat_time is selected, locks it to the primary sub_event (is_muhurat_locked=True)
      and writes to event.metadata_json['muhurat_time'].
    - Explicit skip actions record skip flags without fabricating or carrying stale data.
    """
    meta = dict(event.metadata_json or {})
    compose_state = dict(meta.get("compose_celebration", {}))

    if payload.step:
        compose_state["current_step"] = payload.step

    handle_compose_venue_selection(payload, event, compose_state, meta, db)
    handle_compose_timing_selection(payload, event, compose_state, meta, db)

    meta["compose_celebration"] = compose_state
    event.metadata_json = meta
    db.add(event)
    db.commit()
    db.refresh(event)

    return get_event(event_id=event.id, event=event, db=db)


@router.delete("/{event_id}", status_code=status.HTTP_200_OK)
def delete_event(
    event_id: str, event: Event = Depends(verify_event_owner_token), db: Session = Depends(get_db)
) -> dict[str, Any]:
    owner_id = event.owner_id
    db.delete(event)
    db.commit()
    # Clean up test user if no other events
    remaining = db.query(Event).filter(Event.owner_id == owner_id).count()
    if remaining == 0:
        test_user = db.query(User).filter(User.id == owner_id).first()
        if test_user:
            db.delete(test_user)
            db.commit()
    return {"deleted": True, "event_id": event_id}
