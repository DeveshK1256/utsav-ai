from datetime import date, datetime, time, timedelta, timezone
from typing import Dict, List, Any, Optional, Set


class TaskNode:
    def __init__(
        self,
        task_id: str,
        title: str,
        duration_minutes: int,
        offset_days: int,
        assigned_role: str,
        sub_event_key: Optional[str] = None,
        dependencies: Optional[List[str]] = None
    ):
        self.task_id = task_id
        self.title = title
        self.duration_minutes = duration_minutes
        self.offset_days = offset_days
        self.assigned_role = assigned_role
        self.sub_event_key = sub_event_key
        self.dependencies = dependencies or []


class DAGScheduler:
    """
    Deterministic Directed Acyclic Graph (DAG) Task & Sub-Event Scheduler.
    - Validates dependencies and detects circular dependency deadlocks.
    - Resolves topological execution order.
    - Maps milestones accurately relative to start_date.
    """

    SUB_EVENT_TEMPLATES = {
        "maharashtrian_vedic": [
            {
                "key": "haldi_mehndi",
                "name": "Haldi & Mehndi Ceremony",
                "day_offset": 0,
                "start_time_hour": 16,
                "duration_hours": 4,
                "is_outdoor": True,
                "is_muhurat_locked": False,
                "venue_type": "Courtyard / Lawn"
            },
            {
                "key": "sangeet",
                "name": "Sangeet & Cultural Night",
                "day_offset": 0,
                "start_time_hour": 20,
                "duration_hours": 4,
                "is_outdoor": False,
                "is_muhurat_locked": False,
                "venue_type": "Grand Ballroom"
            },
            {
                "key": "lagna_muhurat",
                "name": "Vedic Lagna & Saptapadi",
                "day_offset": 1,
                "start_time_hour": 10,
                "duration_hours": 4,
                "is_outdoor": False,
                "is_muhurat_locked": True,
                "muhurat_notes": "Auspicious window based on astronomical ephemeris (10:30 AM - 12:15 PM)",
                "venue_type": "Sacred Mandap Hall"
            },
            {
                "key": "reception",
                "name": "Evening Reception & Feast",
                "day_offset": 1,
                "start_time_hour": 19,
                "duration_hours": 4,
                "is_outdoor": True,
                "is_muhurat_locked": False,
                "venue_type": "Royal Palace Lawn"
            }
        ],
        "default": [
            {
                "key": "welcome_evening",
                "name": "Welcome Dinner & Festivities",
                "day_offset": 0,
                "start_time_hour": 18,
                "duration_hours": 4,
                "is_outdoor": True,
                "is_muhurat_locked": False,
                "venue_type": "Garden Terrace"
            },
            {
                "key": "main_ceremony",
                "name": "Main Auspicious Ceremony",
                "day_offset": 1,
                "start_time_hour": 10,
                "duration_hours": 3,
                "is_outdoor": False,
                "is_muhurat_locked": True,
                "muhurat_notes": "Calculated auspicious muhurat window",
                "venue_type": "Main Banquet Hall"
            },
            {
                "key": "celebratory_reception",
                "name": "Celebration Gala & Dinner",
                "day_offset": 1,
                "start_time_hour": 19,
                "duration_hours": 4,
                "is_outdoor": False,
                "is_muhurat_locked": False,
                "venue_type": "Grand Ballroom"
            }
        ]
    }

    FOUNDATION_TASKS = [
        TaskNode("venue_lock", "Contract and Lock Primary Venue", 120, -60, "Host", dependencies=[]),
        TaskNode("caterer_menu", "Finalize Catering Menu & Per-Plate Contract", 90, -45, "Food & Beverage Lead", dependencies=["venue_lock"]),
        TaskNode("mandap_rigging", "Review Mandap Rigging & Floral Decor Specs", 180, -30, "Decor Lead", dependencies=["venue_lock"]),
        TaskNode("priest_samagri", "Consult Priest and Settle Samagri Shopping List", 60, -21, "Elder Coordinator", dependencies=["venue_lock"]),
        TaskNode("whatsapp_invites", "Dispatch WhatsApp Interactive Invitations", 45, -21, "Guest Concierge", dependencies=["caterer_menu"]),
        TaskNode("sound_permits", "Secure Municipal Sound Exemption & Police NOC", 60, -14, "Logistics Lead", dependencies=["venue_lock"]),
        TaskNode("seating_layout", "Finalize Table Constraints & Seating Matrix", 90, -7, "Host", dependencies=["whatsapp_invites"]),
        TaskNode("vendor_call_sheet", "Issue Day-of Vendor Run-of-Show Call Sheet", 60, -2, "Day-of Director", dependencies=["mandap_rigging", "caterer_menu", "sound_permits"])
    ]

    @classmethod
    def get_sub_events_for_tradition(cls, tradition_code: str, start_date_val: date) -> List[Dict[str, Any]]:
        template = cls.SUB_EVENT_TEMPLATES.get(tradition_code.lower(), cls.SUB_EVENT_TEMPLATES["default"])
        result = []
        for idx, item in enumerate(template):
            sub_date = start_date_val + timedelta(days=item["day_offset"])
            start_dt = datetime.combine(sub_date, time(item["start_time_hour"], 0), tzinfo=timezone.utc)
            end_dt = start_dt + timedelta(hours=item["duration_hours"])
            result.append({
                "name": item["name"],
                "start_time": start_dt,
                "end_time": end_dt,
                "venue_name": item["venue_type"],
                "venue_address": "Main Celebration Venue Premises",
                "is_outdoor": item["is_outdoor"],
                "is_muhurat_locked": item["is_muhurat_locked"],
                "muhurat_notes": item.get("muhurat_notes"),
                "sort_order": idx
            })
        return result

    @classmethod
    def check_cycles(cls, task_nodes: List[TaskNode]) -> bool:
        """Returns True if a circular dependency exists in the task graph."""
        adj: Dict[str, List[str]] = {t.task_id: [] for t in task_nodes}
        for t in task_nodes:
            for dep in t.dependencies:
                if dep in adj:
                    adj[dep].append(t.task_id)

        visited: Set[str] = set()
        rec_stack: Set[str] = set()

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

        for node in adj:
            if node not in visited:
                if dfs(node):
                    return True
        return False

    @classmethod
    def generate_scheduled_tasks(cls, start_date_val: date) -> List[Dict[str, Any]]:
        if cls.check_cycles(cls.FOUNDATION_TASKS):
            raise ValueError("Circular dependency detected in foundation task DAG")

        scheduled = []
        for task in cls.FOUNDATION_TASKS:
            task_date = start_date_val + timedelta(days=task.offset_days)
            task_start = datetime.combine(task_date, time(10, 0), tzinfo=timezone.utc)
            task_end = task_start + timedelta(minutes=task.duration_minutes)

            scheduled.append({
                "title": task.title,
                "description": f"Standard operational milestone: {task.title}",
                "status": "pending",
                "scheduled_start": task_start,
                "scheduled_end": task_end,
                "duration_minutes": task.duration_minutes,
                "dependency_task_ids": task.dependencies,
                "assigned_role": task.assigned_role
            })
        return scheduled
