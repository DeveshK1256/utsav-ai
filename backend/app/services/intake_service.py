import re
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.app.models.models import User, Event, SubEvent, BudgetItem, Task, Tradition, EventLog
from backend.app.schemas.intake import (
    IntakeRequestSchema,
    MasterPlanResponseSchema,
    SubEventResponseSchema,
    BudgetItemResponseSchema,
    TaskResponseSchema
)
from backend.app.services.budget_engine import BudgetScalingEngine
from backend.app.services.budget_rescaling_engine import BudgetRescalingEngine
from backend.app.services.dag_scheduler import DAGScheduler
from backend.app.core.security import generate_owner_token


def normalize_indian_phone(phone: str) -> str:
    cleaned = re.sub(r"[\s\-\(\)]", "", phone.strip())
    if cleaned.startswith("+91"):
        digits = cleaned[3:]
    elif cleaned.startswith("91") and len(cleaned) == 12:
        digits = cleaned[2:]
    elif cleaned.startswith("0") and len(cleaned) == 11:
        digits = cleaned[1:]
    else:
        digits = cleaned

    if len(digits) != 10 or not digits.isdigit() or digits[0] not in "6789":
        raise ValueError(f"Invalid Indian mobile number: {phone}")

    return f"+91{digits}"


class IntakeService:

    @classmethod
    def ensure_default_traditions(cls, db: Session):
        known_traditions = [
            ("maharashtrian_vedic", "Maharashtrian Vedic Lagna", "Classical Maharashtrian wedding rituals including Sakharpuda, Haldi, Mandap Muhurat, and Saptapadi."),
            ("gujarati_hindu", "Gujarati Hindu Vivah", "Vibrant Gujarati rituals featuring Mameru, Dandiya Raas, Mandap, and Hastamelap."),
            ("punjabi_sikh", "Punjabi Anand Karaj", "Joyous celebration with Roka, Mehndi/Sangeet, sacred Anand Karaj, and Reception."),
            ("south_indian_iyer", "Tamil Brahmin Iyer Kalyanam", "Traditional rituals including Vratham, Kasi Yatra, Oonjal, and Kanyadaan."),
            ("marwari_traditional", "Marwari Traditional Vivah", "Royal Marwari rituals with Mudha Tika, Pithi, Tel Baan, and Baraat."),
            ("satyanarayan_puja", "Satyanarayan Vrat Katha", "Sacred home blessing and thanksgiving puja ceremony."),
            ("community_festival", "Sarvajanik Community Festival", "Public community festival celebration with cultural programs, aarti, and volunteer coordination."),
            ("birthday_kids_carnival", "Kids Themed Birthday Carnival", "Fun-filled kids birthday celebration with interactive games, magic show, custom cake, and return gifts."),
            ("birthday_milestone", "Milestone Jubilee Birthday", "Celebration for 18th, 21st, 50th, or 60th birthday with family blessings, toasts, and gala feast."),
            ("birthday_traditional", "Traditional Vedic Ayushya Homa", "Sacred birthday rituals including Ayushya Homa, Ganapati puja, elder blessings, and satvik meal."),
            ("community_sarvajanik", "Sarvajanik Utsav & Pandal", "Public festival (Ganesh Utsav / Durga Puja) with murti sthapana, maha aarti, cultural night, and bhandara."),
            ("community_navratri", "Navratri Garba & Dandiya Mahotsav", "Multi-night folk dance celebration with live orchestra, Dandiya Raas, awards, and prasad."),
            ("community_society_mela", "Housing Society Cultural Mela", "Residential community gathering with food & game stalls, resident talent show, and society feast.")
        ]
        for code, name, desc in known_traditions:
            if not db.query(Tradition).filter(Tradition.code == code).first():
                trad = Tradition(code=code, regional_name=name, description=desc)
                db.add(trad)
        db.commit()

    @classmethod
    def generate_master_plan(cls, db: Session, req: IntakeRequestSchema) -> MasterPlanResponseSchema:
        cls.ensure_default_traditions(db)
        clean_phone = normalize_indian_phone(req.phone_number)

        # 1. User
        user = db.query(User).filter(User.phone_number == clean_phone).first()
        if not user:
            user = User(
                phone_number=clean_phone,
                full_name=req.host_name,
                role="host",
                preferred_language="en"
            )
            db.add(user)
            db.flush()

        # 2. Event
        owner_token = generate_owner_token()
        event = Event(
            owner_id=user.id,
            name=req.name,
            event_type=req.event_type,
            tradition_code=req.tradition_code,
            guest_count=req.guest_count,
            total_budget=req.total_budget,
            city=req.city,
            pincode=req.pincode,
            start_date=req.start_date,
            end_date=req.end_date,
            status="planning",
            owner_token=owner_token,
            metadata_json={"host_name": req.host_name, "owner_token": owner_token}
        )
        db.add(event)
        db.flush()

        # 3. Sub-Events via DAGScheduler
        sub_event_specs = DAGScheduler.get_sub_events_for_tradition(req.tradition_code, req.start_date, req.event_type)
        created_sub_events = []
        for spec in sub_event_specs:
            se = SubEvent(
                event_id=event.id,
                name=spec["name"],
                start_time=spec["start_time"],
                end_time=spec["end_time"],
                venue_name=spec["venue_name"],
                venue_address=spec["venue_address"],
                is_outdoor=spec["is_outdoor"],
                is_muhurat_locked=spec["is_muhurat_locked"],
                muhurat_notes=spec["muhurat_notes"],
                sort_order=spec["sort_order"]
            )
            db.add(se)
            db.flush()
            created_sub_events.append(se)

        # 4. Budget Items via BudgetScalingEngine
        budget_allocations = BudgetScalingEngine.compute_budget_allocation(
            total_envelope=req.total_budget,
            event_type=req.event_type,
            city=req.city,
            guest_count=req.guest_count
        )
        created_budget_items = []
        for alloc in budget_allocations:
            rule = BudgetRescalingEngine.resolve_scaling_rule(alloc["category"])
            b_item = BudgetItem(
                event_id=event.id,
                category=alloc["category"],
                name=f"{alloc['category'].replace('_', ' ').title()} Allocation",
                planned_amount=alloc["planned_amount"],
                actual_amount=0.00,
                is_paid=False,
                scaling_rule=rule,
                reasoning_spec=alloc["reasoning_spec"]
            )
            db.add(b_item)
            db.flush()
            created_budget_items.append((b_item, alloc["percentage"]))

        # 5. Scheduled Tasks via DAGScheduler
        scheduled_tasks = DAGScheduler.generate_scheduled_tasks(req.start_date, req.event_type)
        created_tasks = []
        for t in scheduled_tasks:
            task = Task(
                event_id=event.id,
                title=t["title"],
                description=t["description"],
                status=t["status"],
                scheduled_start=t["scheduled_start"],
                scheduled_end=t["scheduled_end"],
                duration_minutes=t["duration_minutes"],
                dependency_task_ids=t["dependency_task_ids"],
                assigned_role=t["assigned_role"]
            )
            db.add(task)
            db.flush()
            created_tasks.append(task)

        # 6. Immutable Event Log
        event_log = EventLog(
            event_id=event.id,
            action_type="EVENT_PLAN_SYNTHESIZED",
            diff_payload={
                "sub_events_count": len(created_sub_events),
                "budget_items_count": len(created_budget_items),
                "tasks_count": len(created_tasks),
                "city_tier": BudgetScalingEngine.resolve_city_tier(req.city)
            },
            actor_id=user.id
        )
        db.add(event_log)
        db.commit()

        # Build Response
        return MasterPlanResponseSchema(
            event_id=event.id,
            owner_token=owner_token,
            name=event.name,
            owner_name=user.full_name,
            status=event.status,
            city_tier=BudgetScalingEngine.resolve_city_tier(req.city),
            total_budget=float(event.total_budget),
            guest_count=event.guest_count,
            tradition_code=req.tradition_code,
            sub_events=[
                SubEventResponseSchema(
                    id=se.id,
                    name=se.name,
                    start_time=se.start_time,
                    end_time=se.end_time,
                    venue_name=se.venue_name,
                    is_outdoor=se.is_outdoor,
                    is_muhurat_locked=se.is_muhurat_locked,
                    muhurat_notes=se.muhurat_notes,
                    sort_order=se.sort_order
                )
                for se in created_sub_events
            ],
            budget_breakdown=[
                BudgetItemResponseSchema(
                    id=bi[0].id,
                    category=bi[0].category,
                    name=bi[0].name,
                    planned_amount=float(bi[0].planned_amount),
                    actual_amount=float(bi[0].actual_amount),
                    percentage=bi[1],
                    reasoning_spec=bi[0].reasoning_spec
                )
                for bi in created_budget_items
            ],
            tasks=[
                TaskResponseSchema(
                    id=t.id,
                    title=t.title,
                    status=t.status,
                    scheduled_start=t.scheduled_start,
                    scheduled_end=t.scheduled_end,
                    duration_minutes=t.duration_minutes,
                    assigned_role=t.assigned_role
                )
                for t in created_tasks
            ],
            created_at=event.created_at
        )
