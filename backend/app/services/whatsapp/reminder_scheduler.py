from datetime import datetime, time, timedelta
from typing import ClassVar

from pydantic import BaseModel

from backend.app.models.models import Event, SubEvent


class ScheduledReminderPlan(BaseModel):
    sub_event_id: str
    sub_event_name: str
    sub_event_start_time: str
    offset_type: str  # "7_days_before", "1_day_before", "morning_of"
    scheduled_send_time: str
    message_draft: str


class ReminderScheduler:
    """
    Deterministic reminder schedule calculator for sub-events.
    Computes exact trigger timestamps without LLM math per DEC-002.
    """

    SUPPORTED_OFFSETS: ClassVar[list[str]] = ["7_days_before", "1_day_before", "morning_of"]

    @classmethod
    def calculate_reminder_send_time(cls, sub_event_start: datetime, offset_type: str) -> datetime:
        """
        Calculates exact target dispatch timestamp from sub_event_start.
        """
        if offset_type == "7_days_before":
            return sub_event_start - timedelta(days=7)
        elif offset_type == "1_day_before":
            return sub_event_start - timedelta(days=1)
        elif offset_type == "morning_of":
            # 8:00 AM on the day of the sub-event, or 2 hours prior if sub-event is before 10:00 AM
            morning_eight = datetime.combine(sub_event_start.date(), time(8, 0))
            if sub_event_start <= morning_eight:
                return sub_event_start - timedelta(hours=2)
            return morning_eight
        else:
            raise ValueError(
                f"Unsupported offset_type: {offset_type}. Choose from {cls.SUPPORTED_OFFSETS}"
            )

    @classmethod
    def draft_reminder_text(cls, event: Event, sub_event: SubEvent, offset_type: str) -> str:
        """Generates clear, deterministic reminder text customized to event type and sub-event."""
        sub_name = sub_event.name
        start_str = sub_event.start_time.strftime("%I:%M %p")
        date_str = sub_event.start_time.strftime("%A, %d %B")

        templates = {
            "7_days_before": (
                f"Reminder: {event.name}'s '{sub_name}' is 1 week away on {date_str} at "
                f"{start_str}! We look forward to celebrating together. "
                "Let us know if your travel plans change."
            ),
            "1_day_before": (
                f"Tomorrow is the day! '{sub_name}' begins tomorrow ({date_str}) at {start_str}. "
                "Location directions & schedule details are available on your invite link."
            ),
            "morning_of": (
                f"Good morning! '{sub_name}' kicks off today at {start_str}. "
                "Please arrive 15 minutes early for seating and welcome refreshments. "
                "See you soon!"
            ),
        }
        return templates.get(offset_type, f"Upcoming: '{sub_name}' on {date_str} at {start_str}.")

    @classmethod
    def generate_event_reminder_plans(
        cls, event: Event, sub_events: list[SubEvent], offsets: list[str] | None = None
    ) -> list[ScheduledReminderPlan]:
        """
        Generates full deterministic reminder schedule for all active sub-events in an event.
        """
        target_offsets = offsets or cls.SUPPORTED_OFFSETS
        plans: list[ScheduledReminderPlan] = []

        for sub in sub_events:
            for offset in target_offsets:
                send_time = cls.calculate_reminder_send_time(sub.start_time, offset)
                draft = cls.draft_reminder_text(event, sub, offset)
                plans.append(
                    ScheduledReminderPlan(
                        sub_event_id=sub.id,
                        sub_event_name=sub.name,
                        sub_event_start_time=sub.start_time.isoformat(),
                        offset_type=offset,
                        scheduled_send_time=send_time.isoformat(),
                        message_draft=draft,
                    )
                )

        # Sort chronologically by scheduled_send_time
        plans.sort(key=lambda p: p.scheduled_send_time)
        return plans
