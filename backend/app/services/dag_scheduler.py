"""DAG Scheduler service facade.

Maintains backward-compatibility by re-exporting symbols from
the modular `backend.app.services.dag` package.
"""

from backend.app.services.dag.node import TaskNode
from backend.app.services.dag.scheduler import DAGScheduler
from backend.app.services.dag.templates import (
    BIRTHDAY_TASKS,
    COMMUNITY_TASKS,
    FOUNDATION_TASKS,
    SUB_EVENT_TEMPLATES,
)

__all__ = [
    "BIRTHDAY_TASKS",
    "COMMUNITY_TASKS",
    "FOUNDATION_TASKS",
    "SUB_EVENT_TEMPLATES",
    "DAGScheduler",
    "TaskNode",
]
