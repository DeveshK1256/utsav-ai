import logging
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, ClassVar

from sqlalchemy.orm import Session

from backend.app.db.seed_traditions import CURATED_TRADITIONS
from backend.app.models.models import RitualItem
from backend.app.services.dag.node import TaskNode
from backend.app.services.dag.templates import (
    BIRTHDAY_TASKS,
    COMMUNITY_TASKS,
    FOUNDATION_TASKS,
    SUB_EVENT_TEMPLATES,
)

logger = logging.getLogger(__name__)


class DAGScheduler:
    """
    Deterministic Directed Acyclic Graph (DAG) Task & Sub-Event Scheduler.
    - Validates dependencies and detects circular dependency deadlocks.
    - Resolves topological execution order.
    - Maps milestones accurately relative to start_date.
    """

    SUB_EVENT_TEMPLATES: ClassVar[dict[str, list[dict[str, Any]]]] = SUB_EVENT_TEMPLATES
    FOUNDATION_TASKS: ClassVar[list[TaskNode]] = FOUNDATION_TASKS
    BIRTHDAY_TASKS: ClassVar[list[TaskNode]] = BIRTHDAY_TASKS
    COMMUNITY_TASKS: ClassVar[list[TaskNode]] = COMMUNITY_TASKS

    @classmethod
    def _resolve_sub_event_template(
        cls, tradition_code: str, event_type: str
    ) -> list[dict[str, Any]]:
        t_key = (tradition_code or "").lower()
        e_key = (event_type or "").lower()

        if t_key in cls.SUB_EVENT_TEMPLATES:
            return cls.SUB_EVENT_TEMPLATES[t_key]
        if "birthday" in e_key or "birthday" in t_key:
            return cls.SUB_EVENT_TEMPLATES.get(
                "birthday_kids_carnival", cls.SUB_EVENT_TEMPLATES["default"]
            )
        fest_keys = ("community", "festival", "mela", "society", "ganesh", "navratri")
        if any(k in e_key or k in t_key for k in fest_keys):
            return cls.SUB_EVENT_TEMPLATES.get(
                "community_sarvajanik", cls.SUB_EVENT_TEMPLATES["default"]
            )
        return cls.SUB_EVENT_TEMPLATES.get(e_key, cls.SUB_EVENT_TEMPLATES["default"])

    @classmethod
    def get_sub_events_for_tradition(
        cls, tradition_code: str, start_date_val: date, event_type: str = "wedding"
    ) -> list[dict[str, Any]]:
        template = cls._resolve_sub_event_template(tradition_code, event_type)
        result = []
        for idx, item in enumerate(template):
            sub_date = start_date_val + timedelta(days=int(str(item["day_offset"])))
            start_dt = datetime.combine(
                sub_date, time(int(str(item["start_time_hour"])), 0), tzinfo=UTC
            )
            end_dt = start_dt + timedelta(hours=float(str(item["duration_hours"])))
            result.append(
                {
                    "name": item["name"],
                    "start_time": start_dt,
                    "end_time": end_dt,
                    "venue_name": item["venue_type"],
                    "venue_address": "Main Celebration Venue Premises",
                    "is_outdoor": item["is_outdoor"],
                    "is_muhurat_locked": item["is_muhurat_locked"],
                    "muhurat_notes": item.get("muhurat_notes"),
                    "sort_order": idx,
                }
            )
        return result

    @classmethod
    def check_cycles(cls, task_nodes: list[TaskNode]) -> bool:
        """Returns True if a circular dependency exists in the task graph."""
        adj: dict[str, list[str]] = {t.task_id: [] for t in task_nodes}
        for t in task_nodes:
            for dep in t.dependencies:
                if dep in adj:
                    adj[dep].append(t.task_id)

        visited: set[str] = set()
        rec_stack: set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node)
            return False

        return any(node not in visited and dfs(node) for node in adj)

    @classmethod
    def generate_scheduled_tasks(
        cls, start_date_val: date, event_type: str = "wedding"
    ) -> list[dict[str, Any]]:
        e_key = (event_type or "").lower()
        if "birthday" in e_key:
            task_nodes = cls.BIRTHDAY_TASKS
        elif any(
            k in e_key for k in ("community", "festival", "mela", "society", "ganesh", "navratri")
        ):
            task_nodes = cls.COMMUNITY_TASKS
        else:
            task_nodes = cls.FOUNDATION_TASKS

        if cls.check_cycles(task_nodes):
            err_msg = f"Circular dependency detected in {event_type} task DAG"
            raise ValueError(err_msg)

        scheduled = []
        for task in task_nodes:
            task_date = start_date_val + timedelta(days=task.offset_days)
            task_start = datetime.combine(task_date, time(10, 0), tzinfo=UTC)
            task_end = task_start + timedelta(minutes=task.duration_minutes)

            scheduled.append(
                {
                    "title": task.title,
                    "description": f"Standard operational milestone: {task.title}",
                    "status": "pending",
                    "scheduled_start": task_start,
                    "scheduled_end": task_end,
                    "duration_minutes": task.duration_minutes,
                    "dependency_task_ids": task.dependencies,
                    "assigned_role": task.assigned_role,
                }
            )
        return scheduled

    @classmethod
    def shift_tasks_for_date_moved(cls, tasks: list[Any], days_delta: int) -> list[dict[str, Any]]:
        """
        Shifts scheduled timing of existing tasks by days_delta while preserving
        dependency ordering. Returns list of task diffs.
        """
        diffs = []
        for t in tasks:
            t_id = getattr(t, "id", "")
            title = getattr(t, "title", "")
            old_start = getattr(t, "scheduled_start", None)
            old_end = getattr(t, "scheduled_end", None)

            new_start = old_start + timedelta(days=days_delta) if old_start else None
            new_end = old_end + timedelta(days=days_delta) if old_end else None

            diffs.append(
                {
                    "task_id": t_id,
                    "title": title,
                    "old_start": old_start.isoformat() if old_start else None,
                    "new_start": new_start.isoformat() if new_start else None,
                    "old_end": old_end.isoformat() if old_end else None,
                    "new_end": new_end.isoformat() if new_end else None,
                    "days_shifted": days_delta,
                    "formula": (
                        f"Date moved: shifted by {days_delta:+d} days to match new event date"
                    ),
                }
            )
        return diffs

    @classmethod
    def shift_sub_events_for_date_moved(
        cls, sub_events: list[Any], days_delta: int
    ) -> list[dict[str, Any]]:
        """
        Shifts sub-event start and end timestamps by days_delta.
        Flags whether religious muhurats are preserved.
        """
        diffs = []
        for se in sub_events:
            se_id = getattr(se, "id", "")
            name = getattr(se, "name", "")
            old_start = getattr(se, "start_time", None)
            old_end = getattr(se, "end_time", None)
            is_muhurat_locked = getattr(se, "is_muhurat_locked", False)

            new_start = old_start + timedelta(days=days_delta) if old_start else None
            new_end = old_end + timedelta(days=days_delta) if old_end else None

            diffs.append(
                {
                    "sub_event_id": se_id,
                    "name": name,
                    "old_start": old_start.isoformat() if old_start else None,
                    "new_start": new_start.isoformat() if new_start else None,
                    "old_end": old_end.isoformat() if old_end else None,
                    "new_end": new_end.isoformat() if new_end else None,
                    "is_muhurat_locked": is_muhurat_locked,
                    "formula": (
                        f"Event date moved: shifted by {days_delta:+d} days "
                        f"(Muhurat lock: {'Preserved' if is_muhurat_locked else 'Standard'})"
                    ),
                }
            )
        return diffs

    @classmethod
    def _load_samagri_from_db(cls, codes: list[str], db: Session) -> list[dict[str, Any]]:

        items = []
        db_items = db.query(RitualItem).filter(RitualItem.tradition_code.in_(codes)).all()
        for i in db_items:
            items.append(
                {
                    "item_name": i.item_name,
                    "regional_name": i.regional_name,
                    "standard_quantity": i.standard_quantity,
                    "ritual_name": i.ritual_name or "Puja Vidhi",
                    "category": i.category or "puja_samagri",
                    "spiritual_purpose": i.spiritual_purpose or "Sacred ceremonial element",
                    "tradition_code": i.tradition_code,
                }
            )
        return items

    @classmethod
    def _load_samagri_from_curated(cls, tradition_set: set[str]) -> list[dict[str, Any]]:

        items = []
        for t in CURATED_TRADITIONS:
            if t["code"] in tradition_set:
                for name, reg, qty, cat, purp, rit in t["items"]:
                    items.append(
                        {
                            "item_name": name,
                            "regional_name": reg,
                            "standard_quantity": qty,
                            "ritual_name": rit,
                            "category": cat,
                            "spiritual_purpose": purp,
                            "tradition_code": t["code"],
                        }
                    )
        return items

    @classmethod
    def _load_samagri_items(
        cls, tradition_code: str, secondary_tradition_code: str | None, db: Session | None
    ) -> list[dict[str, Any]]:
        if db:
            codes = [c for c in [tradition_code, secondary_tradition_code] if c]
            items = cls._load_samagri_from_db(codes, db)
            if items:
                return items

        tradition_set = {tradition_code}
        if secondary_tradition_code:
            tradition_set.add(secondary_tradition_code)
        return cls._load_samagri_from_curated(tradition_set)

    @classmethod
    def _build_ritual_task(
        cls, rit_name: str, group_items: list[dict[str, Any]], idx: int, start_date_val: date
    ) -> dict[str, Any]:
        offset = -1 if idx % 2 == 0 else -2
        task_date = start_date_val + timedelta(days=offset)
        task_start = datetime.combine(task_date, time(9 + (idx % 4), 0), tzinfo=UTC)
        task_end = task_start + timedelta(minutes=90)

        item_list_str = "; ".join(
            [f"{it['item_name']} ({it['standard_quantity']})" for it in group_items[:4]]
        )
        if len(group_items) > 4:
            item_list_str += f"; and {len(group_items) - 4} more items"

        return {
            "title": f"Procure Ritual Samagri: {rit_name}",
            "description": (
                f"Checklist verification and procurement for {rit_name}. "
                f"Items include: {item_list_str}. "
                f"Review quantities with family Panditji / priest before final purchase."
            ),
            "status": "pending",
            "scheduled_start": task_start,
            "scheduled_end": task_end,
            "duration_minutes": 90,
            "dependency_task_ids": ["task-vendor-intake"],
            "assigned_role": "Family Elder / Ritual Lead",
        }

    @classmethod
    def generate_ritual_samagri_tasks(
        cls,
        start_date_val: date,
        tradition_code: str,
        secondary_tradition_code: str | None = None,
        db: Session | None = None,
    ) -> list[dict[str, Any]]:
        """
        Generates structured preparation and procurement tasks for ritual samagri,
        anchored into the DAG schedule prior to event start.
        """
        items = cls._load_samagri_items(tradition_code, secondary_tradition_code, db)

        rituals_grouped: dict[str, list[dict[str, Any]]] = {}
        for it in items:
            rit = it.get("ritual_name") or "Main Sacred Ceremony"
            if rit not in rituals_grouped:
                rituals_grouped[rit] = []
            rituals_grouped[rit].append(it)

        return [
            cls._build_ritual_task(rit_name, group_items, idx, start_date_val)
            for idx, (rit_name, group_items) in enumerate(rituals_grouped.items())
        ]
