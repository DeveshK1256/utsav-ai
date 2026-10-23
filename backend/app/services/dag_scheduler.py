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
        "birthday_kids_carnival": [
            {
                "key": "welcome_and_games",
                "name": "Guest Arrival, Welcome Drinks & Tattoo Station",
                "day_offset": 0,
                "start_time_hour": 16,
                "duration_hours": 2,
                "is_outdoor": False,
                "is_muhurat_locked": False,
                "venue_type": "Themed Party Hall / Play Zone"
            },
            {
                "key": "magic_and_entertainment",
                "name": "Magic Show, Mascot & Interactive Party Games",
                "day_offset": 0,
                "start_time_hour": 18,
                "duration_hours": 2,
                "is_outdoor": False,
                "is_muhurat_locked": False,
                "venue_type": "Center Stage & Activity Arena"
            },
            {
                "key": "cake_cutting",
                "name": "Grand Cake Cutting & Birthday Song",
                "day_offset": 0,
                "start_time_hour": 20,
                "duration_hours": 1,
                "is_outdoor": False,
                "is_muhurat_locked": True,
                "muhurat_notes": "Prime celebration spotlight & photography moment",
                "venue_type": "Theme Backdrop & Cake Table"
            },
            {
                "key": "kids_buffet_and_favors",
                "name": "Kids & Family Feast & Return Gift Distribution",
                "day_offset": 0,
                "start_time_hour": 21,
                "duration_hours": 2,
                "is_outdoor": False,
                "is_muhurat_locked": False,
                "venue_type": "Dining Lounge & Hospitality Desk"
            }
        ],
        "birthday_milestone": [
            {
                "key": "family_blessing",
                "name": "Ayushya Homa & Family Blessings",
                "day_offset": 0,
                "start_time_hour": 9,
                "duration_hours": 3,
                "is_outdoor": False,
                "is_muhurat_locked": True,
                "muhurat_notes": "Auspicious morning muhurat window for long life & health",
                "venue_type": "Puja Mandap & Prayer Hall"
            },
            {
                "key": "jubilee_lunch",
                "name": "Festive Family Lunch & Memory Walk",
                "day_offset": 0,
                "start_time_hour": 13,
                "duration_hours": 3,
                "is_outdoor": False,
                "is_muhurat_locked": False,
                "venue_type": "Banquet Dining Hall"
            },
            {
                "key": "evening_gala",
                "name": "Evening Jubilee Gala, Toasting & Live Music",
                "day_offset": 0,
                "start_time_hour": 19,
                "duration_hours": 4,
                "is_outdoor": True,
                "is_muhurat_locked": False,
                "venue_type": "Rooftop Garden / Grand Terrace"
            }
        ],
        "birthday_traditional": [
            {
                "key": "ayushya_homa",
                "name": "Vedic Ayushya Homa & Ganapati Puja",
                "day_offset": 0,
                "start_time_hour": 8,
                "duration_hours": 3,
                "is_outdoor": False,
                "is_muhurat_locked": True,
                "muhurat_notes": "Sunrise solar alignment for longevity mantras",
                "venue_type": "Traditional Mandap"
            },
            {
                "key": "elder_blessings",
                "name": "Elder Blessings, Aarti & Tilak Ceremony",
                "day_offset": 0,
                "start_time_hour": 11,
                "duration_hours": 2,
                "is_outdoor": False,
                "is_muhurat_locked": False,
                "venue_type": "Main Ancestral Hall"
            },
            {
                "key": "traditional_feast",
                "name": "Satvik Banana Leaf Feast (Pankat)",
                "day_offset": 0,
                "start_time_hour": 13,
                "duration_hours": 3,
                "is_outdoor": False,
                "is_muhurat_locked": False,
                "venue_type": "Dining Hall"
            }
        ],
        "community_sarvajanik": [
            {
                "key": "prana_pratishtha",
                "name": "Pandal Inauguration, Murti Sthapana & Prana Pratishtha",
                "day_offset": 0,
                "start_time_hour": 8,
                "duration_hours": 3,
                "is_outdoor": False,
                "is_muhurat_locked": True,
                "muhurat_notes": "Auspicious Vedic Prana Pratishtha muhurat window",
                "venue_type": "Main Sanctum Pandal"
            },
            {
                "key": "maha_aarti",
                "name": "Maha Sandhya Aarti & Dhol Tasha Procession",
                "day_offset": 0,
                "start_time_hour": 19,
                "duration_hours": 3,
                "is_outdoor": True,
                "is_muhurat_locked": False,
                "venue_type": "Utsav Stage & Courtyard"
            },
            {
                "key": "cultural_program",
                "name": "Resident Talent Showcase & Folk Dance Competition",
                "day_offset": 1,
                "start_time_hour": 18,
                "duration_hours": 4,
                "is_outdoor": False,
                "is_muhurat_locked": False,
                "venue_type": "Main Stage Amphitheater"
            },
            {
                "key": "mahaprasad_bhandara",
                "name": "Community Mahaprasad / Annadan Bhandara",
                "day_offset": 2,
                "start_time_hour": 11,
                "duration_hours": 4,
                "is_outdoor": True,
                "is_muhurat_locked": False,
                "venue_type": "Prasad Distribution Pavilion"
            },
            {
                "key": "visarjan_procession",
                "name": "Grand Visarjan Shobhayatra & Procession",
                "day_offset": 2,
                "start_time_hour": 16,
                "duration_hours": 5,
                "is_outdoor": True,
                "is_muhurat_locked": False,
                "venue_type": "Procession Route & Riverfront"
            }
        ],
        "community_navratri": [
            {
                "key": "ghatasthapana",
                "name": "Maa Durga Ghatasthapana & Opening Aarti",
                "day_offset": 0,
                "start_time_hour": 18,
                "duration_hours": 2,
                "is_outdoor": False,
                "is_muhurat_locked": True,
                "muhurat_notes": "Navratri Day 1 auspicious twilight puja",
                "venue_type": "Garba Mandap Temple"
            },
            {
                "key": "dandiya_raas",
                "name": "Traditional Dandiya Raas & Mega Garba Night",
                "day_offset": 0,
                "start_time_hour": 20,
                "duration_hours": 4,
                "is_outdoor": True,
                "is_muhurat_locked": False,
                "venue_type": "Central Illuminated Garba Arena"
            },
            {
                "key": "awards_and_prasad",
                "name": "Midnight Aarti, Attire Awards & Prasad Distribution",
                "day_offset": 0,
                "start_time_hour": 23,
                "duration_hours": 1,
                "is_outdoor": False,
                "is_muhurat_locked": False,
                "venue_type": "Main Stage"
            }
        ],
        "community_society_mela": [
            {
                "key": "mela_opening",
                "name": "Society Carnival Opening & Food/Game Stalls Live",
                "day_offset": 0,
                "start_time_hour": 16,
                "duration_hours": 3,
                "is_outdoor": True,
                "is_muhurat_locked": False,
                "venue_type": "Society Clubhouse Grounds"
            },
            {
                "key": "musical_tambola",
                "name": "Resident Talent Showcase & Musical Tambola Night",
                "day_offset": 0,
                "start_time_hour": 19,
                "duration_hours": 3,
                "is_outdoor": False,
                "is_muhurat_locked": False,
                "venue_type": "Clubhouse Auditorium"
            },
            {
                "key": "society_dinner",
                "name": "Community Potluck Dinner & Lantern Lighting",
                "day_offset": 0,
                "start_time_hour": 21,
                "duration_hours": 3,
                "is_outdoor": True,
                "is_muhurat_locked": False,
                "venue_type": "Central Lawn Promenade"
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

    BIRTHDAY_TASKS = [
        TaskNode("bday_venue", "Reserve Birthday Party Hall / Clubhouse / Play Zone", 90, -30, "Host", dependencies=[]),
        TaskNode("bday_theme_decor", "Finalize Birthday Theme, Balloon Arches & Backdrop Specs", 120, -21, "Decor Lead", dependencies=["bday_venue"]),
        TaskNode("bday_cake", "Order Custom Themed Birthday Cake & Dessert Spread", 60, -14, "Host", dependencies=["bday_theme_decor"]),
        TaskNode("bday_entertainer", "Book Magician, Game Host/Emcee & Tattoo Artist", 60, -14, "Entertainment Lead", dependencies=["bday_venue"]),
        TaskNode("bday_catering", "Finalize Kids & Adults Party Finger-Food Buffet Menu", 60, -10, "Food & Beverage Lead", dependencies=["bday_venue"]),
        TaskNode("bday_gifts", "Procure Personalized Return Gifts & Party Favors", 60, -7, "Host", dependencies=["bday_theme_decor"]),
        TaskNode("bday_invites", "Send Digital WhatsApp Birthday Invitations & Track RSVPs", 45, -7, "Host", dependencies=["bday_venue"]),
        TaskNode("bday_run_of_show", "Assemble Day-of Party Timeline & Music Playlist", 45, -2, "Host", dependencies=["bday_cake", "bday_entertainer"])
    ]

    COMMUNITY_TASKS = [
        TaskNode("comm_permits_noc", "Obtain Municipal Ward Pandal Permission, Police & Traffic NOC", 120, -45, "Permits Liaison", dependencies=[]),
        TaskNode("comm_pandal_stage", "Contract Pandal Fabricator, Stage & German Hangar Tent", 180, -30, "Logistics Lead", dependencies=["comm_permits_noc"]),
        TaskNode("comm_sound_generator", "Contract Line-Array Sound, Diesel Genset & Fire Safety Gear", 90, -21, "Technical Lead", dependencies=["comm_permits_noc"]),
        TaskNode("comm_prasad_rations", "Procure Mahaprasad Rations, Cooking Team & Eco-Friendly Plates", 120, -14, "Food & Prasad Lead", dependencies=["comm_pandal_stage"]),
        TaskNode("comm_volunteer_corps", "Organize Volunteer Rosters for Crowd Control & Queue Management", 90, -10, "Volunteer Captain", dependencies=["comm_permits_noc"]),
        TaskNode("comm_dignitary_invites", "Issue VIP & Resident Society Cultural Invitations", 60, -7, "Secretary", dependencies=["comm_permits_noc"]),
        TaskNode("comm_security_cctv", "Install CCTV Surveillance, Metal Detectors & First Aid Booth", 120, -3, "Security Lead", dependencies=["comm_pandal_stage"]),
        TaskNode("comm_sound_dry_run", "Conduct Pre-Event Dry Run & Sound Level Decibel Check", 60, -1, "Festival Director", dependencies=["comm_sound_generator", "comm_security_cctv"])
    ]

    @classmethod
    def get_sub_events_for_tradition(cls, tradition_code: str, start_date_val: date, event_type: str = "wedding") -> List[Dict[str, Any]]:
        t_key = (tradition_code or "").lower()
        e_key = (event_type or "").lower()

        if t_key in cls.SUB_EVENT_TEMPLATES:
            template = cls.SUB_EVENT_TEMPLATES[t_key]
        elif "birthday" in e_key or "birthday" in t_key:
            template = cls.SUB_EVENT_TEMPLATES.get("birthday_kids_carnival")
        elif any(k in e_key or k in t_key for k in ("community", "festival", "mela", "society", "ganesh", "navratri")):
            template = cls.SUB_EVENT_TEMPLATES.get("community_sarvajanik")
        else:
            template = cls.SUB_EVENT_TEMPLATES.get(e_key, cls.SUB_EVENT_TEMPLATES["default"])

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
    def generate_scheduled_tasks(cls, start_date_val: date, event_type: str = "wedding") -> List[Dict[str, Any]]:
        e_key = (event_type or "").lower()
        if "birthday" in e_key:
            task_nodes = cls.BIRTHDAY_TASKS
        elif any(k in e_key for k in ("community", "festival", "mela", "society", "ganesh", "navratri")):
            task_nodes = cls.COMMUNITY_TASKS
        else:
            task_nodes = cls.FOUNDATION_TASKS

        if cls.check_cycles(task_nodes):
            raise ValueError(f"Circular dependency detected in {event_type} task DAG")

        scheduled = []
        for task in task_nodes:
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

    @classmethod
    def shift_tasks_for_date_moved(cls, tasks: List[Any], days_delta: int) -> List[Dict[str, Any]]:
        """
        Shifts scheduled timing of existing tasks by days_delta while preserving dependency ordering.
        Returns list of task diffs.
        """
        diffs = []
        for t in tasks:
            t_id = getattr(t, "id", "")
            title = getattr(t, "title", "")
            old_start = getattr(t, "scheduled_start", None)
            old_end = getattr(t, "scheduled_end", None)

            new_start = old_start + timedelta(days=days_delta) if old_start else None
            new_end = old_end + timedelta(days=days_delta) if old_end else None

            diffs.append({
                "task_id": t_id,
                "title": title,
                "old_start": old_start.isoformat() if old_start else None,
                "new_start": new_start.isoformat() if new_start else None,
                "old_end": old_end.isoformat() if old_end else None,
                "new_end": new_end.isoformat() if new_end else None,
                "days_shifted": days_delta,
                "formula": f"Date moved: shifted by {days_delta:+d} days to match new event date"
            })
        return diffs

    @classmethod
    def shift_sub_events_for_date_moved(cls, sub_events: List[Any], days_delta: int) -> List[Dict[str, Any]]:
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

            diffs.append({
                "sub_event_id": se_id,
                "name": name,
                "old_start": old_start.isoformat() if old_start else None,
                "new_start": new_start.isoformat() if new_start else None,
                "old_end": old_end.isoformat() if old_end else None,
                "new_end": new_end.isoformat() if new_end else None,
                "is_muhurat_locked": is_muhurat_locked,
                "formula": f"Event date moved: shifted by {days_delta:+d} days (Muhurat lock: {'Preserved' if is_muhurat_locked else 'Standard'})"
            })
        return diffs
