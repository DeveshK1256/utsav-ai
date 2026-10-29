class TaskNode:
    """Represents an actionable planning node within the DAG graph."""

    def __init__(
        self,
        task_id: str,
        title: str,
        duration_minutes: int,
        offset_days: int,
        assigned_role: str,
        sub_event_key: str | None = None,
        dependencies: list[str] | None = None,
    ) -> None:
        self.task_id = task_id
        self.title = title
        self.duration_minutes = duration_minutes
        self.offset_days = offset_days
        self.assigned_role = assigned_role
        self.sub_event_key = sub_event_key
        self.dependencies = dependencies or []
