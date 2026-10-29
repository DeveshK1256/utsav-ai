from datetime import date, datetime, timezone
import pytest
from backend.app.models.models import BudgetItem, ChangeEvent, AISuggestion, SubEvent, Task
from backend.app.services.dag.scheduler import DAGScheduler, TaskNode
from backend.app.services.replanning.mutations import ProposalMutations


def test_dag_scheduler_cycle_detection_and_samagri_branches():
    # 1. Test check_cycles when dep not in adj
    nodes = [
        TaskNode("t1", "Task 1", 30, 0, "Ops", dependencies=["nonexistent_dep"]),
        TaskNode("t2", "Task 2", 30, 0, "Ops", dependencies=["t1"]),
    ]
    assert DAGScheduler.check_cycles(nodes) is False

    # 2. Test cycle detection in check_cycles
    cyclic_nodes = [
        TaskNode("a", "A", 30, 0, "Ops", dependencies=["b"]),
        TaskNode("b", "B", 30, 0, "Ops", dependencies=["a"]),
    ]
    assert DAGScheduler.check_cycles(cyclic_nodes) is True

    # 3. Test _load_samagri_items with secondary_tradition_code when db is None
    curated_items = DAGScheduler._load_samagri_items("punjabi_traditional", "bengali_vedic", db=None)
    assert len(curated_items) > 0

    # 4. Test _build_ritual_task with more than 4 items
    many_items = [
        {"item_name": f"Item {i}", "standard_quantity": "1 kg"}
        for i in range(7)
    ]
    task = DAGScheduler._build_ritual_task("Grand Aarti", many_items, 0, date(2026, 11, 1))
    assert "and 3 more items" in task["description"]


def test_proposal_mutations_edge_branches(db, sample_event_data):
    event, _ = sample_event_data

    # 1. _apply_budget_diffs with missing id and missing record
    b_item = BudgetItem(
        event_id=event.id,
        name="Catering Package",
        category="Catering",
        planned_amount=100000.0,
        scaling_rule="linear_per_guest",
    )
    db.add(b_item)
    db.commit()
    db.refresh(b_item)

    # Missing budget_item_id
    ProposalMutations._apply_budget_diffs(db, event.id, [{"scaling_rule": "fixed"}])
    # Nonexistent budget item
    ProposalMutations._apply_budget_diffs(
        db,
        event.id,
        [{"budget_item_id": "nonexistent_b_id", "new_amount": 120000.0}],
    )
    # Existing item with scaling_rule change
    ProposalMutations._apply_budget_diffs(
        db,
        event.id,
        [{"budget_item_id": b_item.id, "new_amount": 150000.0, "scaling_rule": "fixed"}],
    )
    db.commit()
    db.refresh(b_item)
    assert float(b_item.planned_amount) == 150000.0
    assert b_item.scaling_rule == "fixed"

    # 2. _apply_task_diffs with missing tasks, missing new_start or new_end
    task = Task(
        event_id=event.id,
        title="Decor Setup",
        status="pending",
        duration_minutes=120,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Nonexistent task
    ProposalMutations._apply_task_diffs(
        db,
        event.id,
        {"moved_tasks": [{"task_id": "nonexistent_task", "new_start": "2026-12-01T10:00:00Z"}]},
    )
    # Task with only new_start
    ProposalMutations._apply_task_diffs(
        db,
        event.id,
        {"moved_tasks": [{"task_id": task.id, "new_start": "2026-12-01T10:00:00+00:00"}]},
    )
    # Task with only new_end
    ProposalMutations._apply_task_diffs(
        db,
        event.id,
        {"moved_tasks": [{"task_id": task.id, "new_end": "2026-12-01T12:00:00+00:00"}]},
    )

    # 3. _apply_sub_event_diffs with nonexistent record and partial updates
    se = SubEvent(
        event_id=event.id,
        name="Mehendi",
        venue_name="Grand Lawn",
        start_time=datetime(2026, 12, 1, 14, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 12, 1, 18, 0, tzinfo=timezone.utc),
    )
    db.add(se)
    db.commit()
    db.refresh(se)

    # Nonexistent sub_event
    ProposalMutations._apply_sub_event_diffs(
        db,
        event.id,
        [{"sub_event_id": "nonexistent_se", "new_start": "2026-12-01T15:00:00+00:00"}],
    )
    # SubEvent with only new_start
    ProposalMutations._apply_sub_event_diffs(
        db,
        event.id,
        [{"sub_event_id": se.id, "new_start": "2026-12-01T15:00:00+00:00"}],
    )
    # SubEvent with only new_end
    ProposalMutations._apply_sub_event_diffs(
        db,
        event.id,
        [{"sub_event_id": se.id, "new_end": "2026-12-01T19:00:00+00:00"}],
    )

    # 4. _apply_event_mutations edge branches
    # guest_count_changed without to_guest_count
    ProposalMutations._apply_event_mutations(event, "guest_count_changed", {})
    # date_moved with missing to_date or from_date
    ProposalMutations._apply_event_mutations(event, "date_moved", {"to_date": "2026-12-05"})
    # budget_cut with None
    ProposalMutations._apply_event_mutations(event, "budget_cut", {})

    # 5. _promote_next_queued with suggestion payload
    ce = ChangeEvent(event_id=event.id, change_type="date_moved", payload={"note": "sample"}, status="queued")
    db.add(ce)
    db.commit()
    db.refresh(ce)

    sugg = AISuggestion(
        event_id=event.id,
        change_event_id=ce.id,
        agent_name="replanning_agent",
        status="queued",
        proposal_payload={"status": "queued", "note": "test"},
    )
    db.add(sugg)
    db.commit()

    ProposalMutations._promote_next_queued(db, event.id)
    db.commit()
    db.refresh(ce)
    db.refresh(sugg)
    assert ce.status == "pending"
    assert sugg.status == "pending"
    assert sugg.proposal_payload["status"] == "pending"

